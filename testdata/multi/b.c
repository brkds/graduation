#include "common.h"

void user_function(void) {
    int tmp = shared_var;              // read
    shared_var = tmp + 1;              // write
}

void assign_func_ptr(void) {
    shared_callback = external_function; // function pointer assignment
}

void assign_data_ptr(void) {
    int *p = &shared_var;              // data pointer assignment
}
