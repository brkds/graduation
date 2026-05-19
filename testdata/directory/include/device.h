#ifndef DEVICE_H
#define DEVICE_H

#include <stdint.h>

struct device {
    uint32_t id;
    void (*callback)(void);
};

extern struct device *dev;

void init_device(void);

#endif