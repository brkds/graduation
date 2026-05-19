/*
 * 简化的主程序 - 演示循环调用
 * 
 * 调用关系图:
 * main() -> process_data() -> send_to_network() -> cache_data() -> process_data() (循环!)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "module_a.h"
#include "module_b.h"
#include "module_c.h"

/**
 * 打印系统状态
 */
void print_system_status(void) {
    printf("\n=== 系统状态 ===\n");
    printf("%s\n", get_module_a_status());
    printf("%s\n", get_network_status());
    printf("%s\n", get_cache_stats());
    printf("================\n\n");
}

/**
 * 测试普通调用（非循环）
 */
void test_normal_calls(void) {
    printf("=== 测试普通函数调用 ===\n");
    
    // 测试数据验证
    int valid = validate_data("test data");
    printf("数据验证结果: %s\n", valid ? "通过" : "失败");
    
    // 测试网络连接
    int connected = check_network_connection();
    printf("网络连接状态: %s\n", connected ? "正常" : "失败");
    
    // 测试缓存空间
    int space_ok = check_cache_space();
    printf("缓存空间状态: %s\n", space_ok ? "充足" : "不足");
    
    printf("=== 普通调用测试完成 ===\n\n");
}

/**
 * 测试循环调用（危险）
 */
void test_circular_calls(void) {
    printf("=== 开始循环调用测试 ===\n");
    printf("警告：这将触发循环调用！\n");
    printf("调用链: process_data() -> send_to_network() -> cache_data() -> process_data()\n\n");
    
    // 这里会触发循环调用链！
    const char* test_data = "循环测试数据";
    int result = process_data(test_data);
    
    printf("\n循环调用测试结果: %d\n", result);
    printf("=== 循环调用测试结束 ===\n\n");
}

/**
 * 主函数
 */
int main(int argc, char* argv[]) {
    printf("==========================================\n");
    printf("       循环调用演示程序\n");
    printf("==========================================\n");
    printf("项目说明：\n");
    printf("- 本程序演示函数间的循环调用关系\n");
    printf("- 循环链：ModuleA -> ModuleB -> ModuleC -> ModuleA\n");
    printf("- 用于测试静态分析工具的循环检测能力\n");
    printf("==========================================\n\n");
    
    // 显示系统状态
    print_system_status();
    
    // 检查命令行参数
    int run_circular_test = 0;
    if (argc > 1 && strcmp(argv[1], "--circular") == 0) {
        run_circular_test = 1;
    }
    
    // 先测试普通调用
    test_normal_calls();
    
    // 根据参数决定是否运行循环调用测试
    if (run_circular_test) {
        test_circular_calls();
    } else {
        printf("=== 跳过循环调用测试 ===\n");
        printf("提示：使用 --circular 参数运行循环调用测试\n");
        printf("例如：./simple_main --circular\n\n");
    }
    
    // 清理操作
    clear_cache();
    
    printf("程序执行完成。\n");
    printf("\n调用关系总结：\n");
    printf("1. main() -> test_normal_calls() -> validate_data()\n");
    printf("2. main() -> test_normal_calls() -> check_network_connection()\n");
    printf("3. main() -> test_normal_calls() -> check_cache_space()\n");
    if (run_circular_test) {
        printf("4. main() -> test_circular_calls() -> process_data() -> send_to_network() -> cache_data() -> process_data() [循环!]\n");
    }
    printf("5. main() -> clear_cache()\n");
    
    return 0;
}
