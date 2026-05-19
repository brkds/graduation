#ifndef GLOBAL_VAR_HANDLER_H
#define GLOBAL_VAR_HANDLER_H

#include <clang/AST/ASTContext.h>
#include "Utils/DatabaseManager.h"
#include "Utils/ASTUtils.h"

class GlobalVarHandler {
public:
    GlobalVarHandler(clang::ASTContext *context, DatabaseManager &dbManager, ASTUtils &utils);
    void handleVarDecl(clang::VarDecl *VD);

private:
    clang::ASTContext *context_;
    DatabaseManager &dbManager_;
    ASTUtils &utils_;
};

#endif // GLOBAL_VAR_HANDLER_H