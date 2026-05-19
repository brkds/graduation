#ifndef AST_UTILS_H
#define AST_UTILS_H

#include <clang/AST/ASTContext.h>
#include <clang/Basic/SourceManager.h> // Required for SourceManager and SourceLocation
#include <clang/Lex/Lexer.h> // Required for Lexer
#include <string> // Required for std::string
#include <set> // Required for user code path tracking

class ASTUtils {
public:
    ASTUtils(clang::ASTContext &Ctx); // Changed to reference
    bool isAssignmentLHS(const clang::Expr *E);
    bool isIncrementDecrement(const clang::Expr *E);  // 新增方法
    std::string getPointerName(clang::Expr *E);
    std::string getAbsoluteFilePath(clang::SourceManager &SM, clang::SourceLocation Loc) const;
    std::string getFullPointerName(clang::Expr *E); // New method for complete pointer expression
    // New function to get detailed location info
    void getSourceLocationDetails(clang::SourceLocation loc, clang::SourceManager &SM, 
                                  std::string &filePath, int &lineNumber, int &columnNumber);
    // Added getSourceText method
    std::string getSourceText(clang::SourceRange SR, clang::SourceManager &SM, const clang::LangOptions &LO);
    
    // 新增：用户代码过滤相关方法
    void setUserCodePaths(const std::set<std::string> &userPaths);
    void addUserCodePath(const std::string &path);
    bool isFromUserCode(clang::SourceLocation loc, clang::SourceManager &SM) const;
    bool isFromUserCode(const clang::Decl *decl) const;
    
    // 改进的过滤方法，结合多种策略
    bool isUserCodeFunction(const clang::FunctionDecl *FD) const;
    bool isUserCodeVariable(const clang::VarDecl *VD) const;
    bool isUserCodeLocation(clang::SourceLocation loc, clang::SourceManager &SM) const;
    
    // 新增：获取SourceManager的方法
    clang::SourceManager& getSourceManager() const;

private:
    clang::ASTContext &Context; // Changed to reference
    std::set<std::string> userCodePaths_; // 存储用户代码的路径集合
};

#endif // AST_UTILS_H