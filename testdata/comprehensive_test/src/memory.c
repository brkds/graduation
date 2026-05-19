#include "memory.h"
#include "common.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 测试点1: 内存管理相关全局变量定义
void *heap_start = NULL;
void *heap_end = NULL;
size_t total_allocated = 0;

// 静态内存管理变量
static void *memory_pool[100];
static bool pool_used[100] = {false};
static int pool_count = 0;

// 内部指针测试
static void **free_list = NULL;
static size_t *size_tracker = &total_allocated;

void* custom_malloc(size_t size) {
    if (size == 0) {
        return NULL;
    }
    
    // 测试点3: 全局变量访问
    void *ptr = malloc(size);
    if (ptr) {
        total_allocated += size; // 写访问
        
        // 测试点4: 指针关系管理
        if (heap_start == NULL) {
            heap_start = ptr; // 第一次分配时设置起始指针
        }
        heap_end = ptr; // 更新结束指针
        
        // 简单的内存池管理
        if (pool_count < 100) {
            memory_pool[pool_count] = ptr; // 测试点4: 指针数组操作
            pool_used[pool_count] = true;
            pool_count++; // 写访问静态变量
        }
        
        printf("Allocated %zu bytes at %p\n", size, ptr);
    }
    
    return ptr;
}

void custom_free(void *ptr) {
    if (!ptr) {
        return;
    }
    
    // 在内存池中查找并标记为未使用
    for (int i = 0; i < pool_count; i++) {
        if (memory_pool[i] == ptr) { // 测试点4: 指针比较
            pool_used[i] = false; // 写访问
            memory_pool[i] = NULL; // 测试点4: 指针置空
            break;
        }
    }
    
    free(ptr);
    printf("Freed memory at %p\n", ptr);
}

void memory_stats(void) {
    // 测试点3: 全局变量读访问
    printf("Memory Statistics:\n");
    printf("  Total allocated: %zu bytes\n", total_allocated);
    printf("  Heap start: %p\n", heap_start);
    printf("  Heap end: %p\n", heap_end);
    printf("  Pool count: %d\n", pool_count);
    
    // 统计活跃内存块
    int active_blocks = 0;
    for (int i = 0; i < pool_count; i++) {
        if (pool_used[i]) { // 读访问
            active_blocks++;
        }
    }
    printf("  Active blocks: %d\n", active_blocks);
    
    // 测试点3: 通过指针访问全局变量
    printf("  Size tracker value: %zu\n", *size_tracker);
}

void garbage_collect(void) {
    // 测试点3: 全局变量访问
    printf("Starting garbage collection...\n");
    
    int freed_count = 0;
    // 遍历内存池，释放未使用的内存
    for (int i = 0; i < pool_count; i++) {
        if (memory_pool[i] && !pool_used[i]) { // 读访问
            custom_free(memory_pool[i]);
            freed_count++;
        }
    }
    
    // 重置内存统计
    if (freed_count > 0) {
        total_allocated = 0; // 写访问全局变量
        heap_start = NULL;   // 测试点4: 指针重置
        heap_end = NULL;
        pool_count = 0;      // 写访问静态变量
        
        // 清空内存池
        memset(memory_pool, 0, sizeof(memory_pool));
        memset(pool_used, false, sizeof(pool_used));
    }
    
    printf("Garbage collection completed. Freed %d blocks.\n", freed_count);
}
