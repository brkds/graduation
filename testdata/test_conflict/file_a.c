#include "common.h"
#include <stdio.h>

static int counter = 100;        // file_a.c 独有的 static 变量，与全局变量同名
int global_counter = 200;
static void helper(void) {       // static 函数，只在 file_a.c 内部使用
    printf("helper in file_a\n");
}

void print_a(void) {
    helper();                    // 调用 static 函数
    printf("file_a: counter = %d\n", counter);   // 读访问
    counter++;                   // 写访问
}