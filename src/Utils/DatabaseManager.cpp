#include "Utils/DatabaseManager.h"
#include <iostream>
#include <iomanip>

DatabaseManager::DatabaseManager(const std::string& dbPath) : dbPath_(dbPath), db_(nullptr), 
                                 batchMode_(false), batchCount_(0), inTransaction_(false),
                                 totalInserts_(0), totalQueries_(0), 
                                 cacheHits_(0), cacheMisses_(0) {
}

DatabaseManager::~DatabaseManager() {
    close();
}

bool DatabaseManager::open() {
    if (db_) {
        return true;
    }

    int rc = sqlite3_open(dbPath_.c_str(), &db_);
    if (rc != SQLITE_OK) {
        std::cerr << "Cannot open database: " << sqlite3_errmsg(db_) << std::endl;
        db_ = nullptr;
        return false;
    }

    rc = sqlite3_busy_timeout(db_, 5000);
    if (rc != SQLITE_OK) {
        std::cerr << "Failed to set busy timeout: " << sqlite3_errmsg(db_) << std::endl;
    }

    if (!executeSQL("PRAGMA journal_mode=WAL;")) {
        std::cerr << "Failed to set WAL journal mode." << std::endl;
        if (!executeSQL("PRAGMA journal_mode=DELETE;")) {
            std::cerr << "Failed to set any journal mode." << std::endl;
        }
    }

    if (!executeSQL("PRAGMA synchronous=NORMAL;")) {
        std::cerr << "Failed to set synchronous mode." << std::endl;
    }

    if (!executeSQL("PRAGMA cache_size=-65536;")) {
        std::cerr << "Failed to set cache size." << std::endl;
    }

    if (!executeSQL("PRAGMA page_size=4096;")) {
        std::cerr << "Failed to set page size." << std::endl;
    }

    if (!executeSQL("PRAGMA temp_store=MEMORY;")) {
        std::cerr << "Failed to set temp store to memory." << std::endl;
    }
    
    if (!executeSQL("PRAGMA foreign_keys = ON;")) {
        std::cerr << "Failed to enable foreign key support." << std::endl;
    }
    
    return true;
}

void DatabaseManager::close() {
    if (db_) {
        std::lock_guard<std::mutex> lock(dbMutex_);
        
        for (auto& pair : preparedStmts_) {
            if (pair.second) {
                sqlite3_finalize(pair.second);
            }
        }
        preparedStmts_.clear();
        
        int autocommit = sqlite3_get_autocommit(db_);
        
        if (!autocommit) {
            char* errMsg = nullptr;
            int rc = sqlite3_exec(db_, "COMMIT;", nullptr, nullptr, &errMsg);
            if (rc != SQLITE_OK) {
                sqlite3_free(errMsg);
            }
            inTransaction_ = false;
        }
        
        char* errMsg = nullptr;
        int rc = sqlite3_exec(db_, "PRAGMA synchronous = FULL;", nullptr, nullptr, &errMsg);
        if (rc != SQLITE_OK) {
            sqlite3_free(errMsg);
        }
        
        rc = sqlite3_exec(db_, "PRAGMA wal_checkpoint(FULL);", nullptr, nullptr, &errMsg);
        if (rc != SQLITE_OK) {
            sqlite3_free(errMsg);
        }
        
        sqlite3_close(db_);
        db_ = nullptr;
    }
}

bool DatabaseManager::isOpen() const {
    return db_ != nullptr;
}

bool DatabaseManager::executeSQL(const std::string& sql) {
    std::lock_guard<std::mutex> lock(dbMutex_);
    return executeSQLInternal(sql);
}

bool DatabaseManager::executeSQLInternal(const std::string& sql) {
    char* errMsg = nullptr;
    int rc = sqlite3_exec(db_, sql.c_str(), nullptr, nullptr, &errMsg);
    if (rc != SQLITE_OK) {
        std::cerr << "SQL error: " << errMsg << " for SQL: " << sql << std::endl;
        sqlite3_free(errMsg);
        return false;
    }
    return true;
}

