#include "common.h"
#include <stdio.h>

int global_counter = 200;        // 真正的全局变量定义

static int counter = 300;        // file_b.c 独有的 static 变量，也与全局变量同名

static void helper(void) {       // static 函数，与 file_a 中的 helper 同名
    printf("helper in file_b\n");
}

void print_b(void) {
    helper();
    printf("file_b: static counter = %d, global_counter = %d\n", counter, global_counter);
    counter += 10;               // 修改 static 变量
    global_counter += 20;        // 修改全局变量
}

void access_global(void) {
    printf("access_global: global_counter = %d\n", global_counter);
}