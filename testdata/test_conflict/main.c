#include "common.h"

extern int a;
int main(void) {
    print_a();
    global_counter = 150; // 修改全局变量
    global_counter--;
    a++;
    print_b();
    access_global();
    return 0;
}