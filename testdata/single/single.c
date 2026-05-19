int global_var = 0; // 全局变量
int *global_ptr = &global_var; // 全局指针

struct Inner {
    int val;
}; //  结构体

struct Outer {
    struct Inner *inner_ptr;
    int (*func_ptr)(int);
}; // 结构体指针和函数指针

struct Outer global_struct;
struct Inner global_inner = { 42 };
struct Inner *global_inner_array[2]; // 结构体指针数组
int global_array[5]; // 数组

int add_one(int x) {
    return x + 1;
}
int (*function_table[2])(int) = { add_one, 0 }; // 函数指针数组

void init() {
    global_ptr = &global_var; // read global_var, write global_ptr
    *global_ptr = 100; // write global_var

    global_struct.inner_ptr = &global_inner; // read global_inner, write global_struct.inner_ptr
    global_struct.inner_ptr->val = 123; // write global_inner

    global_inner_array[1] = &global_inner; // read global_inner, write global_inner_array[1]
    global_inner_array[1]->val = 555; // write global_inner
}

void use_func_pointer(int idx) {
    if (function_table[idx]) {
        int result = function_table[idx](global_var);
    }
} // if idx is 0, then should record add_one read global_var
void execute(int (*func)(int), int x) {
    int result = func(x);
}
void modify_global(int *ptr) {
    *ptr = 999;
}

struct Complex {
    struct Outer outer;
}; // 嵌套结构体

struct Complex global_complex;

void complex_access() {
    global_complex.outer.inner_ptr = &global_inner; // read global_inner, write global_complex.outer.inner_ptr
    global_complex.outer.inner_ptr->val = 789; // write global_inner
}

struct Data {
    int data;
};

struct Data data_array[3]; // 结构体数组

void access_data_array() {
    data_array[2].data = 222; // write data_array[2].data TODO
}

inline int inline_inc(int x) {
    return x + 1;
} // 内联函数

void use_inline() {
    int y = inline_inc(global_var); // read  global_var
}

void test_all() {
    init();
    use_func_pointer(0);
    execute(add_one, 5);
    modify_global(&global_var);
    complex_access();
    access_data_array();
    use_inline();
}
