#include "FileHandler.h"
#include "Utils/DatabaseManager.h"
#include "ASTConsumer.h"
#include <clang/Tooling/Tooling.h>
#include <clang/Frontend/CompilerInstance.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/Support/Path.h>
#include <iostream>
#include <iomanip>
#include <vector>
#include <future>
#include <atomic>
#include <thread>
#include <algorithm>
#include <chrono>
#include <mutex>

#include <experimental/filesystem>
namespace fs = std::experimental::filesystem;

FileHandler::FileHandler(DatabaseManager &dbManager, clang::tooling::CommonOptionsParser &optionsParser,
                         bool enableCallAnalysis, bool singleThreadMode)
    : dbManager_(dbManager), optionsParser(optionsParser),
      enableCallAnalysis_(enableCallAnalysis), singleThreadMode_(singleThreadMode) {
    computeInputRootDir(optionsParser.getSourcePathList());
    userCodePaths_ = collectUserCodePaths(optionsParser.getSourcePathList());
}

void FileHandler::computeInputRootDir(const std::vector<std::string> &sourcePaths) {
    inputRootDir = ".";
    if (!sourcePaths.empty()) {
        const std::string &firstPathStr = sourcePaths.front();
        fs::path firstPath(firstPathStr);
        if (fs::is_directory(firstPath)) {
            inputRootDir = fs::absolute(firstPath).string();
        } else if (fs::exists(firstPath)){
            inputRootDir = fs::absolute(firstPath).parent_path().string();
        } else {
            fs::path p(firstPathStr);
            if (p.has_parent_path()) {
                inputRootDir = fs::absolute(p.parent_path()).string();
            } else {
                inputRootDir = fs::absolute(p).string();
            }
        }
    }
}

std::vector<std::string> FileHandler::getSourceFiles(const std::vector<std::string> &sourcePaths) {
    std::vector<std::string> files;
    for (const auto &path_str : sourcePaths) {
        fs::path p(path_str);
        fs::path absolute_p = fs::absolute(p);

        if (fs::is_directory(absolute_p)) {
            try {
                for (const auto &entry : fs::recursive_directory_iterator(absolute_p)) {
                    if (fs::is_regular_file(entry.status())) {
                        std::string ext = entry.path().extension().string();
                        if (ext == ".c" || ext == ".cc" || ext == ".cpp" || ext == ".h" || ext == ".hpp") {
                            files.push_back(entry.path().string());
                        }
                    }
                }
            } catch (const fs::filesystem_error &e) {
                llvm::errs() << "Error accessing directory " << absolute_p.string() << ": " << e.what() << "\n";
            }
        } else if (fs::is_regular_file(absolute_p)) {
            files.push_back(absolute_p.string());
        } else {
            llvm::errs() << "Warning: Source path " << path_str << " is neither a file nor a directory. Skipping.\n";
        }
    }
    return files;
}

std::set<std::string> FileHandler::collectUserCodePaths(const std::vector<std::string> &sourcePaths) {
    std::set<std::string> userPaths;
    
    for (const auto &path_str : sourcePaths) {
        fs::path p(path_str);
        fs::path absolute_p = fs::absolute(p);
        
        if (fs::is_directory(absolute_p)) {
            userPaths.insert(absolute_p.string());
        } else if (fs::is_regular_file(absolute_p)) {
            userPaths.insert(absolute_p.parent_path().string());
        }
    }
    
    if (!inputRootDir.empty() && inputRootDir != ".") {
        userPaths.insert(inputRootDir);
    }
    
    return userPaths;
}

bool FileHandler::analyzeFile(const std::string &file) {
    std::vector<std::string> currentFile = {file};

    clang::tooling::ClangTool SingleFileTool(optionsParser.getCompilations(), currentFile);

    class SilentDiagConsumer : public clang::DiagnosticConsumer {
    public:
        void HandleDiagnostic(clang::DiagnosticsEngine::Level DiagLevel,
                              const clang::Diagnostic &Info) override {
            // 保持静默
        }
    } DiagConsumer;
    SingleFileTool.setDiagnosticConsumer(&DiagConsumer);

    // 简化的 FrontendAction，单遍遍历
    class KernelFrontendAction : public clang::ASTFrontendAction {
    public:
        KernelFrontendAction(DatabaseManager &dbMgr, const std::set<std::string> &userPaths, 
                             bool enableCallAnalysis) 
            : dbManager_(dbMgr), userCodePaths_(userPaths), enableCallAnalysis_(enableCallAnalysis) {}
        
        std::unique_ptr<clang::ASTConsumer> CreateASTConsumer(clang::CompilerInstance &CI, llvm::StringRef) override {
            return std::unique_ptr<clang::ASTConsumer>(
                new KernelASTConsumer(&CI.getASTContext(), dbManager_, userCodePaths_, enableCallAnalysis_));
        }
    private:
        DatabaseManager &dbManager_;
        const std::set<std::string> &userCodePaths_;
        bool enableCallAnalysis_;
    };

    class SimpleFrontendActionFactory : public clang::tooling::FrontendActionFactory {
    public:
        SimpleFrontendActionFactory(DatabaseManager &dbMgr, const std::set<std::string> &userPaths,
                                    bool enableCallAnalysis) 
            : dbManager_(dbMgr), userCodePaths_(userPaths), enableCallAnalysis_(enableCallAnalysis) {}
        
        std::unique_ptr<clang::FrontendAction> create() override {
            return std::make_unique<KernelFrontendAction>(dbManager_, userCodePaths_, enableCallAnalysis_);
        }
    private:
        DatabaseManager &dbManager_;
        const std::set<std::string> &userCodePaths_;
        bool enableCallAnalysis_;
    };

    SimpleFrontendActionFactory factory(dbManager_, userCodePaths_, enableCallAnalysis_);
    
    if (SingleFileTool.run(&factory) != 0) {
        llvm::errs() << "Error running analysis on file: " << file << "\n";
        return false;
    }

    return true;
}

