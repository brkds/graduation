#include "common.h"
#include "processing.h"
#include "memory.h"
#include "device_manager.h"
#include "utils.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 测试点1: 全局变量定义
int global_counter = 0;
uint32_t shared_buffer[1024] = {0};
bool system_enabled = false;

// 测试点4: 数据指针定义
int *global_ptr = &global_counter;
uint32_t *buffer_ptr = shared_buffer;
device_t *main_device = NULL;

// 静态全局变量测试
static int internal_state = 100;
static int *internal_ptr = NULL;

// Linux内核特性：使用宏复用生成函数
DECLARE_COUNTER_FUNC(main)
DECLARE_COUNTER_FUNC(test)

// 测试点2: 函数定义
void init_system(void) {
    // 测试点3: 数据访问关系 - 写访问
    system_enabled = true;
    global_counter = 0;
    
    // 内存分配
    main_device = custom_malloc(sizeof(device_t));
    if (main_device) {
        main_device->id = 1;
        strcpy(main_device->name, "MainDevice");
        main_device->handler = result_handler_a; // 测试点5: 函数指针赋值
    }
    
    // 测试点3: 数据访问关系 - 读写访问
    internal_state++;
    internal_ptr = &internal_state;
    
    // Linux内核特性：条件编译，访问全局变量
#if CONFIG_DEBUG
    printf("System initialized. Counter: %d, internal_state: %d\n", 
           global_counter, internal_state);
#else
    printf("System initialized. Counter: %d\n", global_counter);
#endif

    if(global_counter<100) init_system();
}

void cleanup_system(void) {
    // 测试点3: 数据访问关系 - 读访问
    if (system_enabled) {
        printf("Cleaning up system. Final counter: %d\n", global_counter);
        
        // 测试点3: 写访问
        system_enabled = false;
        global_counter = -1;
        
        if (main_device) {
            custom_free(main_device);
            main_device = NULL; // 测试点4: 指针关系变化
        }
    }
}

int process_data(uint32_t *data, size_t len) {
    if (!data || len == 0 || !system_enabled) {
        return -1;
    }
    
    // 测试点3: 全局数据访问
    for (size_t i = 0; i < len && i < 1024; i++) {
        shared_buffer[i] = data[i] * 2; // 写访问
        global_counter++; // 写访问（自增）
    }
    
    // 测试点5: 函数指针调用
    if (current_processor) {
        int result = current_processor(shared_buffer, (int)len);
        
        // 测试点5: 回调函数调用
        if (result_callback) {
            result_callback(result);
        }
        
        return result;
    }
    
    return 0;
}

bool validate_input(int value) {
    // 测试点3: 全局变量读访问
    if (!system_enabled) {
        return false;
    }
    
    // 测试点3: 静态变量访问
    return value > 0 && value < internal_state;
}

int main(void) {
    printf("Starting comprehensive test program\n");
    
    // 初始化所有模块
    init_utils();
    init_device_manager();
    init_system();
    
    log_message("All modules initialized");
    
    // 注册一些测试设备 - 测试点5: 函数指针注册
    register_device(1, "SensorA", result_handler_a);
    register_device(2, "SensorB", result_handler_b);
    
    // 设置处理器和回调 - 测试点5: 函数指针操作
    set_processor(algorithm_a);
    set_callback(result_handler_b);
    
    // 切换日志器
    set_logger(console_logger);
    log_message("Switched to console logger");
    
    // 测试数据处理
    uint32_t test_data[] = {1, 2, 3, 4, 5};
    int result = process_data(test_data, 5);
    
    printf("Processing result: %d\n", result);
    
    // 测试设备触发 - 测试点5: 函数指针调用链
    trigger_device(0, 10);
    trigger_device(1, 20);
    
    // 显示当前设备信息
    print_current_device();
    
    // 测试输入验证
    bool valid = validate_input(50);
    printf("Input validation: %s\n", valid ? "PASS" : "FAIL");
    
    // Linux内核特性：测试宏复用生成的函数
    increment_main();
    increment_test();
    
    // 打印各种统计信息
    memory_stats();
    print_log_stats();
    
    // 测试设备回调
    if (main_device && main_device->handler) {
        main_device->handler(result); // 测试点5: 通过结构体的函数指针调用
    }
    
    // 切换回默认日志器
    set_logger(default_logger);
    log_message("Switched back to default logger");
    
    // 清理所有模块
    cleanup_system();
    cleanup_utils();
    
    printf("Program completed\n");
    return 0;
}
