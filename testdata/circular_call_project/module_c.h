/*
 * 模块C头文件 - 缓存管理模块
 */

#ifndef MODULE_C_H
#define MODULE_C_H

/**
 * 缓存数据函数
 * 循环调用链的终点，会重新调用数据处理模块
 */
int cache_data(const char* data);

/**
 * 检查缓存空间
 */
int check_cache_space(void);

/**
 * 压缩数据函数
 */
void compress_data(const char* input, char* output);

/**
 * 解压数据函数
 */
void decompress_data(const char* input, char* output);

/**
 * 清空缓存
 */
void clear_cache(void);

/**
 * 获取缓存统计信息
 */
const char* get_cache_stats(void);

#endif /* MODULE_C_H */
