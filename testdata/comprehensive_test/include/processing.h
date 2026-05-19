#ifndef PROCESSING_H
#define PROCESSING_H

#include "common.h"

// 处理模块的函数声明
typedef int (*processor_func_t)(uint32_t *, int);
typedef void (*callback_func_t)(int result);

// 全局函数指针 - 测试点5: 函数指针关系
extern processor_func_t current_processor;
extern callback_func_t result_callback;

// 函数声明
int algorithm_a(uint32_t *data, int count);
int algorithm_b(uint32_t *data, int count);
void result_handler_a(int result);
void result_handler_b(int result);
void set_processor(processor_func_t proc);
void set_callback(callback_func_t cb);

#endif // PROCESSING_H
