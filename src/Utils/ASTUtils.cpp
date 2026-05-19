#include "ASTUtils.h"
#include <clang/AST/Expr.h>
#include <clang/AST/ParentMapContext.h> // For ASTContext::getParents
#include <clang/AST/ASTTypeTraits.h> // For clang::DynTypedNode
#include <clang/Basic/FileManager.h> 
#include "llvm/Support/Path.h"      
#include <clang/Lex/Lexer.h> // Ensure Lexer is included for getSourceText
#include <string> // Required for std::to_string

ASTUtils::ASTUtils(clang::ASTContext &Ctx) : Context(Ctx) {} // Changed to reference

bool ASTUtils::isAssignmentLHS(const clang::Expr *E) {
    if (!E) return false;
    const clang::Expr* currentExpr = E->IgnoreParenImpCasts();

    // Context is a reference, use . not ->
    const auto& parents = Context.getParents(*currentExpr); 
    if (parents.empty()) {
        return false;
    }

    // Corrected DynTypedNode usage
    const clang::DynTypedNode parentNode = parents[0]; 

    if (const clang::BinaryOperator* BO = parentNode.get<clang::BinaryOperator>()) {
        if (BO->isAssignmentOp() && BO->getLHS()->IgnoreParenImpCasts() == currentExpr) {
            return true;
        }
    } else if (const clang::UnaryOperator* UO = parentNode.get<clang::UnaryOperator>()) {
        // If it's part of ++x or --x, it's an LHS-like context for write
        if (UO->isIncrementDecrementOp() && UO->getSubExpr()->IgnoreParenImpCasts() == currentExpr) {
             // Check if it's a prefix increment/decrement, those are more clearly "LHS"
            if (UO->isPrefix()) return true;
            // Postfix might also be considered a write context for the variable itself.
            // Depending on strictness, you might always return true here for inc/dec.
            return true; 
        }
    }
    // Add other contexts if necessary, e.g., being passed as a non-const reference.
    return false;
}

bool ASTUtils::isIncrementDecrement(const clang::Expr *E) {
    if (!E) return false;
    const clang::Expr* currentExpr = E->IgnoreParenImpCasts();

    const auto& parents = Context.getParents(*currentExpr);
    if (parents.empty()) {
        return false;
    }

    const clang::DynTypedNode parentNode = parents[0];

    if (const clang::UnaryOperator* UO = parentNode.get<clang::UnaryOperator>()) {
        // 检查是否是自增或自减操作
        if (UO->isIncrementDecrementOp() && UO->getSubExpr()->IgnoreParenImpCasts() == currentExpr) {
            return true;
        }
    }
    
    return false;
}

std::string ASTUtils::getPointerName(clang::Expr *E) {
    E = E->IgnoreParenCasts();
    if (auto *DeclRef = clang::dyn_cast<clang::DeclRefExpr>(E)) {
        return DeclRef->getNameInfo().getAsString();
    }
    if (auto *Member = clang::dyn_cast<clang::MemberExpr>(E)) {
        if (clang::ValueDecl *VD = Member->getMemberDecl()) {
            return VD->getNameAsString();
        }
    }
    return "";
}

std::string ASTUtils::getFullPointerName(clang::Expr *E) {
    E = E->IgnoreParenCasts();
    
    if (auto *DeclRef = clang::dyn_cast<clang::DeclRefExpr>(E)) {
        return DeclRef->getNameInfo().getAsString();
    }
    
    if (auto *Member = clang::dyn_cast<clang::MemberExpr>(E)) {
        if (clang::ValueDecl *VD = Member->getMemberDecl()) {
            std::string memberName = VD->getNameAsString();
            std::string baseName = getFullPointerName(Member->getBase());
            
            if (baseName.empty()) {
                return memberName;
            }
            
            // 判断是箭头访问还是点访问
            if (Member->isArrow()) {
                return baseName + "->" + memberName;
            } else {
                return baseName + "." + memberName;
            }
        }
    }
    
    // 处理数组下标访问
    if (auto *ArraySub = clang::dyn_cast<clang::ArraySubscriptExpr>(E)) {
        std::string baseName = getFullPointerName(ArraySub->getBase());
        if (!baseName.empty()) {
            // 简化处理，不获取具体的下标值，只显示[]
            return baseName + "[]";
        }
    }
    
    // 处理解引用
    if (auto *Unary = clang::dyn_cast<clang::UnaryOperator>(E)) {
        if (Unary->getOpcode() == clang::UO_Deref) {
            std::string subName = getFullPointerName(Unary->getSubExpr());
            if (!subName.empty()) {
                return "*" + subName;
            }
        }
    }
    
    return "";
}

