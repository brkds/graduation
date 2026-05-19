#ifndef AST_CONSUMER_H
#define AST_CONSUMER_H

#include <clang/AST/ASTConsumer.h>
#include <clang/AST/ASTContext.h>
#include "ASTVisitor.h"
#include "Utils/DatabaseManager.h"
#include <set>
#include <string>

class KernelASTConsumer : public clang::ASTConsumer {
public:
    KernelASTConsumer(clang::ASTContext *Ctx, DatabaseManager &dbManager,
                      const std::set<std::string> &userCodePaths,
                      bool enableCallAnalysis = true);

    void HandleTranslationUnit(clang::ASTContext &Ctx) override;

private:
    DatabaseManager &dbManager_;
    KernelASTVisitor Visitor;
};

#endif // AST_CONSUMER_H