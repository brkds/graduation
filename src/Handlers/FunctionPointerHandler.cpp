#include "FunctionPointerHandler.h"
#include <clang/AST/Expr.h>
#include <clang/Basic/SourceManager.h>

FunctionPointerHandler::FunctionPointerHandler(clang::ASTContext *Ctx, DatabaseManager &dbManager, ASTUtils &utils)
    : Context(Ctx), dbManager_(dbManager), utils_(utils) {}

void FunctionPointerHandler::handleVarDecl(clang::VarDecl *VD) {
    if (!VD || !VD->hasInit() || !Context) return;

    clang::Expr *Init = VD->getInit();
    if (!Init) return;
    
    Init = Init->IgnoreParenCasts();
    if (!Init) return;

    if (auto *FuncRef = clang::dyn_cast<clang::DeclRefExpr>(Init)) {
        if (!FuncRef->getDecl()) return;
        
        if (auto *FD = clang::dyn_cast<clang::FunctionDecl>(FuncRef->getDecl())) {
            if (!utils_.isUserCodeVariable(VD) || !utils_.isUserCodeFunction(FD)) {
                return;
            }
            
            clang::SourceManager &SM = Context->getSourceManager();
            if (!Init->getBeginLoc().isValid()) return;
            
            clang::SourceLocation Loc = SM.getExpansionLoc(Init->getBeginLoc());
            if (!Loc.isValid()) return;

            std::string pointerName = VD->getNameAsString();
            
            // 先插入函数（如果不存在）
            std::string funcName = FD->getNameAsString();
            std::string funcFilePath;
            int startLine = 0, startCol = 0, endLine = 0, endCol = 0;
            
            if (!FD->getBeginLoc().isValid() || !FD->getEndLoc().isValid()) return;
            
            utils_.getSourceLocationDetails(FD->getBeginLoc(), SM, funcFilePath, startLine, startCol);
            utils_.getSourceLocationDetails(FD->getEndLoc(), SM, funcFilePath, endLine, endCol);
            
            if (funcFilePath == "invalid_location") {
                return;
            }
            
            if (funcFilePath.empty() || startLine <= 0 || endLine <= 0) return;

            std::string params = "(";
            if (FD->getNumParams() == 0) {
                params = "()";
            } else {
                for (unsigned i = 0; i < FD->getNumParams(); ++i) {
                    const clang::ParmVarDecl *PVD = FD->getParamDecl(i);
                    params += PVD->getType().getAsString();
                    if (i < FD->getNumParams() - 1) {
                        params += ", ";
                    }
                }
                params += ")";
            }
            
            // 直接插入函数，不获取 ID
            dbManager_.insertFunction(
                funcName,
                FD->getReturnType().getAsString(),
                params,
                funcFilePath,
                startLine,
                startCol,
                endLine,
                endCol,
                FD->getStorageClass() == clang::SC_Static
            );

            // 插入函数指针关系（直接用名字）
            std::string filePath = utils_.getAbsoluteFilePath(SM, Loc);
            int lineNumber = SM.getSpellingLineNumber(Loc);
            
            if (!filePath.empty() && lineNumber > 0) {
                dbManager_.insertFunctionPointer(pointerName, funcName, filePath, lineNumber);
            }
        }
    }
    
    clang::QualType varType = VD->getType();
    if (varType->isFunctionPointerType() || 
        (varType.getTypePtr()->isTypedefNameType() && 
         varType.getCanonicalType()->isFunctionPointerType())) {
        analyzeFunctionPointerAssignment(VD, Init);
    }
}

