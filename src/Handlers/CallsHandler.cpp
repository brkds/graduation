#include "Handlers/CallsHandler.h"
#include "Utils/DatabaseManager.h"
#include "Utils/ASTUtils.h" 
#include "clang/AST/Decl.h"
#include "clang/AST/Expr.h"
#include "clang/Basic/SourceManager.h"
#include "llvm/Support/Path.h"
#include <iostream>

CallsHandler::CallsHandler(clang::ASTContext* context, DatabaseManager& dbManager, ASTUtils &utils)
    : context_(context), dbManager_(dbManager), utils_(utils) {} 

std::string CallsHandler::getParamsString(const clang::FunctionDecl *FD) {
    std::string paramsStr = "(";
    for (unsigned i = 0; i < FD->getNumParams(); ++i) {
        const clang::ParmVarDecl *PVD = FD->getParamDecl(i);
        paramsStr += PVD->getType().getAsString();
        if (i < FD->getNumParams() - 1) {
            paramsStr += ", ";
        }
    }
    paramsStr += ")";
    return paramsStr;
}

std::string CallsHandler::generateFunctionSignature(const clang::FunctionDecl *FD) {
    std::string signature = "(";
    if (FD->getNumParams() == 0) {
        signature = "()";
    } else {
        for (unsigned i = 0; i < FD->getNumParams(); ++i) {
            const clang::ParmVarDecl *PVD = FD->getParamDecl(i);
            signature += PVD->getType().getAsString();
            if (i < FD->getNumParams() - 1) {
                signature += ", ";
            }
        }
        signature += ")";
    }
    return signature;
}

void CallsHandler::handleCallExpr(clang::CallExpr *CE, const std::string& callerName, 
                                  clang::FunctionDecl *currentFunction) {
    if (!CE || callerName.empty()) {
        return;
    }

    const clang::FunctionDecl *calleeDecl = CE->getDirectCallee();
    if (!calleeDecl) {
        return;
    }

    std::string calleeName = calleeDecl->getNameInfo().getAsString();
    
    clang::SourceManager &SM = context_->getSourceManager();
    clang::SourceLocation calleeLoc = calleeDecl->getLocation();
    bool isMacroExpandedFunction = false;
    
    if (calleeLoc.isValid()) {
        clang::SourceLocation spellingLoc = SM.getSpellingLoc(calleeLoc);
        clang::SourceLocation expansionLoc = SM.getExpansionLoc(calleeLoc);
        
        if (spellingLoc != expansionLoc) {
            isMacroExpandedFunction = true;
        }
        
        if (SM.isInSystemHeader(spellingLoc) && !SM.isInSystemHeader(expansionLoc)) {
            isMacroExpandedFunction = true;
        }
    }
    
    // 检查是否为用户代码或宏展开
    if (!isMacroExpandedFunction && !utils_.isFromUserCode(calleeDecl)) {
        return;
    }
    
    std::string calleeReturnType = calleeDecl->getReturnType().getAsString();
    bool isStatic = (calleeDecl->getStorageClass() == clang::SC_Static);
    std::string signature = generateFunctionSignature(calleeDecl);
    
    // 获取被调用函数的位置信息
    const clang::FunctionDecl *definitionDecl = calleeDecl->getDefinition();
    if (definitionDecl) {
        calleeDecl = definitionDecl;
    }
    
    std::string calleeFilePathStr;
    int calleeStartLine = 0, calleeStartCol = 0, calleeEndLine = 0, calleeEndCol = 0;

    utils_.getSourceLocationDetails(calleeDecl->getBeginLoc(), SM, calleeFilePathStr, calleeStartLine, calleeStartCol);
    utils_.getSourceLocationDetails(calleeDecl->getEndLoc(), SM, calleeFilePathStr, calleeEndLine, calleeEndCol);

    // 对于宏展开的函数，如果位置信息无效，使用调用位置作为替代
    if (calleeFilePathStr == "invalid_location" && isMacroExpandedFunction) {
        utils_.getSourceLocationDetails(CE->getBeginLoc(), SM, calleeFilePathStr, calleeStartLine, calleeStartCol);
        calleeEndLine = calleeStartLine;
        calleeEndCol = calleeStartCol;
    } else if (calleeFilePathStr == "invalid_location") {
        return;
    }

    // 直接插入被调用函数（如果不存在则插入，存在则忽略）
    // insertFunction 内部使用 INSERT OR REPLACE
    dbManager_.insertFunction(
        calleeName, calleeReturnType, signature, calleeFilePathStr, 
        calleeStartLine, calleeStartCol, calleeEndLine, calleeEndCol, 
        isStatic
    );

    // 获取调用位置信息
    std::string callSiteFilePathStr;
    int callSiteLine = 0, callSiteCol = 0;
    utils_.getSourceLocationDetails(CE->getBeginLoc(), SM, callSiteFilePathStr, callSiteLine, callSiteCol);
    
    // 直接插入调用关系（用名字）
    dbManager_.insertCallRelation(callerName, calleeName, callSiteFilePathStr, callSiteLine, callSiteCol);
}