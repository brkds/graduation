#ifndef MEMORY_H
#define MEMORY_H

#include <stddef.h>
#include "common.h"

// 内存管理相关
extern void *heap_start;
extern void *heap_end;
extern size_t total_allocated;

// 内存操作函数
void* custom_malloc(size_t size);
void custom_free(void *ptr);
void memory_stats(void);
void garbage_collect(void);

#endif // MEMORY_H
