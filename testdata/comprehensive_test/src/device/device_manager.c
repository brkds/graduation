#include "common.h"
#include "processing.h"
#include <stdio.h>

// 测试点1: 设备管理模块的全局变量
static device_t devices[10];
static int device_count = 0;
static device_t *current_device = NULL;

// 测试点4: 复杂指针关系
static device_t **device_registry = NULL;
static void (*device_handlers[10])(int) = {NULL};

// 设备初始化函数
void init_device_manager(void) {
    // 测试点3: 静态变量写访问
    device_count = 0;
    current_device = NULL;
    
    // 初始化设备数组
    for (int i = 0; i < 10; i++) {
        devices[i].id = -1; // 写访问数组元素
        devices[i].handler = NULL; // 测试点5: 函数指针初始化
        device_handlers[i] = NULL; // 测试点5: 函数指针数组初始化
    }
    
    printf("Device manager initialized\n");
}

// 注册设备
int register_device(int id, const char *name, void (*handler)(int)) {
    // 测试点3: 静态变量读访问
    if (device_count >= 10) {
        return -1;
    }
    
    // 测试点3: 数组写访问
    devices[device_count].id = id;
    snprintf(devices[device_count].name, 32, "%s", name);
    devices[device_count].handler = handler; // 测试点5: 函数指针赋值
    
    // 测试点4: 指针操作
    current_device = &devices[device_count]; // 指向当前设备
    
    // 测试点5: 函数指针数组操作
    device_handlers[device_count] = handler;
    
    device_count++; // 写访问
    
    printf("Device %d (%s) registered\n", id, name);
    return device_count - 1;
}

// 调用设备处理函数
void trigger_device(int index, int value) {
    // 测试点3: 边界检查读访问
    if (index < 0 || index >= device_count) {
        return;
    }
    
    // 测试点5: 通过数组的函数指针调用
    if (device_handlers[index]) {
        device_handlers[index](value);
        
        // 测试点3: 全局变量访问
        global_counter += value;
    }
    
    // 测试点5: 通过结构体的函数指针调用
    if (devices[index].handler) {
        devices[index].handler(value + 10);
    }
}

// 获取当前设备信息
void print_current_device(void) {
    // 测试点4: 指针读访问
    if (current_device) {
        printf("Current device: ID=%d, Name=%s\n", 
               current_device->id, current_device->name);
        
        // 测试点3: 全局变量读访问
        printf("Global counter: %d\n", global_counter);
    } else {
        printf("No current device\n");
    }
}