bool DatabaseManager::tableExists(const std::string& tableName) {
    std::lock_guard<std::mutex> lock(dbMutex_);
    sqlite3_stmt* stmt;
    std::string sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;";
    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
    if (rc != SQLITE_OK) {
        std::cerr << "Failed to prepare statement: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }
    sqlite3_bind_text(stmt, 1, tableName.c_str(), -1, SQLITE_STATIC);
    bool exists = (sqlite3_step(stmt) == SQLITE_ROW);
    sqlite3_finalize(stmt);
    return exists;
}

bool DatabaseManager::createTables() {
    if (!db_) return false;

    // 1. 全局变量表（联合主键：name + file_path）
    std::string createGlobalVarsTableSQL = R"SQL(
        CREATE TABLE IF NOT EXISTS GlobalVariables (
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            type TEXT,
            line_number INTEGER NOT NULL,
            is_static INTEGER NOT NULL DEFAULT 0,
            definition_code TEXT,
            PRIMARY KEY (name, file_path)
        ) WITHOUT ROWID;
    )SQL";

    // 2. 函数表（联合主键：name + file_path）
    std::string createFunctionsTableSQL = R"SQL(
        CREATE TABLE IF NOT EXISTS Functions (
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            return_type TEXT,
            parameters TEXT,
            start_line INTEGER NOT NULL,
            start_col INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            end_col INTEGER NOT NULL,
            is_static INTEGER NOT NULL DEFAULT 0,
            definition_code TEXT,
            PRIMARY KEY (name, file_path)
        ) WITHOUT ROWID;
    )SQL";

    // 3. 访问关系表（边表，保持不变）
    std::string createAccessRelationsTableSQL = R"SQL(
        CREATE TABLE IF NOT EXISTS AccessRelations (
            var_name TEXT NOT NULL,
            func_name TEXT NOT NULL,
            access_type TEXT NOT NULL CHECK(access_type IN ('read', 'write')),
            access_file_path TEXT NOT NULL,
            access_line_number INTEGER NOT NULL,
            PRIMARY KEY (var_name, func_name, access_type, access_file_path, access_line_number)
        ) WITHOUT ROWID;
    )SQL";

    // 4. 调用关系表（边表，保持不变）
    std::string createCallRelationsTableSQL = R"SQL(
        CREATE TABLE IF NOT EXISTS CallRelations (
            caller_name TEXT NOT NULL,
            callee_name TEXT NOT NULL,
            call_site_file_path TEXT NOT NULL,
            call_site_line_number INTEGER NOT NULL,
            call_site_column_number INTEGER NOT NULL,
            PRIMARY KEY (caller_name, callee_name, call_site_file_path, call_site_line_number, call_site_column_number)
        ) WITHOUT ROWID;
    )SQL";

    // 5. 数据指针表（联合主键：pointer_name + file_path）
    std::string createDataPointersTableSQL = R"SQL(
        CREATE TABLE IF NOT EXISTS DataPointers (
            pointer_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            points_to_var_name TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            PRIMARY KEY (pointer_name, file_path)
        ) WITHOUT ROWID;
    )SQL";

    // 6. 函数指针表（联合主键：pointer_name + file_path）
    std::string createFunctionPointersTableSQL = R"SQL(
        CREATE TABLE IF NOT EXISTS FunctionPointers (
            pointer_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            points_to_func_name TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            PRIMARY KEY (pointer_name, file_path)
        ) WITHOUT ROWID;
    )SQL";

    // 创建索引（保持原有）
    std::string createIndexVarNameSQL = "CREATE INDEX IF NOT EXISTS idx_accessrelations_var_name ON AccessRelations(var_name);";
    std::string createIndexFuncNameSQL = "CREATE INDEX IF NOT EXISTS idx_accessrelations_func_name ON AccessRelations(func_name);";
    std::string createIndexCallerNameSQL = "CREATE INDEX IF NOT EXISTS idx_callrelations_caller_name ON CallRelations(caller_name);";
    std::string createIndexCalleeNameSQL = "CREATE INDEX IF NOT EXISTS idx_callrelations_callee_name ON CallRelations(callee_name);";

    bool success = true;
    
    if (!tableExists("GlobalVariables")) {
        success &= executeSQL(createGlobalVarsTableSQL);
    }
    if (!tableExists("Functions")) {
        success &= executeSQL(createFunctionsTableSQL);
    }
    if (!tableExists("AccessRelations")) {
        success &= executeSQL(createAccessRelationsTableSQL);
        success &= executeSQL(createIndexVarNameSQL);
        success &= executeSQL(createIndexFuncNameSQL);
    }
    if (!tableExists("CallRelations")) {
        success &= executeSQL(createCallRelationsTableSQL);
        success &= executeSQL(createIndexCallerNameSQL);
        success &= executeSQL(createIndexCalleeNameSQL);
    }
    if (!tableExists("DataPointers")) {
        success &= executeSQL(createDataPointersTableSQL);
    }
    if (!tableExists("FunctionPointers")) {
        success &= executeSQL(createFunctionPointersTableSQL);
    }

    return success;
}

