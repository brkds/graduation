#ifndef COMMON_H
#define COMMON_H

extern int shared_var;                   // declared global
extern const int const_shared;           // declared const global
void external_function(void);            // declared function
void (*shared_callback)(void);           // declared function pointer

#endif
