# 基础镜像 - 使用Ubuntu 22.04 以确保LLVM 14兼容性
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# 设置工作目录
WORKDIR /app

# 安装基础系统依赖
RUN apt-get update && apt-get install -y \
    # 基础工具
    build-essential \
    wget \
    curl \
    gnupg2 \
    software-properties-common \
    lsb-release \
    # Python和相关依赖
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    # 数据库
    sqlite3 \
    libsqlite3-dev \
    # 系统工具
    git \
    vim \
    htop \
    tree \
    file

# 安装LLVM 14（使用Ubuntu官方仓库）
RUN apt-get update && apt-get install -y \
    llvm-14 \
    llvm-14-dev \
    libllvm14 \
    clang-14 \
    clang-tools-14 \
    libclang-14-dev

# 设置clang默认版本并清理
RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-14 100 && \
    update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-14 100 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN echo "完成clang等包的安装"

# 创建虚拟环境
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 配置pip使用国内镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 升级pip
RUN pip install --upgrade pip --timeout 300

# 复制项目文件
COPY . /app/

# 安装Python依赖
RUN pip install -r backend/requirements.txt --timeout 300

# 设置kernel_analyzer可执行权限
RUN chmod +x /app/kernel_analyzer

# 创建数据目录
RUN mkdir -p /app/data /app/projects

# 复制启动脚本和工具脚本
COPY entrypoint.sh /app/entrypoint.sh
COPY scripts/create_files_tree.py /app/scripts/create_files_tree.py
RUN chmod +x /app/entrypoint.sh
RUN chmod +x /app/scripts/create_files_tree.py

# 暴露端口
EXPOSE 5002 5001

# 设置默认环境变量
ENV GEMINI_API_KEY=""
ENV PROJECT_PATH="/app/projects"
ENV DATABASE_PATH="/app/data"
ENV BACKEND_HOST="0.0.0.0"
ENV BACKEND_PORT="5002"
ENV FRONTEND_HOST="0.0.0.0"
ENV FRONTEND_PORT="5001"

# 启动脚本
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["start"]