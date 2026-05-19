// Test file for data pointer names and filtering
struct test_struct {
    int data;
    int *data_ptr;
    void (*func_ptr)(void);
};
int a = 0;
struct nested_struct {
    struct test_struct inner;
    int value;
};

// Global variables for testing
int global_var = 42;
int another_global = 100;

// Test normal data pointer assignments
void test_normal_pointers(void) {
    struct test_struct obj;
    struct nested_struct nested;
    int *simple_ptr;
    
    // Simple assignments - should be recorded
    simple_ptr = &global_var;             // Should record: simple_ptr -> global_var
    obj.data_ptr = &global_var;           // Should record: obj.data_ptr -> global_var
    nested.inner.data_ptr = &another_global; // Should record: nested.inner.data_ptr -> another_global
}

// Test with arrow operator
void test_arrow_pointers(void) {
    struct test_struct *ptr_obj;
    struct nested_struct *ptr_nested;
    
    // Arrow assignments - should be recorded
    ptr_obj->data_ptr = &global_var;           // Should record: ptr_obj->data_ptr -> global_var
    ptr_nested->inner.data_ptr = &another_global; // Should record: ptr_nested->inner.data_ptr -> another_global
}

// Test that should be filtered out (simulate kernel infrastructure)
// This simulates what the static_call macros would generate
void *__UNIQUE_ID___addressable___SCK__test123 = &global_var; // Should be filtered out
void *__SCK__another_test = &another_global;                 // Should be filtered out

// Normal global pointer - should NOT be filtered
int *normal_global_ptr = &global_var;  // Should be recorded 