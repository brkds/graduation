/*
 * 简化的循环调用演示
 * 
 * 明确的循环调用链: function_a() -> function_b() -> function_c() -> function_a()
 */

#include <stdio.h>
#include <stdlib.h>

// 函数声明
void function_a(int depth);
void function_b(int depth);
void function_c(int depth);

// 全局变量用于控制递归深度
static int max_depth = 3;

/**
 * 函数A - 循环调用链的起点
 * 调用关系: function_a -> function_b
 */
void function_a(int depth) {
    printf("[A] 函数A被调用，深度: %d\n", depth);
    
    if (depth >= max_depth) {
        printf("[A] 达到最大深度，停止递归\n");
        return;
    }
    
    // 调用函数B
    printf("[A] 调用函数B\n");
    function_b(depth + 1);
    
    printf("[A] 函数A执行完毕\n");
}

/**
 * 函数B - 循环调用链的中间环节
 * 调用关系: function_b -> function_c
 */
void function_b(int depth) {
    printf("[B] 函数B被调用，深度: %d\n", depth);
    
    if (depth >= max_depth) {
        printf("[B] 达到最大深度，停止递归\n");
        return;
    }
    
    // 调用函数C
    printf("[B] 调用函数C\n");
    function_c(depth + 1);
    
    printf("[B] 函数B执行完毕\n");
}

/**
 * 函数C - 循环调用链的终点，但会重新调用A形成循环
 * 调用关系: function_c -> function_a (形成循环!)
 */
void function_c(int depth) {
    printf("[C] 函数C被调用，深度: %d\n", depth);
    
    if (depth >= max_depth) {
        printf("[C] 达到最大深度，停止递归\n");
        return;
    }
    
    // 重新调用函数A，形成循环！
    printf("[C] 重新调用函数A - 形成循环调用！\n");
    function_a(depth + 1);
    
    printf("[C] 函数C执行完毕\n");
}

/**
 * 辅助函数1 - 不参与循环调用
 */
void helper_function1(void) {
    printf("[Helper1] 这是一个普通的辅助函数\n");
}

/**
 * 辅助函数2 - 调用辅助函数1
 */
void helper_function2(void) {
    printf("[Helper2] 调用辅助函数1\n");
    helper_function1();
}

/**
 * 初始化函数 - 调用辅助函数
 */
void initialize_system(void) {
    printf("[Init] 系统初始化\n");
    helper_function2();
    printf("[Init] 系统初始化完成\n");
}

/**
 * 清理函数 - 独立的清理逻辑
 */
void cleanup_system(void) {
    printf("[Cleanup] 系统清理\n");
}

/**
 * 主函数
 */
int main(int argc, char *argv[]) {
    printf("=== 循环调用演示程序 ===\n\n");
    
    // 解析命令行参数
    if (argc > 1) {
        max_depth = atoi(argv[1]);
        if (max_depth <= 0) max_depth = 3;
    }
    
    printf("最大递归深度设置为: %d\n\n", max_depth);
    
    // 初始化系统
    initialize_system();
    printf("\n");
    
    // 开始循环调用演示
    printf("=== 开始循环调用演示 ===\n");
    printf("调用链: A -> B -> C -> A (循环)\n\n");
    
    // 启动循环调用链
    function_a(0);
    
    printf("\n=== 循环调用演示结束 ===\n\n");
    
    // 清理系统
    cleanup_system();
    
    printf("\n程序执行完成\n");
    return 0;
}
