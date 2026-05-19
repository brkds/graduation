#ifndef KERNEL_AST_VISITOR_H
#define KERNEL_AST_VISITOR_H

#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/AST/Decl.h"
#include "clang/AST/Expr.h"
#include "Utils/DatabaseManager.h"
#include "Handlers/FuncHandler.h"
#include "Handlers/GlobalVarHandler.h"
#include "Handlers/AccessHandler.h"
#include "Handlers/CallsHandler.h"
#include "Handlers/DataPointerHandler.h"
#include "Handlers/FunctionPointerHandler.h"
#include "Utils/ASTUtils.h"
#include <memory>
#include <set>
#include <string>

class KernelASTVisitor : public clang::RecursiveASTVisitor<KernelASTVisitor> {
public:
    KernelASTVisitor(clang::ASTContext *Ctx, DatabaseManager &dbManager, 
                     const std::set<std::string> &userCodePaths,
                     bool enableCallAnalysis = true);
    ~KernelASTVisitor();

    // 重写 TraverseFunctionDecl 以维护上下文
    bool TraverseFunctionDecl(clang::FunctionDecl *FD);
    
    // Visit 方法
    bool VisitFunctionDecl(clang::FunctionDecl *FD);
    bool VisitVarDecl(clang::VarDecl *VD);
    bool VisitDeclRefExpr(clang::DeclRefExpr *DRE);
    bool VisitBinaryOperator(clang::BinaryOperator *BO);
    bool VisitUnaryOperator(clang::UnaryOperator *UO);
    bool VisitMemberExpr(clang::MemberExpr *ME);
    bool VisitCallExpr(clang::CallExpr *CE);

private:
    DatabaseManager &dbManager_;
    std::unique_ptr<ASTUtils> utils_;
    bool enableCallAnalysis_;
    
    // 当前分析的函数上下文
    clang::FunctionDecl *currentFunctionAST_;
    std::string currentFunctionName_;
    
    // 已处理的函数集合（避免重复）
    std::set<clang::FunctionDecl*> processedFunctions_;
    
    // Handlers - 全部同时启用
    std::unique_ptr<FuncHandler> FuncH;
    std::unique_ptr<GlobalVarHandler> GlobalVarH;
    std::unique_ptr<AccessHandler> AccessH;
    std::unique_ptr<CallsHandler> CallsH;
    std::unique_ptr<DataPointerHandler> DataPtrH;
    std::unique_ptr<FunctionPointerHandler> FuncPtrH;
};

#endif // KERNEL_AST_VISITOR_H