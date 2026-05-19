/*
 * 模块B头文件 - 网络通信模块
 */

#ifndef MODULE_B_H
#define MODULE_B_H

/**
 * 网络数据发送函数
 * 循环调用链的中间环节
 */
int send_to_network(const char* data);

/**
 * 检查网络连接
 */
int check_network_connection(void);

/**
 * 数据编码函数
 */
void encode_data(const char* input, char* output);

/**
 * 数据解码函数
 */
void decode_data(const char* input, char* output);

/**
 * 获取网络状态
 */
const char* get_network_status(void);

#endif /* MODULE_B_H */
