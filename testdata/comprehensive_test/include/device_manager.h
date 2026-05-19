#ifndef DEVICE_MANAGER_H
#define DEVICE_MANAGER_H

#include "common.h"

// 设备管理函数声明
void init_device_manager(void);
int register_device(int id, const char *name, void (*handler)(int));
void trigger_device(int index, int value);
void print_current_device(void);

#endif // DEVICE_MANAGER_H
