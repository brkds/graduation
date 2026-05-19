#!/bin/bash

# Visual X - C语言代码静态分析平台 - Docker快速启动脚本

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

# 显示欢迎信息
show_banner() {
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE} __     __  _                         _    __  __${NC}"
    echo -e "${BLUE} \\ \\   / / (_)  ___   _   _    __ _  | |   \\ \\/ /${NC}"
    echo -e "${BLUE}  \\ \\ / /  | | / __| | | | |  / _\` | | |    \\  / ${NC}"
    echo -e "${BLUE}   \\ V /   | | \\__ \\ | |_| | | (_| | | |    /  \\ ${NC}"
    echo -e "${BLUE}    \\_/    |_| |___/  \\____|  \\____| |_|   /_/\\_\\ ${NC}"
    echo
    echo -e "${GREEN}         Visual X - C语言代码静态分析平台${NC}"
    echo -e "${GREEN}         Docker容器化部署脚本${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
}

# 检查Docker环境
check_docker() {
    log_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        echo "安装指南: https://docs.docker.com/engine/install/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        echo "安装指南: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi
    
    log_info "✓ Docker环境检查通过"
}

# 检查环境配置
check_env() {
    log_info "检查环境配置..."
    
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            log_warn ".env文件不存在，正在从env.example创建..."
            cp env.example .env
            log_warn "请编辑.env文件，设置您的GEMINI_API_KEY"
            echo
            echo -e "${YELLOW}请按以下步骤配置:${NC}"
            echo "1. 编辑 .env 文件"
            echo "2. 设置 GEMINI_API_KEY=your_actual_api_key"
            echo "3. 保存后重新运行此脚本"
            echo
            read -p "是否现在就编辑 .env 文件？ (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                ${EDITOR:-nano} .env
            else
                exit 1
            fi
        else
            log_error "env.example文件不存在，请手动创建.env文件"
            exit 1
        fi
    fi
    
    # 检查GEMINI_API_KEY是否已设置
    source .env
    if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ]; then
        log_error "请在.env文件中设置有效的GEMINI_API_KEY"
        exit 1
    fi
    
    log_info "✓ 环境配置检查通过"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    # 使用固定的绝对路径
    mkdir -p /home/zwy/visual-x/projects
    mkdir -p /home/zwy/visual-x/data
    mkdir -p /home/zwy/visual-x/logs
    mkdir -p /home/zwy/visual-x/config
    
    log_info "✓ 目录创建完成"
}

# 构建镜像
build_image() {
    log_info "构建Docker镜像..."
    
    docker-compose build --no-cache
    
    log_info "✓ 镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 统一启动所有服务
    docker-compose up -d
    
    log_info "✓ 服务启动中..."
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."
    
    local max_wait=120
    local wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        if curl -s http://localhost:5001/ > /dev/null 2>&1; then
            log_info "✓ 服务已就绪"
            return 0
        fi
        
        echo -n "."
        sleep 2
        wait_time=$((wait_time + 2))
    done
    
    log_error "服务启动超时"
    return 1
}

# 显示访问信息
show_access_info() {
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}🎉 Visual X - C语言代码静态分析平台启动成功！${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo -e "${BLUE}📊 访问地址:${NC}"
    echo -e "  • 前端界面: ${GREEN}http://localhost:5001${NC}"
    echo -e "  • 后端API:  ${GREEN}http://localhost:5002${NC}"
    echo
    echo -e "${BLUE}📁 目录挂载:${NC}"
    echo -e "  • C项目路径: ${YELLOW}/home/zwy/visual-x/projects${NC} → /app/projects"
    echo -e "  • 数据存储:   ${YELLOW}/home/zwy/visual-x/data${NC} → /app/data"
    echo -e "  • 日志文件:   ${YELLOW}/home/zwy/visual-x/logs${NC} → /var/log"
    echo
    echo -e "${BLUE}🔧 常用命令:${NC}"
    echo -e "  • 查看日志:   ${YELLOW}docker-compose logs -f${NC}"
    echo -e "  • 停止服务:   ${YELLOW}docker-compose down${NC}"
    echo -e "  • 重启服务:   ${YELLOW}docker-compose restart${NC}"
    echo -e "  • 进入容器:   ${YELLOW}docker-compose exec visual-x bash${NC}"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# 显示帮助
show_help() {
    echo "Visual X - C语言代码静态分析平台 - Docker快速启动脚本"
    echo
    echo "用法:"
    echo "  $0 [选项]"
    echo
    echo "选项:"
    echo "  start           启动服务（默认）"
    echo "  stop           停止所有服务"
    echo "  restart        重启服务"
    echo "  logs           查看服务日志"
    echo "  status         查看服务状态"
    echo "  clean          清理容器和镜像"
    echo "  help           显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0                # 启动服务"
    echo "  $0 stop          # 停止服务"
}

# 主逻辑
main() {
    local command=${1:-start}
    
    case "$command" in
        "start")
            show_banner
            check_docker
            check_env
            create_directories
            build_image
            start_services "$command"
            wait_for_services
            show_access_info
            ;;
        "stop")
            log_info "停止所有服务..."
            docker-compose down
            log_info "✓ 服务已停止"
            ;;
        "restart")
            log_info "重启服务..."
            docker-compose restart
            log_info "✓ 服务已重启"
            ;;
        "logs")
            docker-compose logs -f
            ;;
        "status")
            docker-compose ps
            ;;
        "clean")
            log_warn "这将删除所有容器和镜像，确定要继续吗？"
            read -p "请输入 'yes' 确认: " confirm
            if [ "$confirm" = "yes" ]; then
                docker-compose down --rmi all --volumes
                log_info "✓ 清理完成"
            else
                log_info "取消清理操作"
            fi
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