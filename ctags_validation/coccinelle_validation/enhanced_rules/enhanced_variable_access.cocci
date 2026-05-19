// 增强版变量访问检测规则 - 支持复杂访问模式
// 解决当前规则无法检测的类型转换、函数参数等问题

@initialize:python@
@@

# 加载函数白名单
valid_functions = set()
try:
    with open("filtered_rules/valid_functions.txt", "r") as f:
        for line in f:
            func_name = line.strip()
            if func_name:
                valid_functions.add(func_name)
    print(f"加载了 {len(valid_functions)} 个有效函数")
except Exception as e:
    print(f"无法加载函数白名单: {e}")

# 加载全局变量白名单
valid_variables = set()
try:
    with open("filtered_rules/valid_variables.txt", "r") as f:
        for line in f:
            var_name = line.strip()
            if var_name:
                valid_variables.add(var_name)
    print(f"加载了 {len(valid_variables)} 个有效全局变量")
except Exception as e:
    print(f"无法加载变量白名单: {e}")

// 规则1: 基本变量访问（现有规则）
@basic_access@
identifier func, var;
@@

func(...) {
    ...
    var
    ...
}

@script:python@
func << basic_access.func;
var << basic_access.var;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|basic_access")

// 规则2: 类型转换中的变量访问
@type_cast_access@
identifier func, var;
type T;
@@

func(...) {
    ...
    (T)var
    ...
}

@script:python@
func << type_cast_access.func;
var << type_cast_access.var;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|type_cast")

// 规则3: 函数参数中的变量访问
@function_arg_access@
identifier func, var, callee;
@@

func(...) {
    ...
    callee(..., var, ...)
    ...
}

@script:python@
func << function_arg_access.func;
var << function_arg_access.var;
callee << function_arg_access.callee;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|function_arg|{callee}")

// 规则4: 返回语句中的变量访问
@return_access@
identifier func, var;
@@

func(...) {
    ...
    return var;
    ...
}

@script:python@
func << return_access.func;
var << return_access.var;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|return_stmt")

// 规则5: 返回语句中类型转换的变量访问
@return_cast_access@
identifier func, var;
type T;
@@

func(...) {
    ...
    return (T)var;
    ...
}

@script:python@
func << return_cast_access.func;
var << return_cast_access.var;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|return_cast")

// 规则6: 赋值中的类型转换
@assign_cast_access@
identifier func, var, target;
type T;
@@

func(...) {
    ...
    target = (T)var;
    ...
}

@script:python@
func << assign_cast_access.func;
var << assign_cast_access.var;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|assign_cast")

// 规则7: 取地址操作
@address_access@
identifier func, var;
@@

func(...) {
    ...
    &var
    ...
}

@script:python@
func << address_access.func;
var << address_access.var;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|address_of")

// 规则8: 数组下标中的变量
@array_index_access@
identifier func, var, array;
@@

func(...) {
    ...
    array[var]
    ...
}

@script:python@
func << array_index_access.func;
var << array_index_access.var;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|array_index")

// 规则9: 指针运算中的变量
@pointer_arith_access@
identifier func, var;
@@

func(...) {
    ...
    (
    var + ... |
    ... + var |
    var - ... |
    ... - var
    )
    ...
}

@script:python@
func << pointer_arith_access.func;
var << pointer_arith_access.var;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|pointer_arith")

// 规则10: 结构体字段访问中的变量
@struct_field_access@
identifier func, var;
identifier field;
@@

func(...) {
    ...
    var.field
    ...
}

@script:python@
func << struct_field_access.func;
var << struct_field_access.var;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|struct_field")

// 规则11: 条件表达式中的变量
@condition_access@
identifier func, var;
@@

func(...) {
    ...
    (
    if (var) ... |
    if (...var...) ... |
    while (var) ... |
    while (...var...) ... |
    for (...; var; ...) ... |
    for (...; ...var...; ...) ...
    )
    ...
}

@script:python@
func << condition_access.func;
var << condition_access.var;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|condition")

// 规则12: 宏参数中的变量
@macro_arg_access@
identifier func, var, macro;
@@

func(...) {
    ...
    macro(var)
    ...
}

@script:python@
func << macro_arg_access.func;
var << macro_arg_access.var;
macro << macro_arg_access.macro;
@@

if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}|macro_arg|{macro}") 