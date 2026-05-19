#ifndef FUNC_HANDLER_H
#define FUNC_HANDLER_H

#include <clang/AST/ASTContext.h>
#include "Utils/DatabaseManager.h"
#include "Utils/ASTUtils.h"

class FuncHandler {
public:
    FuncHandler(clang::ASTContext *Ctx, DatabaseManager &dbManager, ASTUtils &utils);
    
    // 返回类型从 long long 改为 void
    void handleFunctionDecl(clang::FunctionDecl *FD);

private:
    clang::ASTContext *Context;
    DatabaseManager &dbManager_;
    ASTUtils &utils_;
    
    std::string getFunctionSignature(clang::FunctionDecl *FD);
    std::string getParamsString(clang::FunctionDecl *FD);
    std::string getSourceText(clang::SourceRange SR);
};

#endif // FUNC_HANDLER_H