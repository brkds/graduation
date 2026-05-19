#include "common.h"
#include "processing.h"
#include "memory.h"
#include "device_manager.h"
#include <stdio.h>
#include <string.h>

// 测试点1: 工具模块的全局变量
static char log_buffer[2048];
static int log_count = 0;
static bool logging_enabled = true;

// 测试点4: 复杂指针链
static char **message_queue = NULL;
static int *queue_indices = NULL;
static char ***nested_ptr = &message_queue;

// 测试点5: 工具函数指针
typedef void (*logger_func_t)(const char *);
static logger_func_t current_logger = NULL;

// 默认日志函数
void default_logger(const char *message) {
    // 测试点3: 静态变量访问
    if (!logging_enabled || !message) {
        return;
    }
    
    // 测试点3: 全局缓冲区写访问
    int len = strlen(message);
    if (log_count + len < 2048) {
        strcat(log_buffer, message); // 写访问
        strcat(log_buffer, "\n");
        log_count += len + 1; // 写访问计数器
    }
    
    printf("[LOG] %s\n", message);
}

// 控制台日志函数
void console_logger(const char *message) {
    // 测试点3: 全局变量读访问
    printf("[CONSOLE] Global counter: %d, Message: %s\n", global_counter, message);
}

// 设置日志器
void set_logger(logger_func_t logger) {
    // 测试点5: 函数指针赋值
    current_logger = logger ? logger : default_logger;
    
    // 测试日志
    if (current_logger) {
        current_logger("Logger changed");
    }
}

// 日志函数
void log_message(const char *format, ...) {
    if (!current_logger) {
        current_logger = default_logger; // 测试点5: 默认函数指针赋值
    }
    
    // 简化版本，直接传递格式化字符串
    current_logger(format); // 测试点5: 函数指针调用
}

// 初始化工具模块
void init_utils(void) {
    // 测试点3: 静态变量初始化
    memset(log_buffer, 0, sizeof(log_buffer));
    log_count = 0;
    logging_enabled = true;
    
    // 测试点5: 设置默认日志器
    set_logger(default_logger);
    
    // 测试点4: 动态内存分配用于指针链
    message_queue = custom_malloc(10 * sizeof(char*));
    queue_indices = custom_malloc(10 * sizeof(int));
    
    if (message_queue && queue_indices) {
        for (int i = 0; i < 10; i++) {
            message_queue[i] = NULL; // 测试点4: 指针数组初始化
            queue_indices[i] = -1;   // 写访问
        }
        
        // 测试点4: 三级指针操作
        *nested_ptr = message_queue;
    }
    
    log_message("Utils module initialized");
}

// 清理工具模块
void cleanup_utils(void) {
    // 测试点3: 日志状态访问
    if (logging_enabled) {
        log_message("Cleaning up utils module");
    }
    
    // 测试点4: 清理动态分配的指针
    if (message_queue) {
        for (int i = 0; i < 10; i++) {
            if (message_queue[i]) {
                custom_free(message_queue[i]);
                message_queue[i] = NULL; // 测试点4: 指针置空
            }
        }
        custom_free(message_queue);
        message_queue = NULL;
    }
    
    if (queue_indices) {
        custom_free(queue_indices);
        queue_indices = NULL; // 测试点4: 指针重置
    }
    
    // 测试点4: 三级指针重置
    *nested_ptr = NULL;
    
    logging_enabled = false; // 测试点3: 状态变量写访问
}

// 获取日志统计
void print_log_stats(void) {
    // 测试点3: 多个静态变量读访问
    printf("Log Statistics:\n");
    printf("  Buffer size: %d bytes used\n", log_count);
    printf("  Logging enabled: %s\n", logging_enabled ? "Yes" : "No");
    printf("  Current logger: %p\n", (void*)current_logger);
    
    // 测试点4: 指针状态检查
    printf("  Message queue: %p\n", (void*)message_queue);
    printf("  Queue indices: %p\n", (void*)queue_indices);
    printf("  Nested pointer: %p\n", (void*)nested_ptr);
}
