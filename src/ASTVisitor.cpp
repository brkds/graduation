#include "ASTVisitor.h"
#include "clang/AST/ASTContext.h"
#include "clang/AST/Decl.h"
#include "clang/AST/Expr.h"
#include <iostream>

KernelASTVisitor::KernelASTVisitor(clang::ASTContext *Ctx, DatabaseManager &dbManager, 
                                   const std::set<std::string> &userCodePaths,
                                   bool enableCallAnalysis)
    : currentFunctionName_(""),
      dbManager_(dbManager),
      currentFunctionAST_(nullptr),
      enableCallAnalysis_(enableCallAnalysis)
{
    utils_ = std::make_unique<ASTUtils>(*Ctx);
    utils_->setUserCodePaths(userCodePaths);
    
    // 所有 handlers 同时启用（单遍遍历）
    FuncH = std::make_unique<FuncHandler>(Ctx, dbManager_, *utils_);
    GlobalVarH = std::make_unique<GlobalVarHandler>(Ctx, dbManager_, *utils_);
    AccessH = std::make_unique<AccessHandler>(Ctx, dbManager_, *utils_);
    DataPtrH = std::make_unique<DataPointerHandler>(Ctx, dbManager_, *utils_);
    FuncPtrH = std::make_unique<FunctionPointerHandler>(Ctx, dbManager_, *utils_);
    
    if (enableCallAnalysis_) {
        CallsH = std::make_unique<CallsHandler>(Ctx, dbManager_, *utils_);
    }
}

KernelASTVisitor::~KernelASTVisitor() = default;

bool KernelASTVisitor::TraverseFunctionDecl(clang::FunctionDecl *FD) {
    if (!FD) return true;

    // 避免重复处理同一个函数
    if (processedFunctions_.find(FD) != processedFunctions_.end()) {
        return true;
    }

    // 保存上下文
    clang::FunctionDecl *SavedFunctionAST = currentFunctionAST_;
    std::string savedFunctionName = currentFunctionName_;

    currentFunctionAST_ = FD;
    currentFunctionName_ = FD->getNameAsString();
    
    // 1. 处理函数定义（节点）
    if (FuncH) {
        FuncH->handleFunctionDecl(FD);
    }

    // 2. 遍历函数体，触发各种 Visit 回调（边）
    //    在遍历过程中会自动调用 VisitDeclRefExpr、VisitCallExpr 等方法
    bool result = clang::RecursiveASTVisitor<KernelASTVisitor>::TraverseFunctionDecl(FD);

    // 标记为已处理
    processedFunctions_.insert(FD);

    // 恢复上下文
    currentFunctionAST_ = SavedFunctionAST;
    currentFunctionName_ = savedFunctionName;
    
    return result;
}

bool KernelASTVisitor::VisitFunctionDecl(clang::FunctionDecl *FD) {
    // 函数声明也会走到这里，但我们只在 TraverseFunctionDecl 中处理函数定义
    // 这里不需要额外处理
    return true;
}

bool KernelASTVisitor::VisitVarDecl(clang::VarDecl *VD) {
    if (!VD) return true;
    
    // 只处理全局变量
    if (VD->hasGlobalStorage()) {
        // 1. 处理全局变量定义（节点）
        if (GlobalVarH) {
            GlobalVarH->handleVarDecl(VD);
        }
        // 2. 处理指针相关（边）
        if (DataPtrH) {
            DataPtrH->handleVarDecl(VD);
        }
        if (FuncPtrH) {
            FuncPtrH->handleVarDecl(VD);
        }
    }
    return true;
}

bool KernelASTVisitor::VisitDeclRefExpr(clang::DeclRefExpr *DRE) {
    if (!DRE) return true;
    
    // 有当前函数上下文时才记录访问关系
    if (currentFunctionAST_ && !currentFunctionName_.empty() && AccessH) {
        AccessH->handleDeclRefExpr(DRE, currentFunctionAST_, currentFunctionName_);
    }
    return true;
}

bool KernelASTVisitor::VisitBinaryOperator(clang::BinaryOperator *BO) {
    if (!BO) return true;
    
    if (currentFunctionAST_ && !currentFunctionName_.empty()) {
        // 处理赋值操作（写访问）
        if (AccessH) {
            AccessH->handlePotentialWriteViaBinaryOperator(BO, currentFunctionAST_, currentFunctionName_);
        }
        // 处理指针赋值
        if (DataPtrH) {
            DataPtrH->handleBinaryOperator(BO);
        }
        if (FuncPtrH) {
            FuncPtrH->handleBinaryOperator(BO);
        }
    }
    return true;
}

bool KernelASTVisitor::VisitUnaryOperator(clang::UnaryOperator *UO) {
    if (!UO) return true;
    
    // 处理自增/自减等操作（读写访问）
    if (currentFunctionAST_ && !currentFunctionName_.empty() && AccessH) {
        AccessH->handleUnaryOperator(UO, currentFunctionAST_, currentFunctionName_);
    }
    return true;
}

bool KernelASTVisitor::VisitMemberExpr(clang::MemberExpr *ME) {
    if (!ME) return true;
    
    // 处理结构体/类成员访问
    if (currentFunctionAST_ && !currentFunctionName_.empty() && AccessH) {
        AccessH->handleMemberExpr(ME, currentFunctionAST_, currentFunctionName_);
    }
    return true;
}

bool KernelASTVisitor::VisitCallExpr(clang::CallExpr *CE) {
    if (!CE) return true;
    
    // 处理函数调用
    if (enableCallAnalysis_ && CallsH && currentFunctionAST_ && !currentFunctionName_.empty()) {
        CallsH->handleCallExpr(CE, currentFunctionName_, currentFunctionAST_);
    }
    return true;
}