bool DatabaseManager::insertGlobalVariable(
    const std::string& name, const std::string& type, 
    const std::string& filePath, int lineNumber, 
    bool isStatic, const std::string& definitionCode) {
    
    std::lock_guard<std::mutex> lock(dbMutex_);
    totalInserts_++;
    
    sqlite3_stmt* stmt;
    std::string sql = "INSERT OR REPLACE INTO GlobalVariables (name, type, file_path, line_number, is_static, definition_code) VALUES (?, ?, ?, ?, ?, ?);";

    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
    if (rc != SQLITE_OK) {
        std::cerr << "Failed to prepare insertGlobalVariable statement: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }

    sqlite3_bind_text(stmt, 1, name.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, type.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, filePath.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 4, lineNumber);
    sqlite3_bind_int(stmt, 5, isStatic ? 1 : 0);
    sqlite3_bind_text(stmt, 6, definitionCode.c_str(), -1, SQLITE_TRANSIENT);

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    if (rc != SQLITE_DONE) {
        std::cerr << "Failed to insert global variable: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }
    
    if (batchMode_) {
        batchCount_++;
        if (batchCount_ >= BATCH_SIZE) {
            if (!flushBatchInternal()) {
                std::cerr << "Failed to flush batch in insertGlobalVariable" << std::endl;
            }
        }
    }
    
    return true;
}

bool DatabaseManager::insertFunction(
    const std::string& name, const std::string& returnType, 
    const std::string& params, const std::string& filePath, 
    int startLine, int startCol, int endLine, int endCol, 
    bool isStatic) {

    std::lock_guard<std::mutex> lock(dbMutex_);
    totalInserts_++;
    
    sqlite3_stmt* stmt;
    std::string sql = "INSERT OR REPLACE INTO Functions (name, return_type, parameters, file_path, start_line, start_col, end_line, end_col, is_static, definition_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);";

    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
    if (rc != SQLITE_OK) {
        std::cerr << "Failed to prepare insertFunction statement: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }

    sqlite3_bind_text(stmt, 1, name.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, returnType.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, params.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 4, filePath.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 5, startLine);
    sqlite3_bind_int(stmt, 6, startCol);
    sqlite3_bind_int(stmt, 7, endLine);
    sqlite3_bind_int(stmt, 8, endCol);
    sqlite3_bind_int(stmt, 9, isStatic ? 1 : 0);
    sqlite3_bind_null(stmt, 10);  // definition_code

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    if (rc != SQLITE_DONE) {
        std::cerr << "Failed to insert function: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }
    
    if (batchMode_) {
        batchCount_++;
        if (batchCount_ >= BATCH_SIZE) {
            if (!flushBatchInternal()) {
                std::cerr << "Failed to flush batch in insertFunction" << std::endl;
            }
        }
    }
    
    return true;
}

bool DatabaseManager::insertAccessRelation(
    const std::string& varName, const std::string& funcName, 
    const std::string& accessType, 
    const std::string& accessFilePath, int accessLineNumber) {

    std::lock_guard<std::mutex> lock(dbMutex_);
    totalInserts_++;
    
    sqlite3_stmt* stmt;
    std::string sql = "INSERT INTO AccessRelations (var_name, func_name, access_type, access_file_path, access_line_number) VALUES (?, ?, ?, ?, ?);";

    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
    if (rc != SQLITE_OK) {
        std::cerr << "Failed to prepare insertAccessRelation statement: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }

    sqlite3_bind_text(stmt, 1, varName.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, funcName.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, accessType.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 4, accessFilePath.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 5, accessLineNumber);

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    if (rc != SQLITE_DONE) {
        int extended_rc = sqlite3_extended_errcode(db_);
        if (extended_rc == SQLITE_CONSTRAINT_UNIQUE || extended_rc == SQLITE_CONSTRAINT_PRIMARYKEY) {
            return true;
        }
        std::cerr << "Failed to insert access relation: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }
    
    if (batchMode_) {
        batchCount_++;
        if (batchCount_ >= BATCH_SIZE) {
            if (!flushBatchInternal()) {
                std::cerr << "Failed to flush batch in insertAccessRelation" << std::endl;
            }
        }
    }
    
    return true;
}

bool DatabaseManager::insertCallRelation(
    const std::string& callerName, const std::string& calleeName, 
    const std::string& callSiteFilePath, int callSiteLine, int callSiteCol) {
    
    std::lock_guard<std::mutex> lock(dbMutex_);
    totalInserts_++;
    
    sqlite3_stmt* stmt;
    std::string sql = "INSERT INTO CallRelations (caller_name, callee_name, call_site_file_path, call_site_line_number, call_site_column_number) VALUES (?, ?, ?, ?, ?);";

    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
    if (rc != SQLITE_OK) {
        std::cerr << "Failed to prepare insertCallRelation statement: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }

    sqlite3_bind_text(stmt, 1, callerName.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, calleeName.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, callSiteFilePath.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 4, callSiteLine);
    sqlite3_bind_int(stmt, 5, callSiteCol);

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    if (rc != SQLITE_DONE) {
        int extended_rc = sqlite3_extended_errcode(db_);
        if (extended_rc == SQLITE_CONSTRAINT_UNIQUE || extended_rc == SQLITE_CONSTRAINT_PRIMARYKEY) {
            return true;
        }
        std::cerr << "Failed to insert call relation: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }
    
    if (batchMode_) {
        batchCount_++;
        if (batchCount_ >= BATCH_SIZE) {
            if (!flushBatchInternal()) {
                std::cerr << "Failed to flush batch in insertCallRelation" << std::endl;
            }
        }
    }
    
    return true;
}

bool DatabaseManager::insertDataPointer(
    const std::string& pointerName, const std::string& pointsToVarName,
    const std::string& filePath, int lineNumber) {
    
    std::lock_guard<std::mutex> lock(dbMutex_);
    totalInserts_++;
    
    sqlite3_stmt* stmt;
    std::string sql = "INSERT OR REPLACE INTO DataPointers (pointer_name, points_to_var_name, file_path, line_number) VALUES (?, ?, ?, ?);";

    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
    if (rc != SQLITE_OK) {
        std::cerr << "Failed to prepare insertDataPointer statement: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }

    sqlite3_bind_text(stmt, 1, pointerName.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, pointsToVarName.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, filePath.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 4, lineNumber);

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    if (rc != SQLITE_DONE) {
        std::cerr << "Failed to insert data pointer: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }
    
    if (batchMode_) {
        batchCount_++;
        if (batchCount_ >= BATCH_SIZE) {
            flushBatchInternal();
        }
    }
    
    return true;
}

bool DatabaseManager::insertFunctionPointer(
    const std::string& pointerName, const std::string& pointsToFuncName,
    const std::string& filePath, int lineNumber) {
    
    std::lock_guard<std::mutex> lock(dbMutex_);
    totalInserts_++;
    
    sqlite3_stmt* stmt;
    std::string sql = "INSERT OR REPLACE INTO FunctionPointers (pointer_name, points_to_func_name, file_path, line_number) VALUES (?, ?, ?, ?);";

    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
    if (rc != SQLITE_OK) {
        std::cerr << "Failed to prepare insertFunctionPointer statement: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }

    sqlite3_bind_text(stmt, 1, pointerName.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, pointsToFuncName.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, filePath.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 4, lineNumber);

    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    if (rc != SQLITE_DONE) {
        std::cerr << "Failed to insert function pointer: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }
    
    if (batchMode_) {
        batchCount_++;
        if (batchCount_ >= BATCH_SIZE) {
            flushBatchInternal();
        }
    }
    
    return true;
}

bool DatabaseManager::beginTransaction() {
    std::lock_guard<std::mutex> lock(dbMutex_);
    return beginTransactionInternal();
}

bool DatabaseManager::beginTransactionInternal() {
    if (inTransaction_) {
        return true;
    }
    
    bool success = executeSQLInternal("BEGIN TRANSACTION;");
    if (success) {
        inTransaction_ = true;
    }
    return success;
}

bool DatabaseManager::commitTransaction() {
    std::lock_guard<std::mutex> lock(dbMutex_);
    return commitTransactionInternal();
}

bool DatabaseManager::commitTransactionInternal() {
    if (!inTransaction_) {
        return true;
    }
    
    bool success = executeSQLInternal("COMMIT;");
    if (success) {
        inTransaction_ = false;
    }
    return success;
}

bool DatabaseManager::rollbackTransaction() {
    std::lock_guard<std::mutex> lock(dbMutex_);
    if (!inTransaction_) {
        return true;
    }
    
    bool success = executeSQLInternal("ROLLBACK;");
    if (success) {
        inTransaction_ = false;
    }
    return success;
}

int DatabaseManager::getTableRowCount(const std::string& tableName) {
    std::lock_guard<std::mutex> lock(dbMutex_);
    sqlite3_stmt* stmt;
    std::string sql = "SELECT COUNT(*) FROM " + tableName + ";";
    
    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
    if (rc != SQLITE_OK) {
        std::cerr << "Failed to prepare count query for table " << tableName << ": " << sqlite3_errmsg(db_) << std::endl;
        return -1;
    }
    
    int count = -1;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        count = sqlite3_column_int(stmt, 0);
    }
    
    sqlite3_finalize(stmt);
    return count;
}

sqlite3_stmt* DatabaseManager::getPreparedStatement(const std::string& sql) const {
    auto it = preparedStmts_.find(sql);
    if (it != preparedStmts_.end()) {
        sqlite3_reset(it->second);
        sqlite3_clear_bindings(it->second);
        return it->second;
    }
    
    sqlite3_stmt* stmt = nullptr;
    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
    if (rc != SQLITE_OK) {
        std::cerr << "Failed to prepare statement: " << sqlite3_errmsg(db_) << std::endl;
        return nullptr;
    }
    
    preparedStmts_[sql] = stmt;
    return stmt;
}

bool DatabaseManager::enableBatchMode() {
    std::lock_guard<std::mutex> lock(dbMutex_);
    if (!db_) return false;
    
    batchMode_ = true;
    batchCount_ = 0;
    return beginTransactionInternal();
}

bool DatabaseManager::flushBatch() {
    std::lock_guard<std::mutex> lock(dbMutex_);
    if (!db_ || !batchMode_) return false;
    
    bool success = commitTransactionInternal();
    batchCount_ = 0;
    
    if (success) {
        success = beginTransactionInternal();
    }
    
    return success;
}

bool DatabaseManager::flushBatchInternal() {
    if (!db_ || !batchMode_) return false;
    
    bool success = commitTransactionInternal();
    batchCount_ = 0;
    
    if (success) {
        success = beginTransactionInternal();
    }
    
    return success;
}

void DatabaseManager::resetPerformanceCounters() {
    totalInserts_.store(0);
    totalQueries_.store(0);
    cacheHits_.store(0);
    cacheMisses_.store(0);
}

void DatabaseManager::printPerformanceStats() const {
    std::cout << "\n=== Database Performance Statistics ===" << std::endl;
    std::cout << "Total Inserts: " << totalInserts_.load() << std::endl;
    std::cout << "Total Queries: " << totalQueries_.load() << std::endl;
    std::cout << "Cache Hits: " << cacheHits_.load() << std::endl;
    std::cout << "Cache Misses: " << cacheMisses_.load() << std::endl;
    
    long long totalCacheRequests = cacheHits_.load() + cacheMisses_.load();
    if (totalCacheRequests > 0) {
        double hitRate = (double)cacheHits_.load() / totalCacheRequests * 100.0;
        std::cout << "Cache Hit Rate: " << std::fixed << std::setprecision(2) << hitRate << "%" << std::endl;
    }
    std::cout << "=======================================" << std::endl;
}