// Definition for getAbsoluteFilePath
std::string ASTUtils::getAbsoluteFilePath(clang::SourceManager &SM, clang::SourceLocation Loc) const {
    if (!Loc.isValid() || !Loc.isFileID()) {
        return "unknown";
    }

    // 获取展开位置
    clang::SourceLocation ExpansionLoc = SM.getExpansionLoc(Loc);
    if (!ExpansionLoc.isValid()) {
        return "invalid_expansion";
    }

    // 获取拼写位置（实际源代码位置）
    clang::SourceLocation SpellingLoc = SM.getSpellingLoc(Loc);
    if (!SpellingLoc.isValid()) {
        return "invalid_spelling";
    }

    // 优先使用拼写位置的文件
    const clang::FileEntry *FE = SM.getFileEntryForID(SM.getFileID(SpellingLoc));
    if (!FE) {
        // 如果拼写位置没有文件，尝试使用展开位置
        FE = SM.getFileEntryForID(SM.getFileID(ExpansionLoc));
        if (!FE) {
            return "unknown_file_entry";
        }
    }

    std::string FilePath = FE->getName().str();
    if (FilePath.empty()) {
        return "empty_file_path";
    }

    // 转换为绝对路径
    llvm::SmallString<256> AbsPath(FilePath);
    std::error_code EC = llvm::sys::fs::make_absolute(AbsPath);
    if (!EC) {
        // 规范化路径
        llvm::sys::path::remove_dots(AbsPath, true);
        return std::string(AbsPath.str());
    }
    
    return FilePath; // 返回原始路径
}

// Definition for getSourceLocationDetails
void ASTUtils::getSourceLocationDetails(clang::SourceLocation loc, clang::SourceManager &SM, 
                                      std::string &filePath, int &lineNumber, int &columnNumber) {
    if (!loc.isValid()) {
        filePath = "invalid_location";
        lineNumber = 0;
        columnNumber = 0;
        return;
    }

    // 获取展开位置
    clang::SourceLocation ExpansionLoc = SM.getExpansionLoc(loc);
    if (!ExpansionLoc.isValid()) {
        filePath = "invalid_expansion";
        lineNumber = 0;
        columnNumber = 0;
        return;
    }

    // 获取拼写位置
    clang::SourceLocation SpellingLoc = SM.getSpellingLoc(loc);
    if (!SpellingLoc.isValid()) {
        filePath = "invalid_spelling";
        lineNumber = 0;
        columnNumber = 0;
        return;
    }

    // 优先使用拼写位置
    clang::PresumedLoc PLoc = SM.getPresumedLoc(SpellingLoc);
    if (!PLoc.isValid()) {
        // 如果拼写位置无效，尝试使用展开位置
        PLoc = SM.getPresumedLoc(ExpansionLoc);
        if (!PLoc.isValid()) {
            filePath = "invalid_presumed_location";
            lineNumber = 0;
            columnNumber = 0;
            return;
        }
    }

    // 获取文件路径
    filePath = PLoc.getFilename();
    if (filePath.empty()) {
        filePath = "empty_file_path";
        lineNumber = 0;
        columnNumber = 0;
        return;
    }

    // 转换为绝对路径
    llvm::SmallString<256> AbsPath(filePath);
    std::error_code EC = llvm::sys::fs::make_absolute(AbsPath);
    if (!EC) {
        llvm::sys::path::remove_dots(AbsPath, true);
        filePath = std::string(AbsPath.str());
    }

    lineNumber = PLoc.getLine();
    columnNumber = PLoc.getColumn();
}

