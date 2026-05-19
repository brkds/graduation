// 过滤式检测函数中的全局变量读访问
@initialize:python@
@@

# 加载函数白名单
valid_functions = set()
try:
    with open("/home/zwy/project2721707-302151/ctags_validation/filtered_rules/valid_functions.txt", "r") as f:
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
    with open("/home/zwy/project2721707-302151/ctags_validation/filtered_rules/valid_variables.txt", "r") as f:
        for line in f:
            var_name = line.strip()
            if var_name:
                valid_variables.add(var_name)
    print(f"加载了 {len(valid_variables)} 个有效全局变量")
except Exception as e:
    print(f"无法加载变量白名单: {e}")

@rule@
identifier func, var;
@@

func(...) {
    ...
    var
    ...
}

@script:python@
func << rule.func;
var << rule.var;
@@

# 只处理白名单中的函数和全局变量
if func in valid_functions and var in valid_variables:
    print(f"read|{func}|{var}")
