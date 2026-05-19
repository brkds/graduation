#!/bin/bash

# 启动脚本
set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 检查环境变量
check_env() {
    log_info "检查环境变量..."
    
    if [ -z "$GEMINI_API_KEY" ]; then
        log_error "GEMINI_API_KEY 环境变量未设置！"
        log_info "请在启动容器时设置 -e GEMINI_API_KEY=your_api_key"
        exit 1
    fi
    
    log_info "✓ GEMINI_API_KEY 已设置"
    
    # 设置默认值
    export PROJECT_PATH=${PROJECT_PATH:-"/app/projects"}
    export DATABASE_PATH=${DATABASE_PATH:-"/app/data"}
    export BACKEND_HOST=${BACKEND_HOST:-"0.0.0.0"}
    export BACKEND_PORT=${BACKEND_PORT:-"5002"}
    export FRONTEND_HOST=${FRONTEND_HOST:-"0.0.0.0"}
    export FRONTEND_PORT=${FRONTEND_PORT:-"5001"}
    
    log_info "✓ 环境变量检查完成"
}

# 初始化目录
init_directories() {
    log_info "初始化目录结构..."
    
    mkdir -p "$PROJECT_PATH"
    mkdir -p "$DATABASE_PATH"
    
    log_info "✓ 目录结构初始化完成"
    log_debug "项目路径: $PROJECT_PATH"
    log_debug "数据库路径: $DATABASE_PATH"
}

