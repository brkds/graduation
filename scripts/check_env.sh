#!/bin/bash
echo "=== 硬件检查 ==="
echo "CPU 信息:"
lscpu | grep -E "Model name|Thread|Core|Socket"
echo -e "\nCPU 性能:"
sysbench cpu --threads=16 run | grep "events per second"
echo -e "\n内存信息:"
free -h
echo -e "\n存储空间:"
df -h /
echo -e "\n存储类型:"
lsblk -d -o NAME,ROTA

echo -e "\n=== 软件检查 ==="
echo "操作系统版本:"
lsb_release -a 2>/dev/null || cat /etc/os-release
echo -e "\nPython 版本:"
python3 --version
echo -e "\npip 版本:"
pip3 --version
echo -e "\nSQLite 版本:"
sqlite3 --version
echo -e "\ngcc 版本:"
gcc --version | head -n 1
echo -e "\nnm 版本:"
nm --version | head -n 1
echo -e "\nobjdump 版本:"
objdump --version | head -n 1
echo -e "\n工具链完整性:"
for tool in gcc nm objdump; do $tool --version >/dev/null && echo "$tool OK" || echo "$tool Missing"; done
echo -e "\nPython 依赖:"
python3 -c "import flask, sqlalchemy; print(flask.__version__, sqlalchemy.__version__)" 2>/dev/null || echo "依赖未安装"
