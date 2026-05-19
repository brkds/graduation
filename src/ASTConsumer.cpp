#include "ASTConsumer.h"
#include "Utils/DatabaseManager.h"

KernelASTConsumer::KernelASTConsumer(clang::ASTContext *Ctx, DatabaseManager &dbManager, 
                                     const std::set<std::string> &userCodePaths,
                                     bool enableCallAnalysis)
    : dbManager_(dbManager), 
      Visitor(Ctx, dbManager_, userCodePaths, enableCallAnalysis) {
}

void KernelASTConsumer::HandleTranslationUnit(clang::ASTContext &Ctx) {
    Visitor.TraverseDecl(Ctx.getTranslationUnitDecl());
}