void FunctionPointerHandler::handleBinaryOperator(clang::BinaryOperator *BO) {
    if (!BO || !BO->isAssignmentOp() || !Context) return;

    clang::Expr *LHS = BO->getLHS();
    clang::Expr *RHS = BO->getRHS();
    if (!LHS || !RHS) return;
    
    if (const auto *declRef = llvm::dyn_cast<clang::DeclRefExpr>(LHS->IgnoreImpCasts())) {
        if (const auto *varDecl = llvm::dyn_cast<clang::VarDecl>(declRef->getDecl())) {
            clang::QualType varType = varDecl->getType();
            if (varType->isFunctionPointerType() || 
                (varType.getTypePtr()->isTypedefNameType() && 
                 varType.getCanonicalType()->isFunctionPointerType())) {
                analyzeFunctionPointerAssignment(varDecl, RHS);
            }
        }
    }
    
    if (const auto *memberExpr = llvm::dyn_cast<clang::MemberExpr>(LHS->IgnoreImpCasts())) {
        if (const auto *fieldDecl = llvm::dyn_cast<clang::FieldDecl>(memberExpr->getMemberDecl())) {
            clang::QualType fieldType = fieldDecl->getType();
            if (fieldType->isFunctionPointerType() || 
                (fieldType.getTypePtr()->isTypedefNameType() && 
                 fieldType.getCanonicalType()->isFunctionPointerType())) {
                std::string fullPointerName = utils_.getFullPointerName(LHS);
                if (!fullPointerName.empty()) {
                    analyzeMemberFunctionPointerAssignment(fullPointerName, fieldDecl, RHS);
                    return;
                }
            }
        }
    }

    RHS = RHS->IgnoreParenCasts();
    if (!RHS) return;

    if (auto *FuncRef = clang::dyn_cast<clang::DeclRefExpr>(RHS)) {
        if (!FuncRef->getDecl()) return;
        
        if (auto *FD = clang::dyn_cast<clang::FunctionDecl>(FuncRef->getDecl())) {
            clang::SourceManager &SM = Context->getSourceManager();
            if (!RHS->getBeginLoc().isValid()) return;
            
            clang::SourceLocation Loc = SM.getExpansionLoc(RHS->getBeginLoc());
            if (!Loc.isValid()) return;

            std::string funcName = FD->getNameAsString();
            std::string funcFilePath;
            int startLine = 0, startCol = 0, endLine = 0, endCol = 0;
            
            if (!FD->getBeginLoc().isValid() || !FD->getEndLoc().isValid()) return;
            
            utils_.getSourceLocationDetails(FD->getBeginLoc(), SM, funcFilePath, startLine, startCol);
            utils_.getSourceLocationDetails(FD->getEndLoc(), SM, funcFilePath, endLine, endCol);
            
            if (funcFilePath == "invalid_location") {
                return;
            }
            
            if (funcFilePath.empty() || startLine <= 0 || endLine <= 0) return;

            std::string params = "(";
            if (FD->getNumParams() == 0) {
                params = "()";
            } else {
                for (unsigned i = 0; i < FD->getNumParams(); ++i) {
                    const clang::ParmVarDecl *PVD = FD->getParamDecl(i);
                    params += PVD->getType().getAsString();
                    if (i < FD->getNumParams() - 1) {
                        params += ", ";
                    }
                }
                params += ")";
            }
            
            // 直接插入函数
            dbManager_.insertFunction(
                funcName,
                FD->getReturnType().getAsString(),
                params,
                funcFilePath,
                startLine,
                startCol,
                endLine,
                endCol,
                FD->getStorageClass() == clang::SC_Static
            );

            std::string pointerName = utils_.getFullPointerName(BO->getLHS());
            if (pointerName.empty()) return;
            
            std::string filePath = utils_.getAbsoluteFilePath(SM, Loc);
            int lineNumber = SM.getSpellingLineNumber(Loc);
            
            if (!filePath.empty() && lineNumber > 0) {
                // 直接用名字插入函数指针关系
                dbManager_.insertFunctionPointer(pointerName, funcName, filePath, lineNumber);
            }
        }
    }
}

void FunctionPointerHandler::analyzeFunctionPointerAssignment(const clang::NamedDecl *pointerDecl, const clang::Expr *rhs) {
    if (!pointerDecl || !rhs || !Context) return;
    
    std::string pointerName = pointerDecl->getNameAsString();
    rhs = rhs->IgnoreParenCasts();
    
    if (const auto *declRef = llvm::dyn_cast<clang::DeclRefExpr>(rhs)) {
        if (const auto *funcDecl = llvm::dyn_cast<clang::FunctionDecl>(declRef->getDecl())) {
            recordFunctionPointer(pointerName, funcDecl, rhs->getBeginLoc());
        }
    }
    else if (const auto *unaryOp = llvm::dyn_cast<clang::UnaryOperator>(rhs)) {
        if (unaryOp->getOpcode() == clang::UO_AddrOf) {
            if (const auto *declRef = llvm::dyn_cast<clang::DeclRefExpr>(unaryOp->getSubExpr())) {
                if (const auto *funcDecl = llvm::dyn_cast<clang::FunctionDecl>(declRef->getDecl())) {
                    recordFunctionPointer(pointerName, funcDecl, rhs->getBeginLoc());
                }
            }
        }
    }
}

