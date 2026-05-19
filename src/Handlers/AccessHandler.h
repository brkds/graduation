#ifndef ACCESS_HANDLER_H
#define ACCESS_HANDLER_H

#include "Utils/ASTUtils.h"
#include <clang/AST/ASTContext.h>
#include "Utils/DatabaseManager.h"
#include <unordered_map>
#include <string>

class AccessHandler {
public:
    AccessHandler(clang::ASTContext *Ctx, DatabaseManager &dbManager, ASTUtils &utils);
    
    // 参数从 long long currentFuncDbId 改为 const std::string& currentFuncName
    void handleDeclRefExpr(clang::DeclRefExpr *DRE, clang::FunctionDecl *CurrentFunction, 
                           const std::string& currentFuncName);
    void handlePotentialWriteViaBinaryOperator(clang::BinaryOperator *BO, clang::FunctionDecl *CurrentFunction, 
                                               const std::string& currentFuncName);
    void handleUnaryOperator(clang::UnaryOperator *UO, clang::FunctionDecl *CurrentFunction, 
                             const std::string& currentFuncName);
    void handleMemberExpr(clang::MemberExpr *ME, clang::FunctionDecl *CurrentFunction, 
                          const std::string& currentFuncName);

private:
    void recordAccess(clang::VarDecl *varDecl, const std::string& accessType, 
                      clang::FunctionDecl *CurrentFunction, const std::string& funcName, 
                      clang::SourceLocation accessLocation);

    clang::ASTContext *Context;
    DatabaseManager &dbManager_;
    ASTUtils &utils;

    std::string determineAccessType(clang::Expr *E, clang::FunctionDecl *CurrentFunction);
    
    // 用于记录已处理的访问，避免重复
    // key: varName:funcName:accessType:filePath:line
    std::unordered_map<std::string, bool> recordedAccesses_;
};

#endif // ACCESS_HANDLER_H