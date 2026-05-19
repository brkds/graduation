/*
 * 模块A - 数据处理模块
 * 循环调用链: process_data() -> send_to_network()
 */

#include <stdio.h>
#include <string.h>
#include "module_a.h"
#include "module_b.h"  // 会调用模块B的函数

/**
 * 主要的数据处理函数
 * 这是循环调用链的起点: process_data -> send_to_network -> cache_data -> process_data
 */
int process_data(const char* data) {
    static int call_count = 0;
    call_count++;
    
    printf("[ModuleA] process_data() 被调用，第 %d 次\n", call_count);
    printf("[ModuleA] 处理数据: %s\n", data);
    
    // 防止无限递归
    if (call_count > 3) {
        printf("[ModuleA] 检测到递归调用超过限制，停止处理\n");
        call_count = 0;
        return -1;
    }
    
    // 数据验证
    if (!data || strlen(data) == 0) {
        printf("[ModuleA] 数据验证失败\n");
        call_count = 0;
        return -1;
    }
    
    // 数据转换
    printf("[ModuleA] 正在转换数据...\n");
    
    // 调用网络模块发送数据 - 这会触发循环调用链！
    printf("[ModuleA] 准备发送数据到网络模块\n");
    int result = send_to_network(data);
    
    printf("[ModuleA] 网络模块返回结果: %d\n", result);
    
    call_count--;
    return result;
}

/**
 * 数据验证函数
 */
int validate_data(const char* data) {
    printf("[ModuleA] validate_data() 验证数据\n");
    
    if (!data) {
        printf("[ModuleA] 数据指针为空\n");
        return 0;
    }
    
    if (strlen(data) < 3) {
        printf("[ModuleA] 数据长度太短\n");
        return 0;
    }
    
    printf("[ModuleA] 数据验证通过\n");
    return 1;
}

/**
 * 数据格式化函数
 */
void format_data(char* data) {
    printf("[ModuleA] format_data() 格式化数据\n");
    
    if (!data) return;
    
    // 简单的大写转换
    for (int i = 0; data[i]; i++) {
        if (data[i] >= 'a' && data[i] <= 'z') {
            data[i] = data[i] - 'a' + 'A';
        }
    }
    
    printf("[ModuleA] 数据格式化完成\n");
}

/**
 * 获取模块状态
 */
const char* get_module_a_status(void) {
    return "ModuleA: 正常运行";
}