// Added definition for getSourceText
std::string ASTUtils::getSourceText(clang::SourceRange SR, clang::SourceManager &SM, const clang::LangOptions &LO) {
    if (!SR.isValid()) {
        // Output to stderr for easier GDB logging if needed, or use a proper logging mechanism.
        // fprintf(stderr, "ASTUtils::getSourceText: Invalid source range (SR.isValid() is false)\\n");
        return "// Invalid source range (isValid check)";
    }

    clang::SourceLocation spellingBeginLoc = SM.getSpellingLoc(SR.getBegin());
    clang::SourceLocation spellingEndLoc = SM.getSpellingLoc(SR.getEnd());

    if (!spellingBeginLoc.isValid() || !spellingEndLoc.isValid()) {
        spellingBeginLoc = SR.getBegin();
        spellingEndLoc = SR.getEnd();
        if (!spellingBeginLoc.isValid() || !spellingEndLoc.isValid()) {
            // fprintf(stderr, "ASTUtils::getSourceText: Invalid source range (begin/end loc invalid after fallback)\\n");
            return "// Invalid source range (begin/end loc invalid)";
        }
    }
    
    clang::FileID beginFileID = SM.getFileID(spellingBeginLoc);
    clang::FileID endFileID = SM.getFileID(spellingEndLoc);

    if (beginFileID != endFileID) {
        // clang::PresumedLoc pLocBegin = SM.getPresumedLoc(spellingBeginLoc);
        // clang::PresumedLoc pLocEnd = SM.getPresumedLoc(spellingEndLoc);
        // if (pLocBegin.isValid() && pLocEnd.isValid()) {
        //     fprintf(stderr, "ASTUtils::getSourceText: Range spans different files. Begin: %s, End: %s\\n", pLocBegin.getFilename(), pLocEnd.getFilename());
        // } else {
        //     fprintf(stderr, "ASTUtils::getSourceText: Range spans different files or complex macro (PresumedLoc invalid)\\n");
        // }
        return "// Source range spans different files or complex macro expansion";
    }

    bool invalidCharData = false;
    const char *startPtr = SM.getCharacterData(spellingBeginLoc, &invalidCharData);
    if (invalidCharData || !startPtr) {
        // clang::PresumedLoc pLoc = SM.getPresumedLoc(spellingBeginLoc);
        // fprintf(stderr, "ASTUtils::getSourceText: Failed to get char data for start of range. Loc: %s:%d:%d, InvalidFlag: %d, NullPtr: %d\\n",
        //         pLoc.isValid() ? pLoc.getFilename() : "N/A", pLoc.isValid() ? pLoc.getLine() : 0, pLoc.isValid() ? pLoc.getColumn() : 0, invalidCharData, !startPtr);
        return "// Failed to get char data for start of range";
    }

    const char *endPtr = SM.getCharacterData(spellingEndLoc, &invalidCharData);
    if (invalidCharData || !endPtr) {
        // clang::PresumedLoc pLoc = SM.getPresumedLoc(spellingEndLoc);
        // fprintf(stderr, "ASTUtils::getSourceText: Failed to get char data for end of range. Loc: %s:%d:%d, InvalidFlag: %d, NullPtr: %d\\n",
        //         pLoc.isValid() ? pLoc.getFilename() : "N/A", pLoc.isValid() ? pLoc.getLine() : 0, pLoc.isValid() ? pLoc.getColumn() : 0, invalidCharData, !endPtr);
        return "// Failed to get char data for end of range";
    }

    if (endPtr < startPtr) {
        // clang::PresumedLoc pLocBegin = SM.getPresumedLoc(spellingBeginLoc);
        // clang::PresumedLoc pLocEnd = SM.getPresumedLoc(spellingEndLoc);
        // std::string error_msg = "// End pointer is before start pointer. ";
        // if (pLocBegin.isValid()) error_msg += "Begin: " + std::string(pLocBegin.getFilename()) + ":" + std::to_string(pLocBegin.getLine()) + ":" + std::to_string(pLocBegin.getColumn());
        // if (pLocEnd.isValid()) error_msg += ", End: " + std::string(pLocEnd.getFilename()) + ":" + std::to_string(pLocEnd.getLine()) + ":" + std::to_string(pLocEnd.getColumn());
        // fprintf(stderr, "ASTUtils::getSourceText: %s\\n", error_msg.c_str());
        return "// End pointer is before start pointer";
    }

    ptrdiff_t length = endPtr - startPtr;
    
    const ptrdiff_t MAX_REASONABLE_LENGTH = 10 * 1024 * 1024; // 10MB
    if (length > MAX_REASONABLE_LENGTH) {
        // clang::PresumedLoc pLocBegin = SM.getPresumedLoc(spellingBeginLoc);
        // clang::PresumedLoc pLocEnd = SM.getPresumedLoc(spellingEndLoc);
        // std::string error_msg = "// Calculated length is excessively large (" + std::to_string(length) + " bytes). ";
        // if (pLocBegin.isValid()) error_msg += "Begin: " + std::string(pLocBegin.getFilename()) + ":" + std::to_string(pLocBegin.getLine()) + ":" + std::to_string(pLocBegin.getColumn());
        // if (pLocEnd.isValid()) error_msg += ", End: " + std::string(pLocEnd.getFilename()) + ":" + std::to_string(pLocEnd.getLine()) + ":" + std::to_string(pLocEnd.getColumn());
        // fprintf(stderr, "ASTUtils::getSourceText: %s\\n", error_msg.c_str());
        return "// Calculated length is excessively large";
    }
    
    return llvm::StringRef(startPtr, static_cast<size_t>(length)).str();
}

