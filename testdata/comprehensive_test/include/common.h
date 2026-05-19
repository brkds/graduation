#ifndef COMMON_H
#define COMMON_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

// Linux内核特性：条件编译
#ifndef CONFIG_DEBUG
#define CONFIG_DEBUG 1
#endif

// Linux内核特性：宏复用生成函数
#define DECLARE_COUNTER_FUNC(name) \
    void increment_##name(void) { \
        global_counter++; \
        printf("Counter " #name " incremented to %d\n", global_counter); \
    }

// 全局变量声明 - 测试点1: 全局变量分析
extern int global_counter;
extern uint32_t shared_buffer[1024];
extern bool system_enabled;

// 全局指针声明 - 测试点4: 数据指针关系
extern int *global_ptr;
extern uint32_t *buffer_ptr;

// 结构体定义
typedef struct {
    int id;
    char name[32];
    void (*handler)(int);
} device_t;

extern device_t *main_device;

// 函数声明 - 测试点2: 函数原型分析
void init_system(void);
void cleanup_system(void);
int process_data(uint32_t *data, size_t len);
bool validate_input(int value);

#endif // COMMON_H
