#!/bin/bash

# ctags验证执行脚本
# 使用ctags工具验证数据库中函数和变量识别的准确性

set -e  # 遇到错误时退出

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_FILE="$PROJECT_ROOT/linux.db"
SOURCE_DIR="$PROJECT_ROOT/testdata/linux_full/linux-6.6"
OUTPUT_DIR="$SCRIPT_DIR/ctags_output"
REPORT_FILE="$SCRIPT_DIR/ctags_validation_report.json"
PYTHON_SCRIPT="$SCRIPT_DIR/ctags_validation.py"
COMPILE_COMMANDS=""
SUBSYSTEM=""
SINGLE_FILE=""
DRY_RUN=false

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印信息函数
print_info() {
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

# 显示使用说明
show_usage() {
    echo "ctags验证工具使用说明"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help         显示此帮助信息"
    echo "  -d, --db PATH      指定数据库文件路径 (默认: $DB_FILE)"
    echo "  -s, --source PATH  指定Linux源码目录 (默认: $SOURCE_DIR)"
    echo "  -o, --output PATH  指定ctags输出目录 (默认: $OUTPUT_DIR)"
    echo "  -r, --report PATH  指定验证报告输出文件 (默认: $REPORT_FILE)"
    echo "  -c, --compile-commands PATH  指定compile_commands.json文件路径"
    echo "  --subsystem PATH   指定要验证的子系统 (如: mm, fs, drivers/gpu)"
    echo "  --single-file PATH 指定要验证的单个文件路径"
    echo "  --dry-run          只显示将要执行的命令，不实际执行"
    echo "  --clean            清理之前的输出文件"
    echo ""
    echo "示例:"
    echo "  $0                           # 使用默认参数运行验证"
    echo "  $0 --clean                   # 清理输出文件"
    echo "  $0 -d my.db -s /path/to/src  # 使用自定义数据库和源码路径"
    echo "  $0 --subsystem mm            # 只验证内存管理子系统"
    echo "  $0 --compile-commands compile_commands.json  # 使用编译命令文件"
    echo "  $0 --subsystem fs --compile-commands compile_commands.json  # 组合使用"
    echo "  $0 --single-file /path/to/file.c  # 验证单个文件"
    echo ""
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖工具..."
    
    # 检查ctags
    if ! command -v ctags &> /dev/null; then
        print_error "ctags未安装，请先安装ctags工具"
        print_info "Ubuntu/Debian: sudo apt-get install ctags"
        print_info "CentOS/RHEL: sudo yum install ctags"
        exit 1
    fi
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3未安装，请先安装Python3"
        exit 1
    fi
    
    # 检查sqlite3
    if ! command -v sqlite3 &> /dev/null; then
        print_error "sqlite3未安装，请先安装sqlite3"
        exit 1
    fi
    
    print_success "依赖检查通过"
}

# 检查文件是否存在
check_files() {
    print_info "检查输入文件..."
    
    if [ ! -f "$DB_FILE" ]; then
        print_error "数据库文件不存在: $DB_FILE"
        exit 1
    fi
    
    if [ ! -d "$SOURCE_DIR" ]; then
        print_error "源码目录不存在: $SOURCE_DIR"
        exit 1
    fi
    
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        print_error "Python验证脚本不存在: $PYTHON_SCRIPT"
        exit 1
    fi
    
    # 检查编译命令文件
    if [ -n "$COMPILE_COMMANDS" ] && [ ! -f "$COMPILE_COMMANDS" ]; then
        print_error "compile_commands.json文件不存在: $COMPILE_COMMANDS"
        exit 1
    fi
    
    # 检查子系统目录
    if [ -n "$SUBSYSTEM" ]; then
        SUBSYSTEM_PATH="$SOURCE_DIR/$SUBSYSTEM"
        if [ ! -d "$SUBSYSTEM_PATH" ]; then
            print_error "子系统目录不存在: $SUBSYSTEM_PATH"
            exit 1
        fi
    fi
    
    print_success "输入文件检查通过"
}

# 清理输出文件
clean_output() {
    print_info "清理输出文件..."
    
    if [ -d "$OUTPUT_DIR" ]; then
        rm -rf "$OUTPUT_DIR"
        print_success "已删除输出目录: $OUTPUT_DIR"
    fi
    
    if [ -f "$REPORT_FILE" ]; then
        rm -f "$REPORT_FILE"
        print_success "已删除报告文件: $REPORT_FILE"
    fi
    
    # 清理可能的临时文件
    find "$SCRIPT_DIR" -name "*.tmp" -delete 2>/dev/null || true
    find "$SCRIPT_DIR" -name "tags" -delete 2>/dev/null || true
    
    print_success "清理完成"
}

# 显示系统信息
show_system_info() {
    print_info "系统信息:"
    echo "  操作系统: $(uname -s)"
    echo "  内核版本: $(uname -r)"
    echo "  ctags版本: $(ctags --version | head -1)"
    echo "  Python版本: $(python3 --version)"
    echo "  SQLite版本: $(sqlite3 --version)"
    echo ""
}

# 显示验证配置
show_config() {
    print_info "验证配置:"
    echo "  数据库文件: $DB_FILE"
    echo "  源码目录: $SOURCE_DIR"
    echo "  输出目录: $OUTPUT_DIR"
    echo "  报告文件: $REPORT_FILE"
    echo "  Python脚本: $PYTHON_SCRIPT"
    
    if [ -n "$COMPILE_COMMANDS" ]; then
        echo "  编译命令文件: $COMPILE_COMMANDS"
    else
        echo "  编译命令文件: 未指定 (使用默认选项)"
    fi
    
    if [ -n "$SUBSYSTEM" ]; then
        echo "  验证子系统: $SUBSYSTEM"
        # 显示子系统基本信息
        SUBSYSTEM_PATH="$SOURCE_DIR/$SUBSYSTEM"
        if [ -d "$SUBSYSTEM_PATH" ]; then
            C_FILES=$(find "$SUBSYSTEM_PATH" -name "*.c" | wc -l)
            H_FILES=$(find "$SUBSYSTEM_PATH" -name "*.h" | wc -l)
            echo "  子系统文件: ${C_FILES} 个.c文件, ${H_FILES} 个.h文件"
        fi
    else
        echo "  验证子系统: 全部 (整个源码树)"
    fi
    
    echo ""
}

# 执行验证
run_validation() {
    print_info "开始ctags验证..."
    
    # 创建输出目录
    mkdir -p "$OUTPUT_DIR"
    
    # 构建python命令
    PYTHON_CMD="python3 $PYTHON_SCRIPT --db $DB_FILE --source $SOURCE_DIR --output $OUTPUT_DIR --report $REPORT_FILE"
    
    if [[ -n "$COMPILE_COMMANDS_FILE" ]]; then
        PYTHON_CMD="$PYTHON_CMD --compile-commands $COMPILE_COMMANDS_FILE"
    fi
    
    if [[ -n "$SUBSYSTEM" ]]; then
        PYTHON_CMD="$PYTHON_CMD --subsystem $SUBSYSTEM"
    fi
    
    if [[ -n "$SINGLE_FILE" ]]; then
        PYTHON_CMD="$PYTHON_CMD --single-file $SINGLE_FILE"
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "将要执行的命令:"
        echo "  $PYTHON_CMD"
        
        if [[ -n "$SINGLE_FILE" ]]; then
            echo ""
            print_info "将要验证的单个文件:"
            echo "    $SINGLE_FILE"
        elif [[ -n "$SUBSYSTEM" ]]; then
            echo ""
            print_info "将要验证的子系统文件:"
            if [[ -d "$SOURCE_DIR/$SUBSYSTEM" ]]; then
                find "$SOURCE_DIR/$SUBSYSTEM" -name "*.c" 2>/dev/null | head -5 | while read file; do
                    echo "    $(basename "$file")"
                done
                C_COUNT=$(find "$SOURCE_DIR/$SUBSYSTEM" -name "*.c" 2>/dev/null | wc -l)
                if [[ $C_COUNT -gt 5 ]]; then
                    echo "    ... 共 $C_COUNT 个.c文件"
                fi
            fi
        fi
        
        print_success "ctags验证流程完成！"
        echo ""
        print_info "详细验证报告已保存到: $REPORT_FILE"
        print_info "可以使用以下命令查看:"
        echo "  cat '$REPORT_FILE' | python3 -m json.tool"
        echo ""
        print_info "查看差异分析 (需要安装jq):"
        echo "  # 查看只有ctags识别的函数:"
        echo "  jq '.difference_analysis.functions.file_differences' '$REPORT_FILE'"
        echo "  # 查看只有数据库识别的变量:"
        echo "  jq '.difference_analysis.variables.file_differences' '$REPORT_FILE'"
        echo ""
        print_info "ctags输出文件保存在: $OUTPUT_DIR"
        echo "  tags - ctags生成的符号表文件"
        return 0
    fi
    
    # 执行验证
    print_info "执行验证脚本..."
    if $PYTHON_CMD; then
        print_success "验证完成"
        
        # 显示报告摘要
        if [ -f "$REPORT_FILE" ]; then
            print_info "验证结果摘要:"
            python3 -c "
import json
try:
    with open('$REPORT_FILE', 'r') as f:
        data = json.load(f)
    
    # 显示元数据
    metadata = data.get('metadata', {})
    if metadata.get('subsystem'):
        print(f'  验证子系统: {metadata[\"subsystem\"]}')
    if metadata.get('compile_commands'):
        print(f'  使用编译命令: {metadata[\"compile_commands\"]}')
    
    # 显示摘要结果
    summary = data.get('summary', {})
    for category, metrics in summary.items():
        print(f'  {category.upper()}:')
        for metric, value in metrics.items():
            print(f'    {metric}: {value}')
    
    # 显示差异分析摘要
    diff_analysis = data.get('difference_analysis', {})
    if diff_analysis:
        print(f'  差异分析:')
        for category, analysis in diff_analysis.items():
            summary_info = analysis.get('summary', {})
            total_files = summary_info.get('total_files_with_differences', 0)
            ctags_only_files = summary_info.get('files_with_ctags_only', 0)
            db_only_files = summary_info.get('files_with_db_only', 0)
            print(f'    {category}: {total_files}个文件有差异 (ctags独有:{ctags_only_files}, 数据库独有:{db_only_files})')
            
except Exception as e:
    print(f'无法读取报告摘要: {e}')
"
        fi
        
    else
        print_error "验证执行失败"
        return 1
    fi
}

# 主程序
main() {
    # 解析命令行参数
    COMPILE_COMMANDS_FILE=""
    SUBSYSTEM=""
    SINGLE_FILE=""
    DRY_RUN=false
    CLEAN_ONLY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -d|--db)
                DB_FILE="$2"
                shift 2
                ;;
            -s|--source)
                SOURCE_DIR="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -r|--report)
                REPORT_FILE="$2"
                shift 2
                ;;
            --compile-commands)
                COMPILE_COMMANDS_FILE="$2"
                shift 2
                ;;
            --subsystem)
                SUBSYSTEM="$2"
                shift 2
                ;;
            --single-file)
                SINGLE_FILE="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --clean)
                CLEAN_ONLY=true
                shift
                ;;
            *)
                echo -e "${RED}[ERROR]${NC} 未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # 如果只是清理，执行清理后退出
    if [ "$CLEAN_ONLY" = "true" ]; then
        clean_output
        exit 0
    fi
    
    # 显示工具信息
    echo "========================================"
    echo "    Linux源码ctags验证工具"
    if [[ -n "$SINGLE_FILE" ]]; then
        echo "    单文件验证: $SINGLE_FILE"
    elif [[ -n "$SUBSYSTEM" ]]; then
        echo "    子系统验证: $SUBSYSTEM"
    else
        echo "    全源码树验证"
    fi
    echo "========================================"
    
    # 系统信息
    print_info "系统信息:"
    echo "  操作系统: $(uname -s)"
    echo "  内核版本: $(uname -r)"
    echo "  ctags版本: $(ctags --version 2>/dev/null | head -1 || echo '未安装')"
    echo "  Python版本: $(python3 --version 2>/dev/null || echo '未安装')"
    echo "  SQLite版本: $(sqlite3 --version 2>/dev/null || echo '未安装')"
    echo ""
    
    # 验证配置
    print_info "验证配置:"
    echo "  数据库文件: $DB_FILE"
    echo "  源码目录: $SOURCE_DIR"
    echo "  输出目录: $OUTPUT_DIR"
    echo "  报告文件: $REPORT_FILE"
    echo "  Python脚本: $PYTHON_SCRIPT"
    
    if [[ -n "$COMPILE_COMMANDS_FILE" ]]; then
        echo "  编译命令文件: $COMPILE_COMMANDS_FILE"
    else
        echo "  编译命令文件: 未指定 (使用默认选项)"
    fi
    
    if [[ -n "$SINGLE_FILE" ]]; then
        echo "  验证单文件: $SINGLE_FILE"
    elif [[ -n "$SUBSYSTEM" ]]; then
        echo "  验证子系统: $SUBSYSTEM"
        # 统计子系统文件
        if [[ -d "$SOURCE_DIR/$SUBSYSTEM" ]]; then
            C_FILES=$(find "$SOURCE_DIR/$SUBSYSTEM" -name "*.c" 2>/dev/null | wc -l)
            H_FILES=$(find "$SOURCE_DIR/$SUBSYSTEM" -name "*.h" 2>/dev/null | wc -l)
            echo "  子系统文件: $C_FILES 个.c文件, $H_FILES 个.h文件"
        fi
    else
        echo "  验证范围: 整个源码树"
    fi
    echo ""
    
    # 检查依赖和文件
    check_dependencies
    check_files
    
    # 执行验证
    run_validation
    
    echo ""
    print_success "ctags验证流程完成！"
    
    if [ -f "$REPORT_FILE" ]; then
        echo ""
        print_info "详细验证报告已保存到: $REPORT_FILE"
        print_info "可以使用以下命令查看:"
        echo "  cat '$REPORT_FILE' | python3 -m json.tool"
        
        # 如果有差异分析，提供查看建议
        if command -v jq &> /dev/null; then
            echo ""
            print_info "查看差异分析 (需要安装jq):"
            echo "  # 查看只有ctags识别的函数:"
            echo "  jq '.difference_analysis.functions.file_differences' '$REPORT_FILE'"
            echo "  # 查看只有数据库识别的变量:"
            echo "  jq '.difference_analysis.variables.file_differences' '$REPORT_FILE'"
        fi
    fi
    
    if [ -d "$OUTPUT_DIR" ]; then
        echo ""
        print_info "ctags输出文件保存在: $OUTPUT_DIR"
        echo "  tags - ctags生成的符号表文件"
        if [ -f "$OUTPUT_DIR/ctags.conf" ]; then
            echo "  ctags.conf - ctags配置文件 (编译选项)"
        fi
    fi
}

# 执行主程序
main "$@" 