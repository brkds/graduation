# 使用 Clang 替代 GCC
CC = clang-14
CFLAGS = -Iinclude -Wall -g

SRC_DIR = .
OBJ_DIR = obj
SOURCES = main.c drivers/device.c utils/calc.c
OBJECTS = $(SOURCES:%.c=$(OBJ_DIR)/%.o)
TARGET = test_program

# 构建目标程序
$(TARGET): $(OBJECTS)
	$(CC) $(OBJECTS) -o $@

# 编译 C 文件为目标文件
$(OBJ_DIR)/%.o: %.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@

all: $(TARGET)

# 清理构建产物
clean:
	rm -rf $(OBJ_DIR) $(TARGET) compile_commands.json

.PHONY: all clean
