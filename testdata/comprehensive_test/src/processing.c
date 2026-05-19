#include "processing.h"
#include "common.h"
#include <stdio.h>

// 测试点5: 函数指针全局变量定义
processor_func_t current_processor = NULL;
callback_func_t result_callback = NULL;

// 静态函数指针
static processor_func_t backup_processor = algorithm_b;

// 测试点2: 函数定义 - 算法A
int algorithm_a(uint32_t *data, int count) {
    if (!data || count <= 0) {
        return -1;
    }
    
    int sum = 0;
    // 测试点3: 数据访问 - 通过参数访问全局数据
    for (int i = 0; i < count; i++) {
        sum += data[i]; // 读访问
        global_counter++; // 写访问全局变量
    }
    
    printf("Algorithm A processed %d items, sum: %d\n", count, sum);
    return sum;
}

// 测试点2: 函数定义 - 算法B  
int algorithm_b(uint32_t *data, int count) {
    if (!data || count <= 0) {
        return -1;
    }
    
    uint32_t max = 0;
    // 测试点3: 全局变量访问
    for (int i = 0; i < count; i++) {
        if (data[i] > max) {
            max = data[i]; // 读访问
        }
        shared_buffer[i] = data[i] + 100; // 写访问全局数组
    }
    
    printf("Algorithm B processed %d items, max: %u\n", count, max);
    return (int)max;
}

void result_handler_a(int result) {
    // 测试点3: 全局变量读写访问
    printf("Handler A: result = %d, global_counter = %d\n", result, global_counter);
    
    if (result > 0) {
        global_counter += result; // 写访问
    }
}

void result_handler_b(int result) {
    // 测试点3: 全局变量访问
    printf("Handler B: result = %d\n", result);
    
    if (result < 0) {
        system_enabled = false; // 写访问全局变量
    }
}

// 测试点5: 函数指针操作函数
void set_processor(processor_func_t proc) {
    if (proc) {
        current_processor = proc; // 测试点5: 函数指针赋值
        printf("Processor set successfully\n");
    } else {
        // 测试点5: 使用静态函数指针作为备份
        current_processor = backup_processor;
        printf("Using backup processor\n");
    }
}

void set_callback(callback_func_t cb) {
    result_callback = cb; // 测试点5: 函数指针赋值
    
    // 测试点3: 全局变量访问
    if (cb && system_enabled) {
        printf("Callback set successfully\n");
    }
}
