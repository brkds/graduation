# 循环调用项目 (Circular Call Project)

## 项目概述

这是一个专门设计的C语言项目，用于演示函数之间的**循环调用**关系。该项目包含两个版本，都清晰地展示了循环调用链，用于测试静态分析工具（如kernel_analyzer）对循环调用的检测能力。

## 核心特性

### 循环调用链

#### 版本1：模块化循环调用 (simple_main)
```
process_data() → send_to_network() → cache_data() → process_data()
```

- **`process_data()`** (module_a.c): 数据处理函数，调用网络模块发送数据
- **`send_to_network()`** (module_b.c): 网络发送函数，调用缓存模块保存数据  
- **`cache_data()`** (module_c.c): 缓存函数，重新调用数据处理模块进行验证

#### 版本2：最小循环演示 (simple_cycle)
```
function_a() → function_b() → function_c() → function_a()
```

## 文件结构

```
circular_call_project/
├── simple_main.c      # 主程序（模块化版本）
├── module_a.c/.h      # 模块A：数据处理
├── module_b.c/.h      # 模块B：网络通信
├── module_c.c/.h      # 模块C：缓存管理
├── simple_cycle.c     # 最小循环演示
├── Makefile          # 构建配置
└── README.md         # 项目文档
```

## 循环调用检测目标

该项目专为测试以下静态分析功能而设计：

1. **循环调用检测**: 能否正确识别 A→B→C→A 的循环调用链
2. **调用图生成**: 能否生成包含循环的调用关系图

## 使用建议

1. **学习目的**: 了解循环调用的危害和检测方法
2. **工具测试**: 验证Visual X的功能
3. **代码审查**: 作为代码审查的反面教材

## 注意事项

⚠️ **重要警告**:
- 不要在生产环境中使用此代码结构
- 运行循环调用测试时要小心栈溢出
- 该项目仅用于教学和测试目的