void FunctionPointerHandler::analyzeMemberFunctionPointerAssignment(const std::string &fullPointerName,
                                                                   const clang::FieldDecl *fieldDecl,
                                                                   const clang::Expr *rhs) {
    if (!fieldDecl || !rhs || !Context) return;
    
    rhs = rhs->IgnoreParenCasts();
    
    if (const auto *declRef = llvm::dyn_cast<clang::DeclRefExpr>(rhs)) {
        if (const auto *funcDecl = llvm::dyn_cast<clang::FunctionDecl>(declRef->getDecl())) {
            recordFunctionPointer(fullPointerName, funcDecl, rhs->getBeginLoc());
        }
    }
    else if (const auto *unaryOp = llvm::dyn_cast<clang::UnaryOperator>(rhs)) {
        if (unaryOp->getOpcode() == clang::UO_AddrOf) {
            if (const auto *declRef = llvm::dyn_cast<clang::DeclRefExpr>(unaryOp->getSubExpr())) {
                if (const auto *funcDecl = llvm::dyn_cast<clang::FunctionDecl>(declRef->getDecl())) {
                    recordFunctionPointer(fullPointerName, funcDecl, rhs->getBeginLoc());
                }
            }
        }
    }
}

void FunctionPointerHandler::recordFunctionPointer(const std::string &pointerName, 
                                                  const clang::FunctionDecl *funcDecl, 
                                                  clang::SourceLocation loc) {
    if (!funcDecl || !Context) return;
    
    if (!utils_.isUserCodeFunction(funcDecl)) {
        return;
    }
    
    clang::SourceManager &SM = Context->getSourceManager();
    
    std::string funcName = funcDecl->getNameAsString();
    std::string funcFilePath;
    int startLine = 0, startCol = 0, endLine = 0, endCol = 0;
    
    if (!funcDecl->getBeginLoc().isValid() || !funcDecl->getEndLoc().isValid()) return;
    
    utils_.getSourceLocationDetails(funcDecl->getBeginLoc(), SM, funcFilePath, startLine, startCol);
    utils_.getSourceLocationDetails(funcDecl->getEndLoc(), SM, funcFilePath, endLine, endCol);
    
    if (funcFilePath == "invalid_location") {
        return;
    }
    
    if (funcFilePath.empty() || startLine <= 0 || endLine <= 0) return;

    std::string params = "(";
    if (funcDecl->getNumParams() == 0) {
        params = "()";
    } else {
        for (unsigned i = 0; i < funcDecl->getNumParams(); ++i) {
            const clang::ParmVarDecl *PVD = funcDecl->getParamDecl(i);
            params += PVD->getType().getAsString();
            if (i < funcDecl->getNumParams() - 1) {
                params += ", ";
            }
        }
        params += ")";
    }
    
    // 直接插入函数
    dbManager_.insertFunction(
        funcName,
        funcDecl->getReturnType().getAsString(),
        params,
        funcFilePath,
        startLine,
        startCol,
        endLine,
        endCol,
        funcDecl->getStorageClass() == clang::SC_Static
    );

    if (loc.isValid()) {
        clang::SourceLocation expandedLoc = SM.getExpansionLoc(loc);
        if (expandedLoc.isValid()) {
            std::string filePath = utils_.getAbsoluteFilePath(SM, expandedLoc);
            int lineNumber = SM.getSpellingLineNumber(expandedLoc);
            
            if (!filePath.empty() && lineNumber > 0) {
                // 直接用名字插入函数指针关系
                dbManager_.insertFunctionPointer(pointerName, funcName, filePath, lineNumber);
            }
        }
    }
}