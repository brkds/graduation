/*
 * 模块A头文件 - 数据处理模块
 */

#ifndef MODULE_A_H
#define MODULE_A_H

/**
 * 主要的数据处理函数
 * 循环调用链的起点
 */
int process_data(const char* data);

/**
 * 数据验证函数
 */
int validate_data(const char* data);

/**
 * 数据格式化函数
 */
void format_data(char* data);

/**
 * 获取模块状态
 */
const char* get_module_a_status(void);

#endif /* MODULE_A_H */
