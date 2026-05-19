#include "Handlers/GlobalVarHandler.h"
#include "Utils/ASTUtils.h"
#include "Utils/DatabaseManager.h"
#include "clang/AST/Decl.h"
#include "clang/AST/Expr.h"
#include "clang/Basic/SourceManager.h"
#include "llvm/Support/Path.h"
#include "clang/Lex/Lexer.h"

GlobalVarHandler::GlobalVarHandler(clang::ASTContext* context, DatabaseManager& dbManager, ASTUtils &utils)
    : context_(context), dbManager_(dbManager), utils_(utils) {}

void GlobalVarHandler::handleVarDecl(clang::VarDecl *VD) {
    if (!VD) { 
        return;
    }

    if (!utils_.isUserCodeVariable(VD)) {
        return;
    }

    // 只处理变量定义，跳过声明（extern）
    if (VD->hasExternalStorage() && !VD->hasInit() && !VD->isThisDeclarationADefinition()) {
        return;
    }

    clang::SourceManager &SM = context_->getSourceManager();
    clang::SourceLocation loc = VD->getLocation();

    std::string name = VD->getNameAsString();
    std::string type = VD->getType().getAsString();
    std::string filePath = "unknown";
    int lineNumber = 0;

    if (loc.isValid()) {
        filePath = utils_.getAbsoluteFilePath(SM, loc); 
        lineNumber = SM.getPresumedLineNumber(loc);
    }
    
    bool isStatic = VD->getStorageClass() == clang::SC_Static;
    std::string definitionCode = ""; 

    // 获取完整的变量定义代码
    if (loc.isValid()) {
        clang::SourceLocation startLoc = VD->getBeginLoc();
        clang::SourceLocation endLoc;
        
        if (VD->hasInit()) {
            endLoc = VD->getInit()->getEndLoc();
        } else {
            endLoc = VD->getEndLoc();
        }

        if (startLoc.isValid() && endLoc.isValid()) {
            endLoc = clang::Lexer::getLocForEndOfToken(endLoc, 0, SM, context_->getLangOpts());
            clang::SourceRange defRange(startLoc, endLoc);
            definitionCode = utils_.getSourceText(defRange, SM, context_->getLangOpts());
            
            if (!definitionCode.empty() && definitionCode.back() != ';') {
                definitionCode += ";";
            }
        }
    }

    // 直接插入，不再先查找 ID
    // insertGlobalVariable 内部使用 INSERT OR REPLACE，重复插入会自动覆盖
    dbManager_.insertGlobalVariable(name, type, filePath, lineNumber, isStatic, definitionCode);
}