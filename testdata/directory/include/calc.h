#ifndef CALC_H
#define CALC_H

#include <stdint.h>

extern uint32_t sum;
extern int global_count;

uint32_t add(uint32_t a, uint32_t b);
void reset_data(int32_t *ptr);

#endif