#include "common.h"
#include "internal.h"

int shared_var = 10;
const int const_shared = 999;

int internal_var = 100;                  // should be extracted
static int file_local = 42;             // should NOT be extracted

void external_function(void) {
    shared_var = 42;                    // write
}

void internal_function(void) {
    int temp = shared_var;             // read
    temp += const_shared;              // read
}

void (*shared_callback)(void) = external_function; // global func pointer

void test_data_pointer(void) {
    int *ptr1 = &shared_var;           // local pointer
    int *ptr2 = &internal_var;         // local pointer
}
