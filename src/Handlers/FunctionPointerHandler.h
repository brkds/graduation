#ifndef FUNCTION_POINTER_HANDLER_H
#define FUNCTION_POINTER_HANDLER_H

#include "Utils/ASTUtils.h"
#include "Utils/DatabaseManager.h"
#include <clang/AST/ASTContext.h>

class FunctionPointerHandler {
public:
    FunctionPointerHandler(clang::ASTContext *Ctx, DatabaseManager &dbManager, ASTUtils &utils);
    void handleVarDecl(clang::VarDecl *VD);
    void handleBinaryOperator(clang::BinaryOperator *BO);

private:
    clang::ASTContext *Context;
    DatabaseManager &dbManager_;
    ASTUtils &utils_;
    
    // Helper function to analyze function pointer assignments
    void analyzeFunctionPointerAssignment(const clang::NamedDecl *pointerDecl, const clang::Expr *rhs);
    
    // Helper function to analyze member function pointer assignments with full name
    void analyzeMemberFunctionPointerAssignment(const std::string &fullPointerName,
                                               const clang::FieldDecl *fieldDecl,
                                               const clang::Expr *rhs);
    
    // Helper function to record function pointer relationship
    void recordFunctionPointer(const std::string &pointerName, 
                              const clang::FunctionDecl *funcDecl, 
                              clang::SourceLocation loc);
};

#endif // FUNCTION_POINTER_HANDLER_H