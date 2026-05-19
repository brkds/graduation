#!/bin/bash

# Coccinelle验证系统便捷运行脚本
# 用法: ./run_coccinelle_validation.sh [选项]

set -e

# 默认配置
DB_FILE="../full.db"
SOURCE_DIR="../testdata/linux_full/linux-6.6"
VALIDATOR_SCRIPT="coccinelle_validation/scripts/filtered_fast_validator.py"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印帮助信息
print_help() {
    echo "Coccinelle验证系统便捷运行脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -f, --file FILE        验证单个文件 (例如: mm/memcontrol.c)"
    echo "  -s, --subsystem DIR    验证子系统 (例如: mm)"
    echo "  -d, --db DATABASE      指定数据库文件 (默认: ../full.db)"
    echo "  --source SOURCE_DIR    指定源码目录 (默认: ../testdata/linux_full/linux-6.6)"
    echo "  --output FILE          指定输出JSON报告文件"
    echo "  --accurate             使用精确验证器 (包含位置信息)"
    echo "  --performance          运行性能测试"
    echo "  -h, --help             显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -f mm/kfence/core.c                    # 验证单个小文件"
    echo "  $0 -s mm                                  # 验证mm子系统"
    echo "  $0 --performance -f mm/memcontrol.c       # 性能测试"
    echo "  $0 --accurate -f mm/backing-dev.c         # 使用精确验证器"
}

# 打印状态信息
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境
check_environment() {
    print_status "检查运行环境..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi
    
    # 检查Coccinelle
    if ! command -v spatch &> /dev/null; then
        print_error "Coccinelle (spatch) 未安装"
        exit 1
    fi
    
    # 检查数据库文件
    if [ ! -f "$DB_FILE" ]; then
        print_error "数据库文件不存在: $DB_FILE"
        exit 1
    fi
    
    # 检查源码目录
    if [ ! -d "$SOURCE_DIR" ]; then
        print_error "源码目录不存在: $SOURCE_DIR"
        exit 1
    fi
    
    # 检查验证器脚本
    if [ ! -f "$VALIDATOR_SCRIPT" ]; then
        print_error "验证器脚本不存在: $VALIDATOR_SCRIPT"
        exit 1
    fi
    
    print_success "环境检查通过"
}

# 解析命令行参数
FILE=""
SUBSYSTEM=""
OUTPUT_FILE=""
USE_ACCURATE=false
RUN_PERFORMANCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            FILE="$2"
            shift 2
            ;;
        -s|--subsystem)
            SUBSYSTEM="$2"
            shift 2
            ;;
        -d|--db)
            DB_FILE="$2"
            shift 2
            ;;
        --source)
            SOURCE_DIR="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --accurate)
            USE_ACCURATE=true
            shift
            ;;
        --performance)
            RUN_PERFORMANCE=true
            shift
            ;;
        -h|--help)
            print_help
            exit 0
            ;;
        *)
            print_error "未知选项: $1"
            print_help
            exit 1
            ;;
    esac
done

# 检查参数
if [ -z "$FILE" ] && [ -z "$SUBSYSTEM" ]; then
    print_error "必须指定 --file 或 --subsystem 参数"
    print_help
    exit 1
fi

# 检查环境
check_environment

# 选择验证器
if [ "$USE_ACCURATE" = true ]; then
    VALIDATOR_SCRIPT="coccinelle_validation/scripts/accurate_coccinelle_validator.py"
    print_status "使用精确验证器 (包含位置信息)"
elif [ "$RUN_PERFORMANCE" = true ]; then
    VALIDATOR_SCRIPT="coccinelle_validation/scripts/performance_test.py"
    print_status "运行性能测试"
else
    print_status "使用快速验证器 (推荐)"
fi

# 构建命令
CMD="python3 $VALIDATOR_SCRIPT --db $DB_FILE --source $SOURCE_DIR"

if [ -n "$FILE" ]; then
    CMD="$CMD --file $FILE"
    print_status "验证文件: $FILE"
elif [ -n "$SUBSYSTEM" ]; then
    CMD="$CMD --subsystem $SUBSYSTEM"
    print_status "验证子系统: $SUBSYSTEM"
fi

# 添加输出文件参数
if [ -n "$OUTPUT_FILE" ]; then
    CMD="$CMD --output $OUTPUT_FILE"
    print_status "输出文件: $OUTPUT_FILE"
fi

# 运行验证
print_status "开始验证..."
print_status "命令: $CMD"
echo ""

if $CMD; then
    print_success "验证完成！"
else
    print_error "验证失败！"
    exit 1
fi 