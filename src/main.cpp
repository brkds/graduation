#include "Utils/FileHandler.h"
#include "Utils/DatabaseManager.h"
#include <clang/Tooling/CommonOptionsParser.h>
#include <llvm/Support/CommandLine.h>
#include <iostream>

static llvm::cl::OptionCategory ToolCategory("Kernel Analyzer Options");

static llvm::cl::opt<std::string> DatabasePath(
    "db", 
    llvm::cl::desc("Path to the SQLite database file"), 
    llvm::cl::value_desc("filepath"), 
    llvm::cl::init("kernel_analysis.db"), 
    llvm::cl::cat(ToolCategory));

static llvm::cl::opt<bool> SingleThreadMode(
    "single-thread", 
    llvm::cl::desc("Force single-threaded analysis for consistent results"), 
    llvm::cl::init(false), 
    llvm::cl::cat(ToolCategory));

static llvm::cl::opt<unsigned> ThreadCount(
    "j", 
    llvm::cl::desc("Number of threads to use (0 for auto)"), 
    llvm::cl::value_desc("number"), 
    llvm::cl::init(0), 
    llvm::cl::cat(ToolCategory));

static llvm::cl::opt<bool> EnableCallAnalysis(
    "enable-calls", 
    llvm::cl::desc("Enable function call relationship analysis"), 
    llvm::cl::init(false), 
    llvm::cl::cat(ToolCategory));

int main(int argc, const char **argv) {
    auto ExpectedParser = clang::tooling::CommonOptionsParser::create(argc, argv, ToolCategory);
    if (!ExpectedParser) {
        llvm::errs() << ExpectedParser.takeError();
        return 1;
    }
    clang::tooling::CommonOptionsParser &optionsParser = ExpectedParser.get();

    // Initialize DatabaseManager
    DatabaseManager dbManager(DatabasePath.getValue());
    if (!dbManager.open()) {
        llvm::errs() << "Error: Could not open database at " << DatabasePath.getValue() << "\n";
        return 1;
    }
    if (!dbManager.createTables()) {
        llvm::errs() << "Error: Could not create database tables in " << DatabasePath.getValue() << "\n";
        dbManager.close();
        return 1;
    }

    // Enable batch mode for better performance
    if (!dbManager.enableBatchMode()) {
        llvm::errs() << "Warning: Could not enable batch mode\n";
    }
    
    // Reset performance counters
    dbManager.resetPerformanceCounters();

    // 单遍遍历，不再需要 AnalysisConfig
    bool enableCallAnalysis = EnableCallAnalysis.getValue();
    bool singleThreadMode = SingleThreadMode.getValue();
    
    FileHandler fileHandler(dbManager, optionsParser, enableCallAnalysis, singleThreadMode);
    
    // 直接运行单遍分析
    int result = fileHandler.runAnalysis(ThreadCount.getValue());

    // Flush any remaining batch operations
    if (dbManager.isBatchMode()) {
        llvm::outs() << "Flushing remaining batch operations...\n";
        dbManager.flushBatch();
        dbManager.commitTransaction();
    }

    // Print performance statistics
    dbManager.printPerformanceStats();

    // Force database synchronization before closing
    if (dbManager.isOpen()) {
        dbManager.executeSQL("PRAGMA synchronous = FULL;");
        dbManager.executeSQL("PRAGMA wal_checkpoint(FULL);");
    }

    dbManager.close();
    return result;
}