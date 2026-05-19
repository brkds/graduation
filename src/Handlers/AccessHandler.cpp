#include "Handlers/AccessHandler.h"
#include "Utils/ASTUtils.h"
#include "Utils/DatabaseManager.h"
#include "clang/AST/Decl.h"
#include "clang/AST/Expr.h"
#include "clang/AST/ASTContext.h"
#include <clang/AST/ASTTypeTraits.h>
#include <clang/AST/ParentMapContext.h>
#include "clang/Basic/SourceManager.h"
#include "clang/Basic/FileManager.h"
#include "llvm/Support/Path.h"
#include <iostream>

AccessHandler::AccessHandler(clang::ASTContext* astContext, DatabaseManager& dbManager, ASTUtils &utils_param)
    : Context(astContext), dbManager_(dbManager), utils(utils_param) {}

void AccessHandler::recordAccess(clang::VarDecl *varDecl, const std::string& accessType, 
                                 clang::FunctionDecl *CurrentFunction, const std::string& funcName, 
                                 clang::SourceLocation accessLocation) {
    if (!varDecl || funcName.empty()) {
        return;
    }

    clang::SourceManager &SM = Context->getSourceManager();
    if (!utils.isUserCodeLocation(accessLocation, SM)) {
        return; 
    }
    if (!utils.isUserCodeVariable(varDecl)) {
        return; 
    }
    
    std::string varName = varDecl->getNameAsString();

    // 获取访问位置信息
    std::string accessFilePathStr = "unknown";
    int accessLine = 0;

    if (accessLocation.isValid()) {
        accessFilePathStr = utils.getAbsoluteFilePath(SM, accessLocation);
        accessLine = SM.getPresumedLineNumber(accessLocation);
    }
    
    // 生成访问的唯一标识
    std::string accessKey = varName + ":" + 
                           funcName + ":" + 
                           accessType + ":" +
                           accessFilePathStr + ":" + 
                           std::to_string(accessLine);

    // 检查是否已经记录过这个访问
    if (recordedAccesses_.find(accessKey) != recordedAccesses_.end()) {
        return;
    }

    // 直接插入访问关系
    dbManager_.insertAccessRelation(varName, funcName, accessType, accessFilePathStr, accessLine);
    recordedAccesses_[accessKey] = true;
}

std::string AccessHandler::determineAccessType(clang::Expr* expr, clang::FunctionDecl *CurrentFunction) {
    if (utils.isAssignmentLHS(expr)) {
        return "write";
    }
    
    if (utils.isIncrementDecrement(expr)) {
        return "write";
    }

    return "read";
}

void AccessHandler::handleDeclRefExpr(clang::DeclRefExpr *DRE, clang::FunctionDecl *CurrentFunction, 
                                      const std::string& currentFuncName) {
    if (!DRE || currentFuncName.empty()) {
        return;
    }

    clang::ValueDecl *VD = DRE->getDecl();
    if (auto *VarD = llvm::dyn_cast<clang::VarDecl>(VD)) {
        if (VarD->hasGlobalStorage()) {
            std::string accessType = determineAccessType(DRE, CurrentFunction);
            recordAccess(VarD, accessType, CurrentFunction, currentFuncName, DRE->getLocation());
        }
    }
}

void AccessHandler::handlePotentialWriteViaBinaryOperator(clang::BinaryOperator *BO, 
                                                          clang::FunctionDecl *CurrentFunction, 
                                                          const std::string& currentFuncName) {
    // 不需要在这里处理，DeclRefExpr 会处理
    return;
}

void AccessHandler::handleUnaryOperator(clang::UnaryOperator *UO, clang::FunctionDecl *CurrentFunction, 
                                        const std::string& currentFuncName) {
    // 不需要在这里处理，DeclRefExpr 会处理
    return;
}

void AccessHandler::handleMemberExpr(clang::MemberExpr *ME, clang::FunctionDecl *CurrentFunction, 
                                     const std::string& currentFuncName) {
    if (!ME || currentFuncName.empty()) return;

    clang::ValueDecl *memberDecl = ME->getMemberDecl();
    if (!memberDecl) return;

    clang::Expr *base = ME->getBase()->IgnoreParenImpCasts();
    clang::VarDecl *baseGlobalVar = nullptr;

    while (base) {
        if (auto *DRE = llvm::dyn_cast<clang::DeclRefExpr>(base)) {
            if (auto *VD = llvm::dyn_cast<clang::VarDecl>(DRE->getDecl())) {
                if (VD->hasGlobalStorage()) {
                    baseGlobalVar = VD;
                    break;
                }
            }
            break; 
        } else if (auto *baseME_iter = llvm::dyn_cast<clang::MemberExpr>(base)) {
            base = baseME_iter->getBase()->IgnoreParenImpCasts(); 
        } else if (auto *implicitCast = llvm::dyn_cast<clang::ImplicitCastExpr>(base)){
            base = implicitCast->getSubExpr()->IgnoreParenImpCasts();
        } else {
            break; 
        }
    }

    if (baseGlobalVar) {
        std::string accessType = determineAccessType(ME, CurrentFunction);
        recordAccess(baseGlobalVar, accessType, CurrentFunction, currentFuncName, ME->getMemberLoc());
    }
}