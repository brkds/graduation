# 简化版循环调用项目 Makefile
# 专注于演示循环调用关系

CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -g -O0
INCLUDES = -I.

# 简化版源文件
SIMPLE_SOURCES = simple_main.c module_a.c module_b.c module_c.c
SIMPLE_OBJECTS = $(SIMPLE_SOURCES:.c=.o)
SIMPLE_TARGET = simple_circular

# 最小循环演示
CYCLE_SOURCES = simple_cycle.c
CYCLE_OBJECTS = $(CYCLE_SOURCES:.c=.o)
CYCLE_TARGET = cycle_demo

# 头文件依赖
HEADERS = module_a.h module_b.h module_c.h

.PHONY: all simple cycle clean test test-cycle

# 默认构建简化版
all: simple

# 构建简化版（模块化的循环调用）
simple: $(SIMPLE_TARGET)

# 构建最小循环演示
cycle: $(CYCLE_TARGET)

# 构建所有版本
both: simple cycle

$(SIMPLE_TARGET): $(SIMPLE_OBJECTS)
	@echo "链接简化版可执行文件..."
	$(CC) $(SIMPLE_OBJECTS) -o $(SIMPLE_TARGET)
	@echo "简化版编译完成: $(SIMPLE_TARGET)"

$(CYCLE_TARGET): $(CYCLE_OBJECTS)
	@echo "链接循环演示可执行文件..."
	$(CC) $(CYCLE_OBJECTS) -o $(CYCLE_TARGET)
	@echo "循环演示编译完成: $(CYCLE_TARGET)"

%.o: %.c $(HEADERS)
	@echo "编译 $<..."
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# 测试简化版（安全模式）
test: $(SIMPLE_TARGET)
	@echo "=== 运行简化版测试（安全模式）==="
	./$(SIMPLE_TARGET)
	@echo "=== 简化版测试完成 ==="

# 测试循环调用（危险模式）
test-cycle: $(SIMPLE_TARGET)
	@echo "=== 运行循环调用测试（危险模式）==="
	@echo "警告：这将触发循环调用！"
	./$(SIMPLE_TARGET) --circular
	@echo "=== 循环调用测试完成 ==="

# 测试最小循环演示
test-minimal: $(CYCLE_TARGET)
	@echo "=== 运行最小循环演示 ==="
	./$(CYCLE_TARGET)
	@echo "=== 最小循环演示完成 ==="

# 显示调用关系图
show-calls:
	@echo "=== 函数调用关系图 ==="
	@echo ""
	@echo "简化版 ($(SIMPLE_TARGET)):"
	@echo "main()"
	@echo "├── print_system_status()"
	@echo "│   ├── get_module_a_status()"
	@echo "│   ├── get_network_status()"
	@echo "│   └── get_cache_stats()"
	@echo "├── test_normal_calls()"
	@echo "│   ├── validate_data()"
	@echo "│   ├── check_network_connection()"
	@echo "│   └── check_cache_space()"
	@echo "├── test_circular_calls()"
	@echo "│   └── process_data() ──┐"
	@echo "│       └── send_to_network() ──┐"
	@echo "│           └── cache_data() ──┐"
	@echo "│               └── process_data() ←─┘ [循环!]"
	@echo "└── clear_cache()"
	@echo ""
	@echo "最小演示 ($(CYCLE_TARGET)):"
	@echo "main()"
	@echo "├── initialize_system()"
	@echo "│   └── helper_function2()"
	@echo "│       └── helper_function1()"
	@echo "├── function_a() ──┐"
	@echo "│   └── function_b() ──┐"
	@echo "│       └── function_c() ──┐"
	@echo "│           └── function_a() ←─┘ [循环!]"
	@echo "└── cleanup_system()"
	@echo ""

# 静态分析
analyze:
	@echo "=== 静态代码分析 ==="
	@echo "检查简化版源码..."
	cppcheck --enable=all $(SIMPLE_SOURCES) 2>/dev/null || echo "未安装 cppcheck"
	@echo "检查最小演示源码..."
	cppcheck --enable=all $(CYCLE_SOURCES) 2>/dev/null || echo "未安装 cppcheck"

# 清理
clean:
	@echo "清理编译文件..."
	rm -f $(SIMPLE_OBJECTS) $(CYCLE_OBJECTS)
	rm -f $(SIMPLE_TARGET) $(CYCLE_TARGET)
	@echo "清理完成"

# 帮助信息
help:
	@echo "可用的make目标:"
	@echo "  simple       - 编译简化版循环调用程序"
	@echo "  cycle        - 编译最小循环演示程序"
	@echo "  both         - 编译所有版本"
	@echo "  test         - 运行简化版测试（安全模式）"
	@echo "  test-cycle   - 运行循环调用测试（危险模式）"
	@echo "  test-minimal - 运行最小循环演示"
	@echo "  show-calls   - 显示函数调用关系图"
	@echo "  analyze      - 运行静态代码分析"
	@echo "  clean        - 清理编译文件"
	@echo "  help         - 显示此帮助信息"

# 项目信息
info:
	@echo "=== 简化版循环调用项目 ==="
	@echo "目标：演示C语言中的循环调用关系"
	@echo ""
	@echo "文件结构："
	@echo "- simple_main.c, module_[abc].[ch] : 模块化循环调用"
	@echo "- simple_cycle.c                  : 最小循环演示"
	@echo ""
	@echo "循环调用链："
	@echo "process_data() -> send_to_network() -> cache_data() -> process_data()"
	@echo ""
	@echo "使用建议："
	@echo "1. 先运行 'make test' 测试安全模式"
	@echo "2. 再运行 'make test-cycle' 测试循环调用"
	@echo "3. 使用 'make show-calls' 查看调用关系"
