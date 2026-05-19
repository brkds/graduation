#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ctags验证工具快速测试脚本
用于验证工具是否正常工作，支持新功能测试
"""

import os
import sqlite3
import subprocess
from pathlib import Path
import json

def quick_test():
    """快速测试ctags验证工具"""
    
    print("🚀 ctags验证工具快速测试 (增强版)")
    print("=" * 50)
    
    # 检查基本工具
    print("\n1. 检查依赖工具...")
    
    tools = ['ctags', 'python3', 'sqlite3']
    for tool in tools:
        try:
            result = subprocess.run([tool, '--version'], 
                                    capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                print(f"   ✅ {tool}: {version}")
            else:
                print(f"   ❌ {tool}: 未安装或无法执行")
                return False
        except Exception as e:
            print(f"   ❌ {tool}: 检查失败 - {e}")
            return False
    
    # 检查可选工具
    optional_tools = ['jq']
    for tool in optional_tools:
        try:
            result = subprocess.run([tool, '--version'], 
                                    capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                print(f"   ✅ {tool} (可选): {version}")
            else:
                print(f"   ⚠️ {tool} (可选): 未安装，某些功能受限")
        except Exception:
            print(f"   ⚠️ {tool} (可选): 未安装，某些功能受限")
    
    # 检查文件
    print("\n2. 检查必要文件...")
    
    project_root = Path(__file__).parent.parent
    
    files_to_check = {
        'full6.12.db': project_root / 'full6.12.db',
        'Linux源码': project_root / 'testdata/linux_full/linux-6.6',
        'Python脚本': project_root / 'validation/ctags_validation.py',
        'Shell脚本': project_root / 'validation/run_ctags_validation.sh'
    }
    
    for name, path in files_to_check.items():
        if path.exists():
            if path.is_file():
                size = path.stat().st_size / (1024*1024)  # MB
                print(f"   ✅ {name}: 存在 ({size:.1f}MB)")
            else:
                files = list(path.glob("**/*.c"))[:5]
                print(f"   ✅ {name}: 存在 (含{len(files)}+个.c文件)")
        else:
            print(f"   ❌ {name}: 不存在 - {path}")
            return False
    
    # 检查子系统目录
    print("\n3. 检查子系统结构...")
    
    linux_root = project_root / 'testdata/linux_full/linux-6.6'
    subsystems = ['mm', 'fs', 'net', 'kernel', 'drivers']
    
    for subsys in subsystems:
        subsys_path = linux_root / subsys
        if subsys_path.exists():
            c_files = list(subsys_path.glob("**/*.c"))
            h_files = list(subsys_path.glob("**/*.h"))
            print(f"   ✅ {subsys}: {len(c_files)}个.c文件, {len(h_files)}个.h文件")
        else:
            print(f"   ❌ {subsys}: 目录不存在")
    
    # 检查数据库
    print("\n4. 检查数据库内容...")
    
    try:
        db_path = project_root / 'full6.12.db'
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 查询函数数量
        cursor.execute("SELECT COUNT(*) FROM Functions WHERE is_static = 0")
        func_count = cursor.fetchone()[0]
        print(f"   ✅ 非静态函数: {func_count:,} 个")
        
        # 查询变量数量
        cursor.execute("SELECT COUNT(*) FROM GlobalVariables WHERE is_static = 0")
        var_count = cursor.fetchone()[0]
        print(f"   ✅ 非静态全局变量: {var_count:,} 个")
        
        # 检查子系统数据分布
        print(f"   📊 子系统数据分布:")
        for subsys in ['mm', 'fs', 'net']:
            cursor.execute(f"SELECT COUNT(*) FROM Functions WHERE is_static = 0 AND file_path LIKE '%/{subsys}/%'")
            subsys_func_count = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM GlobalVariables WHERE is_static = 0 AND file_path LIKE '%/{subsys}/%'")
            subsys_var_count = cursor.fetchone()[0]
            print(f"      {subsys}: {subsys_func_count:,}个函数, {subsys_var_count:,}个变量")
        
        # 样例数据
        cursor.execute("SELECT name, file_path FROM Functions WHERE is_static = 0 LIMIT 3")
        samples = cursor.fetchall()
        print(f"   📋 函数样例:")
        for name, path in samples:
            short_path = str(Path(path).name)
            print(f"      - {name} @ {short_path}")
        
        conn.close()
        
    except Exception as e:
        print(f"   ❌ 数据库检查失败: {e}")
        return False
    
    # 测试ctags命令
    print("\n5. 测试ctags基本功能...")
    
    try:
        # 创建临时测试目录
        test_dir = project_root / 'validation/test_temp'
        test_dir.mkdir(exist_ok=True)
        
        # 创建简单的C文件用于测试
        test_c_file = test_dir / 'test.c'
        test_c_file.write_text("""
#include <stdio.h>

int global_var = 42;

void test_function(int param) {
    printf("Hello, world!\\n");
}

