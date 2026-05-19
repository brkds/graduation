#include "Handlers/FuncHandler.h"
#include "Utils/ASTUtils.h"
#include <clang/AST/Decl.h>
#include <clang/AST/Stmt.h>
#include <clang/Lex/Lexer.h>
#include <llvm/Support/FileSystem.h>
#include <llvm/Support/Path.h>
#include <iostream>

FuncHandler::FuncHandler(clang::ASTContext *Ctx, DatabaseManager &dbManager, ASTUtils &utils)
    : Context(Ctx), dbManager_(dbManager), utils_(utils) {} 

std::string FuncHandler::getParamsString(clang::FunctionDecl *FD) {
    if (FD->getNumParams() == 0) {
        return "()";
    }
    
    std::string paramsStr = "(";
    for (unsigned i = 0; i < FD->getNumParams(); ++i) {
        clang::ParmVarDecl *PVD = FD->getParamDecl(i);
        paramsStr += PVD->getType().getAsString();
        if (i < FD->getNumParams() - 1) {
            paramsStr += ", ";
        }
    }
    paramsStr += ")";
    return paramsStr;
}

std::string FuncHandler::getSourceText(clang::SourceRange SR) {
    const clang::SourceManager &SM = Context->getSourceManager();
    const clang::LangOptions &LO = Context->getLangOpts();
    if (SR.isInvalid() || !SM.isLocalSourceLocation(SR.getBegin()) || !SM.isLocalSourceLocation(SR.getEnd())){
        return "";
    }
    clang::SourceLocation B = SM.getSpellingLoc(SR.getBegin());
    clang::SourceLocation E = SM.getSpellingLoc(SR.getEnd());
    if (B.isInvalid() || E.isInvalid()) return "";

    llvm::StringRef ref = clang::Lexer::getSourceText(
        clang::CharSourceRange::getTokenRange(clang::SourceRange(B,E)), SM, LO);
    return ref.str();
}

void FuncHandler::handleFunctionDecl(clang::FunctionDecl *FD) {
    if (!FD || !FD->getIdentifier()) { 
        return; 
    }

    if (!utils_.isUserCodeFunction(FD)) {
        return;
    }

    std::string funcName = FD->getNameInfo().getName().getAsString();
    clang::SourceManager &SM = Context->getSourceManager();
    
    std::string filePath;
    int startLine = 0, startCol = 0, endLine = 0, endCol = 0;

    clang::SourceLocation nameStart = FD->getLocation();
    utils_.getSourceLocationDetails(nameStart, SM, filePath, startLine, startCol);

    if (clang::Stmt *Body = FD->getBody()) {
        clang::SourceLocation bodyEnd = Body->getEndLoc();
        std::string endFilePath;
        utils_.getSourceLocationDetails(bodyEnd, SM, endFilePath, endLine, endCol);
    } else {
        clang::SourceLocation declEnd = FD->getEndLoc();
        std::string endFilePath;
        utils_.getSourceLocationDetails(declEnd, SM, endFilePath, endLine, endCol);
    }

    if (filePath == "invalid_location") {
        return;
    }

    std::string returnType = FD->getReturnType().getAsString();
    std::string params = getParamsString(FD);
    bool isStatic = FD->getStorageClass() == clang::SC_Static;
    
    // 直接插入，不关心返回值
    dbManager_.insertFunction(funcName, returnType, params, filePath, 
                              startLine, startCol, endLine, endCol, isStatic);
}