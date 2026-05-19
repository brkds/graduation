#include "DataPointerHandler.h"
#include <clang/AST/Expr.h>
#include <clang/Basic/SourceManager.h>

DataPointerHandler::DataPointerHandler(clang::ASTContext *Ctx, DatabaseManager &dbManager, ASTUtils &utils)
    : Context(Ctx), dbManager_(dbManager), utils_(utils) {}

bool DataPointerHandler::shouldFilterSymbol(const std::string& name) {
    if (name.find("__UNIQUE_ID___addressable") != std::string::npos) return true;
    if (name.find("__SCK__") != std::string::npos) return true;
    if (name.find("__SCT__") != std::string::npos) return true;
    if (name.find("__ADDRESSABLE") != std::string::npos) return true;
    if (name.find("__static_call") != std::string::npos) return true;
    if (name.find("__UNIQUE_ID_") != std::string::npos) return true;
    if (name.find("__func__.") != std::string::npos) return true;
    if (name.find("__PRETTY_FUNCTION__.") != std::string::npos) return true;
    return false;
}

void DataPointerHandler::handleVarDecl(clang::VarDecl *VD) {
    if (!VD || !VD->hasInit() || !Context) return;

    clang::Expr *Init = VD->getInit();
    if (!Init) return;
    
    Init = Init->IgnoreParenCasts();
    if (!Init) return;

    if (auto *Unary = clang::dyn_cast<clang::UnaryOperator>(Init)) {
        if (!Unary->getSubExpr()) return;
        
        if (Unary->getOpcode() == clang::UO_AddrOf) {
            if (auto *DeclRef = clang::dyn_cast<clang::DeclRefExpr>(Unary->getSubExpr())) {
                if (!DeclRef->getDecl()) return;
                
                if (auto *Pointee = clang::dyn_cast<clang::VarDecl>(DeclRef->getDecl())) {
                    if (Pointee->hasGlobalStorage()) {
                        if (!utils_.isUserCodeVariable(VD) || !utils_.isUserCodeVariable(Pointee)) {
                            return;
                        }

                        std::string pointerName = VD->getNameAsString();
                        std::string pointeeName = Pointee->getNameAsString();
                        
                        if (shouldFilterSymbol(pointerName) || shouldFilterSymbol(pointeeName)) {
                            return;
                        }

                        clang::SourceManager &SM = Context->getSourceManager();
                        if (!Init->getBeginLoc().isValid()) return;
                        
                        clang::SourceLocation Loc = SM.getExpansionLoc(Init->getBeginLoc());
                        if (!Loc.isValid()) return;

                        // 直接记录指针关系，不需要查找 ID
                        std::string filePath = utils_.getAbsoluteFilePath(SM, Loc);
                        int lineNumber = SM.getSpellingLineNumber(Loc);
                        
                        if (!filePath.empty() && lineNumber > 0) {
                            // 直接用变量名插入，不再需要 ID
                            dbManager_.insertDataPointer(pointerName, pointeeName, filePath, lineNumber);
                        }
                    }
                }
            }
        }
    }
    
    if (VD->getType()->isPointerType()) {
        analyzePointerAssignment(VD, Init);
    }
}

void DataPointerHandler::handleBinaryOperator(clang::BinaryOperator *BO) {
    if (!BO || !BO->isAssignmentOp() || !Context) return;

    clang::Expr *LHS = BO->getLHS();
    clang::Expr *RHS = BO->getRHS();
    if (!LHS || !RHS) return;
    
    if (const auto *declRef = llvm::dyn_cast<clang::DeclRefExpr>(LHS->IgnoreImpCasts())) {
        if (const auto *varDecl = llvm::dyn_cast<clang::VarDecl>(declRef->getDecl())) {
            if (varDecl->getType()->isPointerType()) {
                analyzePointerAssignment(varDecl, RHS);
            }
        }
    }
    
    if (const auto *memberExpr = llvm::dyn_cast<clang::MemberExpr>(LHS->IgnoreImpCasts())) {
        if (const auto *fieldDecl = llvm::dyn_cast<clang::FieldDecl>(memberExpr->getMemberDecl())) {
            if (fieldDecl->getType()->isPointerType()) {
                std::string fullPointerName = utils_.getFullPointerName(LHS);
                if (!fullPointerName.empty()) {
                    analyzeMemberPointerAssignment(fullPointerName, fieldDecl, RHS);
                    return;
                }
            }
        }
    }

    RHS = RHS->IgnoreParenCasts();
    if (!RHS) return;

    if (auto *Unary = clang::dyn_cast<clang::UnaryOperator>(RHS)) {
        if (!Unary->getSubExpr()) return;
        
        if (Unary->getOpcode() == clang::UO_AddrOf) {
            if (auto *DeclRef = clang::dyn_cast<clang::DeclRefExpr>(Unary->getSubExpr())) {
                if (!DeclRef->getDecl()) return;
                
                if (auto *Pointee = clang::dyn_cast<clang::VarDecl>(DeclRef->getDecl())) {
                    if (Pointee->hasGlobalStorage()) {
                        std::string pointerName = utils_.getFullPointerName(BO->getLHS());
                        if (pointerName.empty()) return;
                        
                        std::string pointeeName = Pointee->getNameAsString();
                        if (shouldFilterSymbol(pointerName) || shouldFilterSymbol(pointeeName)) {
                            return;
                        }

                        clang::SourceManager &SM = Context->getSourceManager();
                        if (!RHS->getBeginLoc().isValid()) return;
                        
                        clang::SourceLocation Loc = SM.getExpansionLoc(RHS->getBeginLoc());
                        if (!Loc.isValid()) return;

                        std::string filePath = utils_.getAbsoluteFilePath(SM, Loc);
                        int lineNumber = SM.getSpellingLineNumber(Loc);
                        
                        if (!filePath.empty() && lineNumber > 0) {
                            // 直接用变量名插入
                            dbManager_.insertDataPointer(pointerName, pointeeName, filePath, lineNumber);
                        }
                    }
                }
            }
        }
    }
}

