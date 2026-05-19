/*
 * 模块B - 网络通信模块
 * 循环调用链: send_to_network() -> cache_data()
 */

#include <stdio.h>
#include <string.h>
#include "module_b.h"
#include "module_c.h"  // 会调用模块C的函数

/**
 * 网络数据发送函数
 * 循环调用链的中间环节: send_to_network -> cache_data -> process_data
 */
int send_to_network(const char* data) {
    static int call_count = 0;
    call_count++;
    
    printf("[ModuleB] send_to_network() 被调用，第 %d 次\n", call_count);
    printf("[ModuleB] 准备发送数据: %s\n", data);
    
    // 防止无限递归
    if (call_count > 3) {
        printf("[ModuleB] 检测到递归调用超过限制，停止发送\n");
        call_count = 0;
        return -1;
    }
    
    // 网络连接检查
    if (!check_network_connection()) {
        printf("[ModuleB] 网络连接失败\n");
        call_count = 0;
        return -1;
    }
    
    // 数据编码
    printf("[ModuleB] 正在编码数据...\n");
    
    // 模拟网络传输
    printf("[ModuleB] 正在传输数据...\n");
    
    // 调用缓存模块保存数据 - 这会继续循环调用链！
    printf("[ModuleB] 准备缓存发送的数据\n");
    int result = cache_data(data);
    
    printf("[ModuleB] 缓存模块返回结果: %d\n", result);
    
    call_count--;
    return result;
}

/**
 * 检查网络连接
 */
int check_network_connection(void) {
    printf("[ModuleB] check_network_connection() 检查网络连接\n");
    // 模拟网络检查
    printf("[ModuleB] 网络连接正常\n");
    return 1;
}

/**
 * 数据编码函数
 */
void encode_data(const char* input, char* output) {
    printf("[ModuleB] encode_data() 编码数据\n");
    
    if (!input || !output) return;
    
    // 简单的编码：每个字符+1
    int i = 0;
    while (input[i] && i < 255) {
        output[i] = input[i] + 1;
        i++;
    }
    output[i] = '\0';
    
    printf("[ModuleB] 数据编码完成\n");
}

/**
 * 数据解码函数
 */
void decode_data(const char* input, char* output) {
    printf("[ModuleB] decode_data() 解码数据\n");
    
    if (!input || !output) return;
    
    // 简单的解码：每个字符-1
    int i = 0;
    while (input[i] && i < 255) {
        output[i] = input[i] - 1;
        i++;
    }
    output[i] = '\0';
    
    printf("[ModuleB] 数据解码完成\n");
}

/**
 * 获取网络状态
 */
const char* get_network_status(void) {
    return "ModuleB: 网络连接正常";
}
