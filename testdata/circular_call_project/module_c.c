/*
 * 模块C - 缓存管理模块
 * 循环调用链: cache_data() -> process_data() (完成循环)
 */

#include <stdio.h>
#include <string.h>
#include "module_c.h"
#include "module_a.h"  // 会调用模块A的函数，完成循环！

/**
 * 缓存数据函数
 * 循环调用链的终点，但会重新调用process_data形成循环: cache_data -> process_data
 */
int cache_data(const char* data) {
    static int call_count = 0;
    call_count++;
    
    printf("[ModuleC] cache_data() 被调用，第 %d 次\n", call_count);
    printf("[ModuleC] 准备缓存数据: %s\n", data);
    
    // 防止无限递归
    if (call_count > 3) {
        printf("[ModuleC] 检测到递归调用超过限制，停止缓存\n");
        call_count = 0;
        return -1;
    }
    
    // 检查缓存空间
    if (!check_cache_space()) {
        printf("[ModuleC] 缓存空间不足\n");
        call_count = 0;
        return -1;
    }
    
    // 数据压缩
    printf("[ModuleC] 正在压缩数据...\n");
    
    // 存储到缓存
    printf("[ModuleC] 正在存储到缓存...\n");
    
    // 关键步骤：数据完整性验证 - 重新调用数据处理模块！
    // 这里完成了循环: process_data -> send_to_network -> cache_data -> process_data
    char verify_data[256];
    snprintf(verify_data, sizeof(verify_data), "验证:%s", data);
    
    printf("[ModuleC] 准备验证缓存数据的完整性\n");
    printf("[ModuleC] *** 重新调用数据处理模块进行验证 - 形成循环调用！***\n");
    
    int result = process_data(verify_data);
    
    printf("[ModuleC] 数据验证结果: %d\n", result);
    
    call_count--;
    return result >= 0 ? 0 : -1;
}

/**
 * 检查缓存空间
 */
int check_cache_space(void) {
    printf("[ModuleC] check_cache_space() 检查缓存空间\n");
    // 模拟缓存空间检查
    printf("[ModuleC] 缓存空间充足\n");
    return 1;
}

/**
 * 压缩数据函数
 */
void compress_data(const char* input, char* output) {
    printf("[ModuleC] compress_data() 压缩数据\n");
    
    if (!input || !output) return;
    
    // 简单的压缩模拟：去掉空格
    int i = 0, j = 0;
    while (input[i] && j < 255) {
        if (input[i] != ' ') {
            output[j++] = input[i];
        }
        i++;
    }
    output[j] = '\0';
    
    printf("[ModuleC] 数据压缩完成\n");
}

/**
 * 解压数据函数
 */
void decompress_data(const char* input, char* output) {
    printf("[ModuleC] decompress_data() 解压数据\n");
    
    if (!input || !output) return;
    
    // 简单的解压模拟：直接复制
    strcpy(output, input);
    
    printf("[ModuleC] 数据解压完成\n");
}

/**
 * 清空缓存
 */
void clear_cache(void) {
    printf("[ModuleC] clear_cache() 清空缓存\n");
    printf("[ModuleC] 缓存已清空\n");
}

/**
 * 获取缓存统计信息
 */
const char* get_cache_stats(void) {
    return "ModuleC: 缓存使用率 45%";
}
