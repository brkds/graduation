#ifndef FILE_HANDLER_H
#define FILE_HANDLER_H

#include "ASTConsumer.h"
#include "Utils/DatabaseManager.h"
#include <clang/Tooling/CommonOptionsParser.h>
#include <string>
#include <vector>
#include <set>

// 删除 AnalysisConfig.h 的依赖，因为不再需要分遍配置

class FileHandler {
public:
    FileHandler(DatabaseManager &dbManager, clang::tooling::CommonOptionsParser &optionsParser, 
                bool enableCallAnalysis = true, bool singleThreadMode = false);

    // 运行分析工具，处理所有源文件（单遍遍历）
    int runAnalysis(unsigned threadCount = 0);

private:
    // 计算输入根目录（用于相对路径）
    void computeInputRootDir(const std::vector<std::string> &sourcePaths);

    // 收集源文件路径（支持目录递归）
    std::vector<std::string> getSourceFiles(const std::vector<std::string> &sourcePaths);
    
    // 收集用户代码路径
    std::set<std::string> collectUserCodePaths(const std::vector<std::string> &sourcePaths);

    // 分析单个源文件
    bool analyzeFile(const std::string &file);

    DatabaseManager &dbManager_;
    std::string inputRootDir;
    clang::tooling::CommonOptionsParser &optionsParser;
    std::set<std::string> userCodePaths_;
    
    bool enableCallAnalysis_;
    bool singleThreadMode_;
};

#endif // FILE_HANDLER_H