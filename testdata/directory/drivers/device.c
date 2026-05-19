#include <stdlib.h>
#include "device.h"

struct device *dev = NULL;
int a;
void init_device(void) {
    dev = malloc(sizeof(struct device));
    if (dev) {
        dev->id = 1;
        dev->callback = NULL;
    }
}