#ifndef DATA_POINTER_HANDLER_H
#define DATA_POINTER_HANDLER_H

#include <clang/AST/ASTContext.h>
#include <clang/AST/Decl.h>
#include <clang/AST/Expr.h>
#include "../Utils/DatabaseManager.h"
#include "../Utils/ASTUtils.h"

class DataPointerHandler {
public:
    DataPointerHandler(clang::ASTContext *Ctx, DatabaseManager &dbManager, ASTUtils &utils);
    void handleVarDecl(clang::VarDecl *VD);
    void handleBinaryOperator(clang::BinaryOperator *BO);

private:
    clang::ASTContext *Context;
    DatabaseManager &dbManager_;
    ASTUtils &utils_;
    
    // Helper function to filter out compiler/kernel infrastructure symbols
    bool shouldFilterSymbol(const std::string& name);
    
    // Helper function to analyze pointer assignments
    void analyzePointerAssignment(const clang::NamedDecl *pointerDecl, const clang::Expr *rhs);
    
    // Helper function to analyze member pointer assignments with full name
    void analyzeMemberPointerAssignment(const std::string &fullPointerName,
                                       const clang::FieldDecl *fieldDecl,
                                       const clang::Expr *rhs);
    
    // Helper function to record pointer to variable relationship
    void recordPointerToVariable(const std::string &pointerName, 
                                const clang::VarDecl *varDecl, 
                                clang::SourceLocation loc);
};

#endif // DATA_POINTER_HANDLER_H