#include <stdio.h>
#include <stdlib.h>
#include "include/device.h"
#include "include/calc.h"

int global_count = 0;
static int *global_ptr = &global_count;
void increment_count(int *ptr) {
    (*ptr)++;
}

int main(void) {
    void (*func_ptr)(int *) = increment_count;

    init_device();
    if (dev) {
        printf("Device ID: %u\n", dev->id);
    }

    sum = add(5, 3);
    printf("Sum: %u\n", sum);

    reset_data(&global_count);
    printf("Global count after reset: %d\n", global_count);

    func_ptr(global_ptr);
    printf("Global count after increment: %d\n", *global_ptr);

    return 0;
}