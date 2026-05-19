#ifndef UTILS_H
#define UTILS_H

// 日志函数类型定义
typedef void (*logger_func_t)(const char *);

// 日志函数声明
void default_logger(const char *message);
void console_logger(const char *message);
void set_logger(logger_func_t logger);
void log_message(const char *format, ...);

// 工具模块管理
void init_utils(void);
void cleanup_utils(void);
void print_log_stats(void);

#endif // UTILS_H
