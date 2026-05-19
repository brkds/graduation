# Compiler and flags
CXX = clang++-14
CXXFLAGS = -std=c++17 -Wall -g
LDFLAGS = -L/usr/lib/llvm-14/lib \
  -lclangTooling \
  -lclangFrontendTool \
  -lclangFrontend \
  -lclangSerialization \
  -lclangDriver \
  -lclangParse \
  -lclangSema \
  -lclangAnalysis \
  -lclangASTMatchers \
  -lclangAST \
  -lclangEdit \
  -lclangLex \
  -lclangBasic \
  -lLLVM-14 \
  -lsqlite3 \
  -lstdc++fs

# Directories
SRC_DIR = src
HANDLERS_DIR = $(SRC_DIR)/Handlers
UTILS_DIR = $(SRC_DIR)/Utils
OBJ_DIR = obj
OUT_DIR = output
SCRIPT_DIR = scripts

TEST_SINGLE_DIR = testdata/single
TEST_MULTI_DIR = testdata/multi
TEST_DIRECTORY_DIR = testdata/directory
TEST_LINUX_DIR = testdata/linux_full/linux-6.6

# Source files
SRCS = $(wildcard $(SRC_DIR)/*.cpp) \
       $(wildcard $(HANDLERS_DIR)/*.cpp) \
       $(wildcard $(UTILS_DIR)/*.cpp)
OBJS = $(patsubst $(SRC_DIR)/%.cpp, $(OBJ_DIR)/%.o, \
       $(patsubst $(HANDLERS_DIR)/%.cpp, $(OBJ_DIR)/Handlers/%.o, \
       $(patsubst $(UTILS_DIR)/%.cpp, $(OBJ_DIR)/Utils/%.o, $(SRCS))))

# Executable
TARGET = kernel_analyzer

# Include paths
INCLUDES = -I$(SRC_DIR) -I/usr/include/nlohmann -I/usr/lib/llvm-14/include

# 线程数选项
THREADS ?= 0

# Default target
all: $(TARGET)

# Link object files to create executable
$(TARGET): $(OBJS)
	$(CXX) $(OBJS) -o $@ $(LDFLAGS)

# Compile source files to object files
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp | $(OBJ_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

$(OBJ_DIR)/Handlers/%.o: $(HANDLERS_DIR)/%.cpp | $(OBJ_DIR)/Handlers
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

$(OBJ_DIR)/Utils/%.o: $(UTILS_DIR)/%.cpp | $(OBJ_DIR)/Utils
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

# Create object directories
$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

$(OBJ_DIR)/Handlers:
	mkdir -p $(OBJ_DIR)/Handlers

$(OBJ_DIR)/Utils:
	mkdir -p $(OBJ_DIR)/Utils

# Create output directory
$(OUT_DIR):
	mkdir -p $(OUT_DIR)

test-comprehensive: $(TARGET) | $(OUT_DIR)
	./$(TARGET) --db $(OUT_DIR)/comprehensive.db --enable-calls -j 1 $(TEST_LINUX_DIR)/comprehensive_test

test-random: $(TARGET) | $(OUT_DIR)
	./$(TARGET) --db $(OUT_DIR)/random.db --enable-calls -j $(THREADS) $(TEST_LINUX_DIR)/drivers/char/random.c

test-module: $(TARGET) | $(OUT_DIR)
	./$(TARGET) --db $(OUT_DIR)/hw_random.db --enable-calls -j $(THREADS) $(TEST_LINUX_DIR)/drivers/char/hw_random

test-full: $(TARGET) | $(OUT_DIR)
	./$(TARGET) --db $(OUT_DIR)/full.db --enable-calls -j $(THREADS)  $(TEST_LINUX_DIR) 
# ============================================
# 分析测试 - 直接输入目录
# ============================================

# 这行是关键！把命令行参数提取到 DIR 变量
DIR := $(filter-out test,$(MAKECMDGOALS))

test: $(TARGET) | $(OUT_DIR)
	@if [ -z "$(DIR)" ]; then \
		echo ""; \
		echo "Usage: make test <directory>"; \
		echo ""; \
		echo "Examples:"; \
		echo "  make test /home/user/mycode"; \
		echo "  make test ."; \
		echo "  make test /home/user/linux/drivers/char"; \
		echo ""; \
		exit 1; \
	fi
	@echo "========================================="
	@echo "Analyzing: $(DIR)"
	@echo "Database: $(OUT_DIR)/analysis.db"
	@echo "Threads: $(THREADS)"
	@echo "========================================="
	./$(TARGET) --db $(OUT_DIR)/analysis.db --enable-calls -j $(THREADS) $(DIR)
	. venv/bin/activate && python3 scripts/create_files_tree.py --db $(OUT_DIR)/analysis.db --dir $(DIR)

# 忽略额外参数（防止 "No rule to make target" 错误）
%:
	@:
# Clean up

clean-db:
	rm -f $(OUT_DIR)/analysis.db

clean:
	rm -rf $(OBJ_DIR) $(TARGET) $(OUT_DIR)

# Phony targets
.PHONY: all test-single test-multi test-directory test-random test-mpfs test-module test-full clean