# 自动分析项目
auto_analyze_projects() {
    log_info "检查并分析项目..."
    
    local db_file="/app/data/analysis.db"
    
    # 检查是否已有数据库文件
    if [ -f "$db_file" ]; then
        log_info "✓ 发现现有数据库: $db_file"
        return 0
    fi
    
    # 检查projects目录中的项目
    if [ ! -d "$PROJECT_PATH" ] || [ -z "$(ls -A "$PROJECT_PATH" 2>/dev/null)" ]; then
        log_warn "projects目录为空，跳过自动分析"
        return 0
    fi
    
    # 遍历projects目录中的项目
    for project_dir in "$PROJECT_PATH"/*; do
        if [ -d "$project_dir" ]; then
            local project_name=$(basename "$project_dir")
            log_info "发现项目: $project_name"
            
            # 分析项目
            if analyze_project "$project_dir" "$db_file"; then
                log_info "✓ 项目 $project_name 分析完成"
                
                # 运行create_files_tree.py构建文件树
                log_info "构建文件树..."
                if python /app/scripts/create_files_tree.py --db "$db_file" --dir "$project_dir"; then
                    log_info "✓ 文件树构建完成"
                else
                    log_warn "文件树构建失败"
                fi
                
                break  # 只分析第一个项目
            else
                log_error "项目 $project_name 分析失败"
            fi
        fi
    done
}

# 分析C项目
analyze_project() {
    local project_path="$1"
    local output_db="$2"
    
    if [ ! -d "$project_path" ]; then
        log_error "项目路径不存在: $project_path"
        return 1
    fi
    
    log_info "开始分析C项目: $project_path"
    log_info "输出数据库: $output_db"
    
    # 检查是否有compile_commands.json
    if [ -f "$project_path/compile_commands.json" ]; then
        log_info "✓ 发现 compile_commands.json，将进行复杂分析"
    else
        log_warn "未发现 compile_commands.json，将进行基础分析"
    fi
    
    # 运行kernel_analyzer
    log_info "运行 kernel_analyzer..."
    cd /app
    if ./kernel_analyzer -db "$output_db" "$project_path"; then
        log_info "✓ 项目分析完成"
        return 0
    else
        log_error "项目分析失败"
        return 1
    fi
}

# 启动后端服务
start_backend() {
    log_info "启动后端服务..."
    cd /app/backend
    
    # 设置数据库路径
    if [ -n "$DATABASE_FILE" ]; then
        export DATABASE_URI="sqlite:///$DATABASE_FILE"
        log_info "使用指定数据库: $DATABASE_FILE"
    else
        # 使用默认数据库
        default_db="/app/data/analysis.db"
        if [ -f "$default_db" ]; then
            export DATABASE_URI="sqlite:///$default_db"
            log_info "使用默认数据库: $default_db"
        else
            log_warn "默认数据库不存在，将创建新数据库"
        fi
    fi
    
    # 后台启动Flask应用
    python run.py > /var/log/backend.log 2>&1 &
    BACKEND_PID=$!
    
    log_info "✓ 后端服务已启动 (PID: $BACKEND_PID)"
    log_debug "后端监听: $BACKEND_HOST:$BACKEND_PORT"
}

# 启动前端服务
start_frontend() {
    log_info "启动前端服务..."
    cd /app/frontend
    
    # 更新前端配置中的后端地址
    if [ -f "app.py" ]; then
        sed -i "s|BACKEND_URL = \".*\"|BACKEND_URL = \"http://localhost:$BACKEND_PORT\"|g" app.py
    fi
    
    # 启动前端服务
    python -c "
from app import app
app.run(debug=False, host='$FRONTEND_HOST', port=$FRONTEND_PORT)
" > /var/log/frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    log_info "✓ 前端服务已启动 (PID: $FRONTEND_PID)"
    log_debug "前端监听: $FRONTEND_HOST:$FRONTEND_PORT"
}

# 等待服务启动
wait_for_services() {
    log_info "等待服务启动..."
    
    # 等待后端服务
    for i in {1..30}; do
        if curl -s "http://localhost:$BACKEND_PORT/api/v1/health" > /dev/null 2>&1; then
            log_info "✓ 后端服务就绪"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "后端服务启动超时"
            return 1
        fi
        sleep 1
    done
    
    # 等待前端服务
    for i in {1..30}; do
        if curl -s "http://localhost:$FRONTEND_PORT/" > /dev/null 2>&1; then
            log_info "✓ 前端服务就绪"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "前端服务启动超时"
            return 1
        fi
        sleep 1
    done
}

# 显示访问信息
show_access_info() {
    log_info "服务启动完成！"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}🎉 Visual X - C语言代码静态分析平台已启动${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo -e "${BLUE}📊 服务地址:${NC}"
    echo -e "  • 前端界面: ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "  • 后端API:  ${GREEN}http://localhost:$BACKEND_PORT${NC}"
    echo
    echo -e "${BLUE}📁 目录信息:${NC}"
    echo -e "  • 项目路径: ${YELLOW}$PROJECT_PATH${NC}"
    echo -e "  • 数据路径: ${YELLOW}$DATABASE_PATH${NC}"
    echo
    echo -e "${BLUE}🔧 环境配置:${NC}"
    echo -e "  • Gemini API: ${GREEN}已配置${NC}"
    echo -e "  • Clang版本: $(clang --version | head -n1)"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# 优雅停止
graceful_shutdown() {
    log_info "正在优雅停止服务..."
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        log_info "✓ 前端服务已停止"
    fi
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        log_info "✓ 后端服务已停止"
    fi
    
    log_info "服务已全部停止"
    exit 0
}

# 捕获停止信号
trap graceful_shutdown SIGTERM SIGINT

# 帮助信息
show_help() {
    echo "Visual X - C语言代码静态分析平台 - Docker容器启动脚本"
    echo
    echo "用法:"
    echo "  $0 [命令] [参数...]"
    echo
    echo "命令:"
    echo "  start                    启动完整服务（默认）"
    echo "  analyze <项目路径> [输出数据库]  分析指定C项目"
    echo "  backend                  仅启动后端服务"
    echo "  frontend                 仅启动前端服务"
    echo "  shell                    进入容器shell"
    echo "  help                     显示此帮助信息"
    echo
    echo "环境变量:"
    echo "  GEMINI_API_KEY          Gemini API密钥（必需）"
    echo "  PROJECT_PATH            C项目路径（默认：/app/projects）"
    echo "  DATABASE_PATH           数据库存储路径（默认：/app/data）"
    echo "  DATABASE_FILE           指定数据库文件"
    echo "  BACKEND_PORT            后端端口（默认：5002）"
    echo "  FRONTEND_PORT           前端端口（默认：5001）"
    echo
    echo "示例:"
    echo "  docker run -e GEMINI_API_KEY=your_key -p 5001:5001 image_name"
    echo "  docker run -e GEMINI_API_KEY=your_key -v /path/to/project:/app/projects image_name analyze /app/projects"
}

# 主逻辑
main() {
    local command=${1:-start}
    
    case "$command" in
        "start")
            check_env
            init_directories
            auto_analyze_projects
            start_backend
            start_frontend
            wait_for_services
            show_access_info
            
            # 保持容器运行
            while true; do
                sleep 10
                # 检查服务是否还在运行
                if ! kill -0 $BACKEND_PID 2>/dev/null; then
                    log_error "后端服务异常停止"
                    exit 1
                fi
                if ! kill -0 $FRONTEND_PID 2>/dev/null; then
                    log_error "前端服务异常停止"
                    exit 1
                fi
            done
            ;;
        "analyze")
            check_env
            init_directories
            local project_path="${2:-$PROJECT_PATH}"
            local output_db="${3:-$DATABASE_PATH/analysis_$(date +%Y%m%d_%H%M%S).db}"
            analyze_project "$project_path" "$output_db"
            ;;
        "backend")
            check_env
            start_backend
            log_info "后端服务已启动，保持运行..."
            wait
            ;;
        "frontend")
            start_frontend
            log_info "前端服务已启动，保持运行..."
            wait
            ;;
        "shell")
            log_info "进入容器shell..."
            exec /bin/bash
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 执行主逻辑
main "$@"