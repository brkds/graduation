#ifndef CALLS_HANDLER_H
#define CALLS_HANDLER_H

#include "clang/AST/Expr.h"
#include "clang/AST/Decl.h"
#include "clang/AST/ASTContext.h"
#include "Utils/DatabaseManager.h"
#include "Utils/ASTUtils.h"
#include <string>

class CallsHandler {
public:
    CallsHandler(clang::ASTContext *Ctx, DatabaseManager &dbManager, ASTUtils &utils);
    
    // 参数从 long long callerFuncDbId 改为 const std::string& callerName
    void handleCallExpr(clang::CallExpr *CE, const std::string& callerName, 
                        clang::FunctionDecl *currentFunction = nullptr);

private:
    clang::ASTContext *context_;
    DatabaseManager &dbManager_;
    ASTUtils &utils_;
    
    std::string getParamsString(const clang::FunctionDecl *FD);
    std::string generateFunctionSignature(const clang::FunctionDecl *FD);
};

#endif // CALLS_HANDLER_H