void DataPointerHandler::analyzePointerAssignment(const clang::NamedDecl *pointerDecl, const clang::Expr *rhs) {
    if (!pointerDecl || !rhs || !Context) return;
    
    std::string pointerName = pointerDecl->getNameAsString();
    if (shouldFilterSymbol(pointerName)) {
        return;
    }
    
    rhs = rhs->IgnoreParenCasts();
    
    if (const auto *unaryOp = llvm::dyn_cast<clang::UnaryOperator>(rhs)) {
        if (unaryOp->getOpcode() == clang::UO_AddrOf) {
            if (const auto *declRef = llvm::dyn_cast<clang::DeclRefExpr>(unaryOp->getSubExpr())) {
                if (const auto *varDecl = llvm::dyn_cast<clang::VarDecl>(declRef->getDecl())) {
                    if (varDecl->hasGlobalStorage()) {
                        recordPointerToVariable(pointerName, varDecl, rhs->getBeginLoc());
                    }
                }
            }
        }
    }
    else if (const auto *declRef = llvm::dyn_cast<clang::DeclRefExpr>(rhs)) {
        if (const auto *varDecl = llvm::dyn_cast<clang::VarDecl>(declRef->getDecl())) {
            if (varDecl->hasGlobalStorage() && varDecl->getType()->isArrayType()) {
                recordPointerToVariable(pointerName, varDecl, rhs->getBeginLoc());
            }
        }
    }
}

void DataPointerHandler::analyzeMemberPointerAssignment(const std::string &fullPointerName,
                                                       const clang::FieldDecl *fieldDecl,
                                                       const clang::Expr *rhs) {
    if (!fieldDecl || !rhs || !Context) return;
    
    if (shouldFilterSymbol(fullPointerName)) {
        return;
    }
    
    rhs = rhs->IgnoreParenCasts();
    
    if (const auto *unaryOp = llvm::dyn_cast<clang::UnaryOperator>(rhs)) {
        if (unaryOp->getOpcode() == clang::UO_AddrOf) {
            if (const auto *declRef = llvm::dyn_cast<clang::DeclRefExpr>(unaryOp->getSubExpr())) {
                if (const auto *varDecl = llvm::dyn_cast<clang::VarDecl>(declRef->getDecl())) {
                    if (varDecl->hasGlobalStorage()) {
                        recordPointerToVariable(fullPointerName, varDecl, rhs->getBeginLoc());
                    }
                }
            }
        }
    }
    else if (const auto *declRef = llvm::dyn_cast<clang::DeclRefExpr>(rhs)) {
        if (const auto *varDecl = llvm::dyn_cast<clang::VarDecl>(declRef->getDecl())) {
            if (varDecl->hasGlobalStorage() && varDecl->getType()->isArrayType()) {
                recordPointerToVariable(fullPointerName, varDecl, rhs->getBeginLoc());
            }
        }
    }
}

void DataPointerHandler::recordPointerToVariable(const std::string &pointerName, 
                                                const clang::VarDecl *varDecl, 
                                                clang::SourceLocation loc) {
    if (!varDecl || !Context) return;
    
    clang::SourceManager &SM = Context->getSourceManager();
    std::string pointeeName = varDecl->getNameAsString();
    
    if (shouldFilterSymbol(pointeeName)) {
        return;
    }
    
    if (loc.isValid()) {
        clang::SourceLocation expandedLoc = SM.getExpansionLoc(loc);
        if (expandedLoc.isValid()) {
            std::string filePath = utils_.getAbsoluteFilePath(SM, expandedLoc);
            int lineNumber = SM.getSpellingLineNumber(expandedLoc);
            
            if (!filePath.empty() && lineNumber > 0) {
                // 直接用变量名插入
                dbManager_.insertDataPointer(pointerName, pointeeName, filePath, lineNumber);
            }
        }
    }
}