int FileHandler::runAnalysis(unsigned threadCount) {
    std::vector<std::string> sourcePaths = optionsParser.getSourcePathList();
    if (sourcePaths.empty()) {
        llvm::errs() << "No source files specified.\n";
        return 1;
    }

    std::vector<std::string> filesToAnalyze = getSourceFiles(sourcePaths);
    if (filesToAnalyze.empty()) {
        llvm::errs() << "No processable source files found in the specified paths.\n";
        return 1;
    }

    llvm::outs() << "Starting single-pass analysis of " << filesToAnalyze.size() << " file(s)...\n";

    std::atomic<int> successCount(0);
    std::atomic<int> failureCount(0);
    std::atomic<int> processedCount(0);
    int totalFiles = filesToAnalyze.size();

    // 确定线程数
    unsigned int numCores = std::thread::hardware_concurrency();
    unsigned int maxConcurrentTasks;
    
    if (threadCount == 0) {
        maxConcurrentTasks = numCores > 0 ? std::min(numCores, 8u) : 2;
    } else {
        maxConcurrentTasks = threadCount;
    }
    
    if (maxConcurrentTasks == 0) maxConcurrentTasks = 1;

    // 开始事务
    if (!dbManager_.beginTransaction()) {
        llvm::errs() << "Failed to begin transaction\n";
        return 1;
    }

    if (singleThreadMode_) {
        llvm::outs() << "Running in single-threaded mode.\n";
        
        for (int i = 0; i < totalFiles; ++i) {
            const std::string& file = filesToAnalyze[i];
            
            std::string progressMessage = "[" + std::to_string(i + 1) + "/" + 
                                        std::to_string(totalFiles) + "] Analyzing: " + file;
            std::cout << "\r" << progressMessage << std::flush;
            
            if (analyzeFile(file)) {
                successCount++;
            } else {
                failureCount++;
            }
        }
        
        llvm::outs() << "\n";
    } else {
        llvm::outs() << "Using " << maxConcurrentTasks << " concurrent tasks.\n";

        std::vector<std::future<bool>> futures;
        futures.reserve(maxConcurrentTasks);
        std::mutex coutMutex;

        for (int i = 0; i < totalFiles; ++i) {
            if (futures.size() >= maxConcurrentTasks) {
                bool taskCompleted = false;
                while (!taskCompleted) {
                    for (auto it = futures.begin(); it != futures.end(); ) {
                        if (it->wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                            try {
                                if (it->get()) successCount++; else failureCount++;
                            } catch (...) {
                                failureCount++;
                            }
                            it = futures.erase(it);
                            taskCompleted = true;
                            break;
                        } else {
                            ++it;
                        }
                    }
                    if (!taskCompleted) {
                        std::this_thread::sleep_for(std::chrono::milliseconds(100));
                    }
                }
            }

            const std::string& file = filesToAnalyze[i];
            futures.emplace_back(std::async(std::launch::async, [this, file, &processedCount, totalFiles, &coutMutex]() {
                bool result = analyzeFile(file);
                
                int current = processedCount.fetch_add(1) + 1;
                {
                    std::lock_guard<std::mutex> lock(coutMutex);
                    std::cout << "\r[" << current << "/" << totalFiles << "] " << file << std::flush;
                }
                return result;
            }));
        }

        // 等待所有任务完成
        while (!futures.empty()) {
            for (auto it = futures.begin(); it != futures.end(); ) {
                if (it->wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                    try {
                        if (it->get()) successCount++; else failureCount++;
                    } catch (...) {
                        failureCount++;
                    }
                    it = futures.erase(it);
                } else {
                    ++it;
                }
            }
            if (!futures.empty()) {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
        }
        
        llvm::outs() << "\n";
    }
    
    // 刷新并提交
    if (dbManager_.isBatchMode()) {
        dbManager_.flushBatch();
    }
    dbManager_.commitTransaction();
    
    llvm::outs() << "\n=== Analysis finished ===\n";
    llvm::outs() << "Successfully analyzed: " << successCount.load() << " file(s).\n";
    llvm::outs() << "Failed to analyze: " << failureCount.load() << " file(s).\n";

    return failureCount.load() > 0 ? 1 : 0;
}