int main() {
    test_function(global_var);
    return 0;
}
""")
        
        # 运行ctags
        cmd = ['ctags', '-R', '--c-kinds=+f+v+g', '--fields=+n', 
               '-f', str(test_dir / 'tags'), str(test_dir)]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # 检查输出
            tags_file = test_dir / 'tags'
            if tags_file.exists():
                content = tags_file.read_text()
                lines = [line for line in content.split('\n') if not line.startswith('!')]
                print(f"   ✅ ctags执行成功，生成 {len(lines)} 个符号")
                
                # 显示样例
                for line in lines[:3]:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            print(f"      - {parts[0]}")
            else:
                print(f"   ❌ ctags未生成输出文件")
                return False
        else:
            print(f"   ❌ ctags执行失败: {result.stderr}")
            return False
        
        # 清理测试文件
        import shutil
        shutil.rmtree(test_dir)
        
    except Exception as e:
        print(f"   ❌ ctags测试失败: {e}")
        return False
    
    # 测试compile_commands.json解析 (如果存在)
    print("\n6. 测试编译命令支持...")
    
    compile_commands_files = [
        project_root / 'compile_commands.json',
        project_root / 'testdata/compile_commands.json',
        project_root / 'testdata/linux_full/compile_commands.json'
    ]
    
    found_compile_commands = False
    for cc_file in compile_commands_files:
        if cc_file.exists():
            found_compile_commands = True
            try:
                with open(cc_file, 'r') as f:
                    compile_data = json.load(f)
                
                print(f"   ✅ 找到编译命令文件: {cc_file}")
                print(f"      包含 {len(compile_data)} 个编译条目")
                
                # 检查是否包含子系统相关的编译命令
                mm_files = [cmd for cmd in compile_data 
                           if 'mm/' in cmd.get('file', '')]
                if mm_files:
                    print(f"      包含 {len(mm_files)} 个mm子系统相关文件")
                
                break
                
            except Exception as e:
                print(f"   ❌ 编译命令文件格式错误: {e}")
    
    if not found_compile_commands:
        print(f"   ⚠️ 未找到compile_commands.json文件，编译选项功能不可用")
    
    # 测试子系统验证准备
    print("\n7. 测试子系统验证准备...")
    
    test_subsystem = 'mm'  # 使用mm作为测试子系统
    subsys_path = linux_root / test_subsystem
    
    if subsys_path.exists():
        c_files = list(subsys_path.glob("**/*.c"))
        print(f"   ✅ 子系统 '{test_subsystem}' 准备就绪")
        print(f"      包含 {len(c_files)} 个.c文件")
        
        # 显示几个示例文件
        for c_file in c_files[:3]:
            rel_path = c_file.relative_to(linux_root)
            print(f"      - {rel_path}")
        
        if len(c_files) > 3:
            print(f"      ... 共 {len(c_files)} 个文件")
    else:
        print(f"   ❌ 测试子系统 '{test_subsystem}' 不存在")
    
    print("\n✅ 所有测试通过！")
    print("\n📖 使用说明:")
    print("   基本验证:     ./run_ctags_validation.sh")
    print("   子系统验证:   ./run_ctags_validation.sh --subsystem mm")
    if found_compile_commands:
        cc_path = next(cc for cc in compile_commands_files if cc.exists())
        rel_cc_path = cc_path.relative_to(project_root)
        print(f"   编译选项:     ./run_ctags_validation.sh --compile-commands {rel_cc_path}")
        print(f"   组合使用:     ./run_ctags_validation.sh --subsystem mm --compile-commands {rel_cc_path}")
    print("   查看帮助:     ./run_ctags_validation.sh --help")
    print("   预览模式:     ./run_ctags_validation.sh --subsystem mm --dry-run")
    
    return True

def test_new_features():
    """测试新功能的简单演示"""
    
    print("\n" + "="*50)
    print("🧪 新功能演示测试")
    print("="*50)
    
    project_root = Path(__file__).parent.parent
    
    # 演示预览模式
    print("\n1. 演示预览模式...")
    
    try:
        cmd = [
            str(project_root / 'validation/run_ctags_validation.sh'),
            '--subsystem', 'mm',
            '--dry-run'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, 
                               cwd=str(project_root / 'validation'))
        
        if result.returncode == 0:
            print("   ✅ 预览模式测试成功")
            lines = result.stdout.split('\n')
            # 显示关键输出
            for line in lines:
                if '将要执行的命令' in line or 'python3' in line:
                    print(f"      {line}")
        else:
            print(f"   ❌ 预览模式测试失败: {result.stderr}")
    
    except Exception as e:
        print(f"   ❌ 预览模式测试异常: {e}")
    
    # 检查脚本参数支持
    print("\n2. 检查脚本参数支持...")
    
    try:
        cmd = [
            str(project_root / 'validation/run_ctags_validation.sh'),
            '--help'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True,
                               cwd=str(project_root / 'validation'))
        
        if result.returncode == 0:
            help_text = result.stdout
            
            # 检查新参数是否存在
            new_params = ['--compile-commands', '--subsystem']
            for param in new_params:
                if param in help_text:
                    print(f"   ✅ 参数 {param} 支持正常")
                else:
                    print(f"   ❌ 参数 {param} 不支持")
        else:
            print(f"   ❌ 帮助信息获取失败")
    
    except Exception as e:
        print(f"   ❌ 参数检查异常: {e}")
    
    print("\n✅ 新功能演示完成！")

if __name__ == "__main__":
    success = quick_test()
    
    if success:
        test_new_features()
    
    exit(0 if success else 1) 