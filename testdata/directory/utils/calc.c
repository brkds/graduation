#include "calc.h"
extern int a; // should be extracted
uint32_t sum = 0;
static uint32_t calc_count = 0;
uint32_t add(uint32_t a, uint32_t b) {
    sum = a + b;
    calc_count++;
    return sum;
}

void reset_data(int32_t *ptr) {
    *ptr = 0;
    global_count = 0;
    calc_count = 0;
    a++;
}