// 新增：用户代码过滤相关方法的实现
void ASTUtils::setUserCodePaths(const std::set<std::string> &userPaths) {
    userCodePaths_ = userPaths;
}

void ASTUtils::addUserCodePath(const std::string &path) {
    userCodePaths_.insert(path);
}

bool ASTUtils::isFromUserCode(clang::SourceLocation loc, clang::SourceManager &SM) const {
    if (!loc.isValid()) {
        return false;
    }
    
    std::string filePath = getAbsoluteFilePath(SM, loc);
    if (filePath == "unknown" || filePath == "unknown_file_entry" || filePath == "invalid_location") {
        return false;
    }
    
    // 检查文件路径是否属于用户代码路径
    for (const auto &userPath : userCodePaths_) {
        // 如果文件路径以用户代码路径开头，认为是用户代码
        if (filePath.find(userPath) == 0) {
            return true;
        }
    }
    
    return false;
}

bool ASTUtils::isFromUserCode(const clang::Decl *decl) const {
    if (!decl) {
        return false;
    }
    
    clang::SourceLocation loc = decl->getLocation();
    clang::SourceManager &SM = Context.getSourceManager();
    return isFromUserCode(loc, SM);
}

// 改进的过滤方法实现
bool ASTUtils::isUserCodeFunction(const clang::FunctionDecl *FD) const {
    if (!FD) {
        return false;
    }
    
    clang::SourceManager &SM = Context.getSourceManager();
    clang::SourceLocation loc = FD->getLocation();
    
    // 1. 检查系统头文件
    if (loc.isValid() && SM.isInSystemHeader(loc)) {
        return false;
    }
    
    // 2. 只处理有函数体的函数定义，过滤掉仅声明的系统函数
    if (!FD->doesThisDeclarationHaveABody()) {
        return false;
    }
    
    // 3. 检查是否来自用户代码路径
    return isFromUserCode(loc, SM);
}

bool ASTUtils::isUserCodeVariable(const clang::VarDecl *VD) const {
    if (!VD) {
        return false;
    }
    
    clang::SourceManager &SM = Context.getSourceManager();
    clang::SourceLocation loc = VD->getLocation();
    
    // 1. 检查系统头文件
    if (loc.isValid() && SM.isInSystemHeader(loc)) {
        return false;
    }
    
    // 2. 检查是否来自用户代码路径 - 这是主要的过滤条件
    if (!isFromUserCode(loc, SM)) {
        return false;
    }
    
    // 3. 对于全局变量，我们接受所有在用户代码中定义的变量
    // 包括具有外部链接的变量（跨文件访问需要）
    return VD->hasGlobalStorage();
}

bool ASTUtils::isUserCodeLocation(clang::SourceLocation loc, clang::SourceManager &SM) const {
    if (!loc.isValid()) {
        return false;
    }
    
    // 1. 检查系统头文件
    if (SM.isInSystemHeader(loc)) {
        return false;
    }
    
    // 2. 检查是否来自用户代码路径
    return isFromUserCode(loc, SM);
}

clang::SourceManager& ASTUtils::getSourceManager() const {
    return Context.getSourceManager();
}