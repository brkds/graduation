#ifndef DATABASE_MANAGER_H
#define DATABASE_MANAGER_H

#include <sqlite3.h>
#include <string>
#include <vector>
#include <mutex>
#include <atomic>
#include <unordered_map>

class DatabaseManager {
public:
    DatabaseManager(const std::string& dbPath);
    ~DatabaseManager();

    bool open();
    void close();
    bool isOpen() const;

    bool createTables();

    // 插入方法：全部返回 bool，参数全部用名字（无 ID）
    bool insertGlobalVariable(const std::string& name, const std::string& type, 
                              const std::string& filePath, int lineNumber, 
                              bool isStatic, const std::string& definitionCode = "");

    bool insertFunction(const std::string& name, const std::string& returnType, 
                        const std::string& params, const std::string& filePath, 
                        int startLine, int startCol, int endLine, int endCol, 
                        bool isStatic);
    
    bool insertAccessRelation(const std::string& varName, const std::string& funcName, 
                              const std::string& accessType,
                              const std::string& accessFilePath, int accessLineNumber);

    bool insertCallRelation(const std::string& callerName, const std::string& calleeName, 
                            const std::string& callSiteFilePath, int callSiteLine, int callSiteCol);

    bool insertDataPointer(const std::string& pointerName, const std::string& pointsToVarName,
                           const std::string& filePath, int lineNumber);

    bool insertFunctionPointer(const std::string& pointerName, const std::string& pointsToFuncName,
                               const std::string& filePath, int lineNumber);

    // Transaction management
    bool beginTransaction();
    bool commitTransaction();
    bool rollbackTransaction();
    bool inTransaction() const { return inTransaction_; }

    // Batch operations for performance
    bool enableBatchMode();
    bool flushBatch();
    bool isBatchMode() const { return batchMode_; }

    // Performance counters
    void resetPerformanceCounters();
    void printPerformanceStats() const;

    // Public SQL execution for debugging/maintenance
    bool executeSQL(const std::string& sql);
    
    // Query methods for debugging
    int getTableRowCount(const std::string& tableName);

private:
    std::string dbPath_;
    sqlite3* db_;
    std::mutex dbMutex_;
    
    bool tableExists(const std::string& tableName);
    bool executeSQLInternal(const std::string& sql);
    bool beginTransactionInternal();
    bool commitTransactionInternal();
    
    bool batchMode_;
    int batchCount_;
    bool inTransaction_;
    static const int BATCH_SIZE = 1000;
    
    mutable std::atomic<long long> totalInserts_;
    mutable std::atomic<long long> totalQueries_;
    mutable std::atomic<long long> cacheHits_;
    mutable std::atomic<long long> cacheMisses_;
    
    mutable std::unordered_map<std::string, sqlite3_stmt*> preparedStmts_;
    sqlite3_stmt* getPreparedStatement(const std::string& sql) const;
    
    bool flushBatchInternal();
};

#endif // DATABASE_MANAGER_H