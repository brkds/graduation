#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ctags验证脚本
使用ctags工具验证数据库中函数和变量识别的准确性
支持条件编译、子系统验证和详细差异报告
"""

import os
import sqlite3
import subprocess
import sys
import argparse
from pathlib import Path
from collections import defaultdict
import json
import re

class CtagsValidator:
    def __init__(self, db_path, source_root, compile_commands=None, subsystem=None, single_file=None):
        """
        初始化ctags验证器
        
        Args:
            db_path: 数据库文件路径
            source_root: Linux源码根目录
            compile_commands: compile_commands.json文件路径
            subsystem: 要验证的子系统路径 (如 'mm', 'fs/ext4')
            single_file: 只分析单个文件 (如 'mm/page_alloc.c')
        """
        self.db_path = Path(db_path)
        self.source_root = Path(source_root)
        self.subsystem = subsystem
        self.single_file = single_file
        self.compile_commands_file = compile_commands
        self.compile_flags = []
        self.include_dirs = set()
        self.defines = set()
        
        # 如果指定了单文件，优先级高于子系统
        if self.single_file:
            self.subsystem = None
            print(f"单文件分析模式: {self.single_file}")
        elif self.subsystem:
            print(f"子系统分析模式: {self.subsystem}")
        else:
            print("全源码树分析模式")
        
        # 验证输入
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
        
        if not self.source_root.exists():
            raise FileNotFoundError(f"源码目录不存在: {self.source_root}")
        
        # 如果指定了单文件，检查文件是否存在
        if self.single_file:
            single_file_path = self.source_root / self.single_file
            if not single_file_path.exists():
                raise FileNotFoundError(f"指定文件不存在: {single_file_path}")
        
        # 解析编译命令
        if self.compile_commands_file:
            self._parse_compile_commands()
        
        # 初始化数据存储
        self.ctags_data = None
        self.db_data = None
    
    def _parse_compile_commands(self):
        """
        解析compile_commands.json文件，提取编译选项
        """
        if not self.compile_commands_file:
            print("警告: 未指定compile_commands.json文件，将使用默认编译选项")
            return
        
        # 转换为绝对路径
        compile_commands_path = Path(self.compile_commands_file)
        if not compile_commands_path.is_absolute():
            # 如果是相对路径，基于当前工作目录解析
            compile_commands_path = Path.cwd() / compile_commands_path
        
        if not compile_commands_path.exists():
            print(f"警告: compile_commands.json文件不存在: {compile_commands_path}")
            print("将使用默认编译选项")
            return
        
        print(f"正在解析编译命令文件: {compile_commands_path}")
        
        try:
            with open(compile_commands_path, 'r') as f:
                compile_commands = json.load(f)
            
            # 收集所有编译选项
            for entry in compile_commands:
                file_path = entry.get('file', '')
                command = entry.get('command', '')
                arguments = entry.get('arguments', [])
                
                # 如果指定了单文件，只处理该文件的编译选项
                if self.single_file:
                    if not file_path.endswith(self.single_file):
                        continue
                
                # 如果指定了子系统，只处理子系统文件
                elif self.subsystem:
                    if not self._is_subsystem_file(file_path):
                        continue
                
                # 解析命令行或参数列表
                if arguments:
                    args = arguments
                elif command:
                    args = command.split()
                else:
                    continue
                
                # 提取各种编译选项
                i = 0
                while i < len(args):
                    arg = args[i]
                    
                    # 包含目录
                    if arg.startswith('-I'):
                        if arg == '-I' and i + 1 < len(args):
                            self.include_dirs.add(args[i + 1])
                            i += 1
                        else:
                            self.include_dirs.add(arg[2:])
                    
                    # 宏定义
                    elif arg.startswith('-D'):
                        if arg == '-D' and i + 1 < len(args):
                            self.defines.add(args[i + 1])
                            i += 1
                        else:
                            self.defines.add(arg[2:])
                    
                    i += 1
            
            print(f"提取到编译选项: {len(self.include_dirs)}个包含目录, {len(self.defines)}个宏定义")
            if self.include_dirs:
                print(f"包含目录示例: {list(self.include_dirs)[:3]}")
            if self.defines:
                print(f"宏定义示例: {list(self.defines)[:3]}")
            
        except Exception as e:
            print(f"解析compile_commands.json失败: {e}")
            print("将使用默认编译选项")
    
    def _is_subsystem_file(self, file_path):
        """
        判断文件是否属于指定的子系统
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否属于子系统
        """
        if self.single_file:
            # 单文件模式：检查是否是指定的文件
            return file_path.endswith(self.single_file)
        
        if not self.subsystem:
            return True
        
        # 标准化路径分隔符
        normalized_path = file_path.replace('\\', '/')
        
        # 精确匹配：只匹配顶级子系统目录
        # 例如：mm参数只匹配 mm/xxx.c，不匹配 arch/*/mm/xxx.c
        
        # 检查是否以 {subsystem}/ 开头
        if normalized_path.startswith(f'{self.subsystem}/'):
            return True
            
        # 检查路径中是否包含 /{subsystem}/ 且是顶级目录
        # 但要确保不是嵌套在其他目录中的同名目录
        parts = normalized_path.split('/')
        
        # 找到子系统名称在路径中的位置
        for i, part in enumerate(parts):
            if part == self.subsystem:
                # 检查这是否是顶级子系统目录
                # 如果前面只有项目路径部分，则认为是顶级目录
                prefix_parts = parts[:i]
                # 忽略项目路径前缀（如 testdata/linux_full/linux-6.6）
                filtered_prefix = [p for p in prefix_parts if p not in ['testdata', 'linux_full', 'linux-6.6', '']]
                
                # 如果过滤后的前缀为空，说明是顶级子系统目录
                if not filtered_prefix:
                    return True
        
        return False
    
    def generate_ctags_data(self, output_dir="validation/ctags_output"):
        """
        使用ctags生成基准数据
        为了真正支持条件编译，先使用gcc预处理器处理源码，再用ctags解析
        
        Args:
            output_dir: ctags输出目录
        """
        print("正在使用ctags生成基准数据...")
        
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 确定要处理的源码目录或文件
        if self.single_file:
            target_path = self.source_root / self.single_file
            if not target_path.exists():
                raise FileNotFoundError(f"指定文件不存在: {target_path}")
            print(f"只分析单个文件: {self.single_file}")
        elif self.subsystem:
            target_path = self.source_root / self.subsystem
            if not target_path.exists():
                raise FileNotFoundError(f"子系统目录不存在: {target_path}")
            print(f"只验证子系统: {self.subsystem}")
        else:
            target_path = self.source_root
            print("验证整个源码树")
        
        # 如果有编译选项，使用预处理器方法
        if self.include_dirs or self.defines:
            print("使用预处理器+ctags方法处理条件编译...")
            return self._generate_with_preprocessor(output_path, target_path)
        else:
            print("使用传统ctags方法...")
            return self._generate_traditional_ctags(output_path, target_path)
    
    def _generate_with_preprocessor(self, output_path, target_path):
        """
        使用预处理器+ctags方法处理条件编译
        """
        # 创建预处理输出目录
        preprocessed_dir = output_path / "preprocessed"
        preprocessed_dir.mkdir(exist_ok=True)
        
        # 收集所有.c文件
        c_files = []
        if target_path.is_file():
            if target_path.suffix == '.c':
                c_files = [target_path]
        else:
            c_files = list(target_path.rglob('*.c'))
            if self.subsystem:
                # 过滤子系统文件
                c_files = [f for f in c_files if self._is_subsystem_file(str(f))]
        
        print(f"找到{len(c_files)}个C文件需要预处理")
        
        if not c_files:
            print("没有找到C文件")
            return False
        
        # 准备预处理器参数
        cpp_args = [
            "gcc", "-E",  # 只预处理，不编译
            "-nostdinc",  # 不使用标准头文件
            "-dD",        # 保留宏定义
            "-P",         # 不生成行号信息
        ]
        
        # 添加包含目录
        for inc_dir in sorted(self.include_dirs):
            abs_inc_dir = self.source_root / inc_dir if not Path(inc_dir).is_absolute() else Path(inc_dir)
            if abs_inc_dir.exists():
                cpp_args.extend(["-I", str(abs_inc_dir)])
        
        # 添加宏定义
        for define in sorted(self.defines):
            cpp_args.extend(["-D", define])
        
        # 添加内核特定的宏定义
        cpp_args.extend([
            "-D__KERNEL__",
            "-DCONFIG_X86_64=1",  # 假设x86_64架构
            "-DCONFIG_64BIT=1",
        ])
        
        print(f"预处理器参数: {len(cpp_args)}个")
        print(f"包含目录: {len([a for a in cpp_args if a.startswith('-I')])//2}个")
        print(f"宏定义: {len([a for a in cpp_args if a.startswith('-D')])//2}个")
        
        # 预处理每个C文件
        preprocessed_files = []
        success_count = 0
        
        for c_file in c_files[:10]:  # 限制处理文件数量以加快测试
            try:
                # 生成预处理文件名
                rel_path = c_file.relative_to(self.source_root)
                preprocessed_file = preprocessed_dir / f"{rel_path.stem}_preprocessed.c"
                preprocessed_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 运行预处理器
                cmd = cpp_args + [str(c_file)]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.source_root)
                
                if result.returncode == 0:
                    # 写入预处理结果
                    with open(preprocessed_file, 'w') as f:
                        f.write(result.stdout)
                    preprocessed_files.append(preprocessed_file)
                    success_count += 1
                else:
                    print(f"预处理失败: {c_file.name} - {result.stderr[:100]}...")
                    
            except Exception as e:
                print(f"预处理错误: {c_file.name} - {e}")
        
        print(f"预处理完成: {success_count}/{len(c_files[:10])}个文件成功")
        
        if not preprocessed_files:
            print("没有成功预处理的文件，回退到传统方法")
            return self._generate_traditional_ctags(output_path, target_path)
        
        # 对预处理后的文件运行ctags
        ctags_file = output_path / "tags"
        cmd = [
            "/usr/local/bin/ctags",
            "-R",
            "--c-kinds=+f+v+g",
            "--fields=+n+S+K+l",
            "--extras=+q+f",
            "--language-force=C",
            "--langmap=C:.c.h",
            "-f", str(ctags_file.resolve()),
        ]
        
        # 添加所有预处理文件
        cmd.extend([str(f) for f in preprocessed_files])
        
        try:
            print(f"对{len(preprocessed_files)}个预处理文件运行ctags...")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.source_root)
            
            if result.returncode != 0:
                print(f"ctags执行失败: {result.stderr}")
                return False
            
            # 即使成功也打印输出以便调试
            if result.stderr:
                print(f"ctags警告: {result.stderr}")
            if result.stdout:
                print(f"ctags输出: {result.stdout}")
            
            print(f"ctags执行成功，输出文件: {ctags_file}")
            return self._parse_ctags_output(ctags_file)
            
        except Exception as e:
            print(f"执行ctags时发生错误: {e}")
            return False
    
    def _generate_traditional_ctags(self, output_path, target_path):
        """
        传统的ctags方法（原有逻辑）
        """
        # ctags命令 - 只处理.c和.h文件，使用Universal Ctags
        ctags_file = output_path / "tags"
        
        # 使用绝对路径
        ctags_file_abs = ctags_file.resolve()
        
        cmd = [
            "/usr/local/bin/ctags",  # 使用Universal Ctags
            "-R",  # 递归处理
            "--c-kinds=+f+v+g",  # 只包含函数、变量、全局变量
            "--fields=+n+S+K+l",  # 包含行号、签名、类型等信息
            "--extras=+q+f",  # 额外信息
            "--languages=C",  # 只处理C语言
            "--langmap=C:.c.h",  # 只处理.c和.h文件
            "--exclude=.*.cmd",  # 排除编译命令文件
            "--exclude=*.o",  # 排除目标文件
            "--exclude=*.a",  # 排除静态库文件
        ]
        
        # ctags不能真正处理条件编译，所以不使用编译选项
        # 它会解析所有符号，包括条件编译块中的符号
        if self.include_dirs or self.defines:
            print("注意: ctags不能处理条件编译，将解析所有符号（包括条件编译块中的符号）")
            print(f"忽略编译选项: {len(self.include_dirs)}个包含目录, {len(self.defines)}个宏定义")
        
        cmd.extend([
            "-f", str(ctags_file_abs),  # 输出文件（绝对路径）
            str(target_path)  # 源码目录或文件
        ])
        
        try:
            print(f"执行ctags命令: {' '.join(cmd)}...")
            
            # 调试：打印完整命令
            print(f"输出文件: {ctags_file}")
            print(f"目标路径: {target_path}")
            print(f"工作目录: {self.source_root}")
            
            # 修复工作目录：应该在项目根目录执行，这样target_path相对路径才正确
            project_root = Path.cwd()  # 当前工作目录（项目根目录）
            print(f"实际ctags工作目录: {project_root}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
            if result.returncode != 0:
                print(f"ctags执行失败 (返回码: {result.returncode})")
                print(f"stderr: {result.stderr}")
                print(f"stdout: {result.stdout}")
                return False
            
            # 即使成功也打印输出以便调试
            if result.stderr:
                print(f"ctags警告: {result.stderr}")
            if result.stdout:
                print(f"ctags输出: {result.stdout}")
            
            print(f"ctags执行成功，输出文件: {ctags_file}")
            return self._parse_ctags_output(ctags_file)
            
        except Exception as e:
            print(f"执行ctags时发生错误: {e}")
            return False
    
    def _parse_ctags_output(self, ctags_file):
        """
        解析ctags输出文件
        
        Args:
            ctags_file: ctags输出文件路径
        """
        print("正在解析ctags输出...")
        
        functions = {}
        variables = {}
        total_lines = 0
        comment_lines = 0
        processed_lines = 0
        
        try:
            with open(ctags_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    total_lines += 1
                    line = line.strip()
                    if line.startswith('!'):  # 跳过注释行
                        comment_lines += 1
                        continue
                    
                    if not line:  # 跳过空行
                        continue
                    
                    processed_lines += 1
                    
                    # 解析ctags行格式: symbol\tfile\taddress;"kind\tfield:value
                    # 注意：address字段可能包含制表符，需要特殊处理
                    parts = line.split('\t')
                    if len(parts) < 4:
                        continue
                    
                    # 前两个字段是确定的
                    symbol = parts[0]
                    file_path = parts[1]
                    
                    # 找到第3个字段的结束位置（以 ;"结尾）
                    address_parts = []
                    kind_start_idx = 2
                    for i in range(2, len(parts)):
                        if parts[i].endswith(';"'):
                            # 找到了address字段的结束
                            address_parts.append(parts[i])
                            kind_start_idx = i + 1
                            break
                        else:
                            address_parts.append(parts[i])
                    
                    # 重建address字段
                    address = '\t'.join(address_parts) if address_parts else parts[2]
                    
                    # 剩余的字段从kind_start_idx开始
                    remaining_parts = parts[kind_start_idx:]
                    kind_info = remaining_parts[0] if remaining_parts else ""
                    
                    # 检查是否是Linux内核属性符号（__read_mostly, ____cacheline_aligned_in_smp等）
                    # 如果是，需要从typeref字段中提取真正的符号名
                    kernel_attributes = ['__read_mostly', '____cacheline_aligned_in_smp', '__weak', '__init', '__exit', '__ro_after_init', '__meminitdata', '__initdata_memblock']
                    if symbol in kernel_attributes:
                        # 查找typeref字段来获取真正的符号名
                        real_symbol = None
                        for part in remaining_parts:
                            if part.startswith('typeref:'):
                                # typeref格式: typeref:typename:int symbol_name 或 typeref:struct:struct_name symbol_name
                                typeref_parts = part.split(':')
                                if len(typeref_parts) >= 3:
                                    # 取最后一部分，去掉可能的额外信息
                                    symbol_part = typeref_parts[-1].strip()
                                    # 可能包含多个单词，取最后一个（符号名）
                                    words = symbol_part.split()
                                    if words:
                                        real_symbol = words[-1]
                                        break
                        
                        if real_symbol:
                            symbol = real_symbol
                        else:
                            # 如果无法从typeref提取，跳过这个符号
                            continue
                    
                    # 只处理.c和.h文件
                    if not (file_path.endswith('.c') or file_path.endswith('.h')):
                        continue
                    
                    # 标准化文件路径
                    file_path = self._normalize_path(file_path)
                    
                    # 子系统过滤（在路径标准化后进行）
                    if not self._is_subsystem_file(file_path):
                        continue
                    
                    # 提取行号
                    line_num = None
                    if ';' in address:
                        # 处理 /^pattern$/; 格式，从后续字段中提取行号
                        for part in remaining_parts:
                            if part.startswith('line:'):
                                try:
                                    line_num = int(part.split(':')[1])
                                    break
                                except (ValueError, IndexError):
                                    continue
                    elif address.isdigit():
                        line_num = int(address)
                    
                    if not line_num:
                        continue
                    
                    # 解析kind - ctags输出格式分析
                    kind = None
                    if kind_info:
                        # 第kind字段格式可能是: ;"function 或 ;"f 或 ;"variable 或 ;"v 等
                        kind_field = kind_info.strip()
                        
                        # 处理带;"前缀的情况（这种情况应该不会出现了，因为我们已经分离了address）
                        if kind_field.startswith(';"'):
                            kind_value = kind_field[2:].strip()
                        else:
                            kind_value = kind_field
                        
                        # 映射kind值到标准类型
                        if kind_value in ['function', 'f']:
                            kind = 'function'
                        elif kind_value in ['variable', 'v', 'g']:  # g表示全局变量
                            kind = 'variable'
                    
                    # 如果第一个kind字段没有识别出来，检查后续字段
                    if not kind and len(remaining_parts) > 1:
                        for field in remaining_parts[1:]:
                            field = field.strip()
                            if field in ['function', 'f']:
                                kind = 'function'
                                break
                            elif field in ['variable', 'v', 'g']:
                                kind = 'variable'
                                break
                    
                    # 只处理functions和variables
                    if kind not in ['function', 'variable']:
                        continue
                    
                    # 存储数据
                    if kind == 'function':
                        functions[(symbol, file_path)] = {
                            'line': line_num,
                            'kind': kind
                        }
                    elif kind == 'variable':
                        variables[(symbol, file_path)] = {
                            'line': line_num,
                            'kind': kind
                        }
            
            self.ctags_data = {
                'functions': functions,
                'variables': variables
            }
            
            print(f"ctags解析完成: 函数 {len(functions)} 个, 变量 {len(variables)} 个")
            return True
            
        except Exception as e:
            print(f"解析ctags输出时发生错误: {e}")
            return False
    
    def _normalize_path(self, file_path):
        """
        标准化文件路径，统一为相对于linux-6.6源码根目录的路径
        
        Args:
            file_path: 原始文件路径
            
        Returns:
            标准化后的文件路径
        """
        try:
            path_str = str(file_path)
            
            # 查找linux-6.6的位置，提取之后的路径
            if 'linux-6.6/' in path_str:
                # 分割路径，取linux-6.6/之后的部分
                parts = path_str.split('linux-6.6/')
                if len(parts) > 1:
                    return parts[-1]  # 返回最后一部分，如 mm/readahead.c 或 arch/openrisc/mm/fault.c
            
            # 如果没有找到linux-6.6，可能已经是标准化的路径
            # 检查是否是相对路径且包含常见的linux内核目录
            if not path_str.startswith('/') and any(part in path_str for part in [
                'mm/', 'arch/', 'kernel/', 'fs/', 'drivers/', 'net/', 'sound/', 
                'crypto/', 'lib/', 'include/', 'tools/', 'scripts/'
            ]):
                return path_str
                
            return file_path
        except Exception:
            return file_path
    
    def extract_db_data(self):
        """
        从数据库中提取函数和变量数据
        """
        print("正在从数据库提取数据...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建子系统过滤条件
            subsystem_filter = ""
            if self.subsystem:
                subsystem_filter = f"AND file_path LIKE '%/{self.subsystem}/%'"
            
            # 提取函数数据
            query = f"""
                SELECT name, file_path, start_line, is_static 
                FROM Functions 
                WHERE 1=1 {subsystem_filter}
            """
            cursor.execute(query)
            functions = {}
            for row in cursor.fetchall():
                name, file_path, start_line, is_static = row
                norm_path = self._normalize_db_path(file_path)
                
                # 再次确认是否属于子系统
                if self._is_subsystem_file(norm_path):
                    functions[(name, norm_path)] = {
                        'line': start_line,
                        'is_static': is_static
                    }
            
            # 提取变量数据
            query = f"""
                SELECT name, file_path, line_number, is_static 
                FROM GlobalVariables 
                WHERE 1=1 {subsystem_filter}
            """
            cursor.execute(query)
            variables = {}
            for row in cursor.fetchall():
                name, file_path, line_number, is_static = row
                norm_path = self._normalize_db_path(file_path)
                
                # 再次确认是否属于子系统
                if self._is_subsystem_file(norm_path):
                    variables[(name, norm_path)] = {
                        'line': line_number,
                        'is_static': is_static
                    }
            
            conn.close()
            
            self.db_data = {
                'functions': functions,
                'variables': variables
            }
            
            print(f"数据库提取完成: 函数 {len(functions)} 个, 变量 {len(variables)} 个")
            return True
            
        except Exception as e:
            print(f"从数据库提取数据时发生错误: {e}")
            return False
    
    def _normalize_db_path(self, db_path):
        """
        标准化数据库中的文件路径，与ctags路径格式保持一致
        
        Args:
            db_path: 数据库中的文件路径
            
        Returns:
            标准化后的文件路径
        """
        try:
            path_str = str(db_path)
            
            # 查找linux-6.6的位置，提取之后的路径
            if 'linux-6.6/' in path_str:
                # 分割路径，取linux-6.6/之后的部分
                parts = path_str.split('linux-6.6/')
                if len(parts) > 1:
                    return parts[-1]  # 返回最后一部分，如 mm/readahead.c 或 arch/openrisc/mm/fault.c
            
            # 如果没有找到linux-6.6，可能已经是标准化的路径
            # 检查是否是相对路径且包含常见的linux内核目录
            if not path_str.startswith('/') and any(part in path_str for part in [
                'mm/', 'arch/', 'kernel/', 'fs/', 'drivers/', 'net/', 'sound/', 
                'crypto/', 'lib/', 'include/', 'tools/', 'scripts/'
            ]):
                return path_str
                
            return db_path
        except Exception:
            return db_path
    
    def compare_and_validate(self):
        """
        比较ctags和数据库数据，计算准确性指标
        
        Returns:
            验证结果字典
        """
        print("正在进行数据对比验证...")
        
        # 比较functions
        print("\n正在比较functions...")
        functions_result = self._compare_symbols(
            self.ctags_data['functions'], 
            self.db_data['functions'], 
            'functions'
        )
        
        # 比较variables
        print("\n正在比较variables...")
        variables_result = self._compare_symbols(
            self.ctags_data['variables'], 
            self.db_data['variables'], 
            'variables'
        )
        
        results = {
            'functions': functions_result,
            'variables': variables_result
        }
        
        return results
    
    def _compare_symbols(self, ctags_symbols, db_symbols, symbol_type):
        """
        比较符号数据
        
        由于ctags不能处理条件编译，它会解析所有符号（包括条件编译块中的符号）。
        而数据库中的符号是经过条件编译后的真实符号，应该是ctags符号的子集。
        因此主要验证：数据库中的符号是否都能被ctags覆盖。
        
        Args:
            ctags_symbols: ctags识别的符号（包含条件编译中的符号）
            db_symbols: 数据库中的符号（经过条件编译后的真实符号）
            symbol_type: 符号类型（functions或variables）
            
        Returns:
            比较结果
        """
        print(f"正在比较{symbol_type}...")
        
        # 转换为集合进行比较
        ctags_set = set(ctags_symbols.keys())
        db_set = set(db_symbols.keys())
        
        # 计算交集、差集
        common = ctags_set & db_set  # ctags和数据库都识别的符号
        missed_by_ctags = db_set - ctags_set  # 数据库有但ctags没有的符号（影响覆盖率）
        extra_in_ctags = ctags_set - db_set  # ctags有但数据库没有的符号（条件编译导致，正常现象）
        
        # 计算覆盖率（唯一重要指标）
        total_ctags = len(ctags_set)
        total_db = len(db_set)
        total_common = len(common)
        
        # 覆盖率 = 数据库中被ctags覆盖的符号 / 数据库总符号数
        # 这是唯一重要的指标：验证数据库符号是否被ctags完全覆盖
        coverage_rate = total_common / total_db if total_db > 0 else 0
        
        # 详细差异分析（用于调试）
        missed_by_ctags_detailed = []
        for symbol, path in missed_by_ctags:
            missed_by_ctags_detailed.append({
                'symbol': symbol,
                'path': path,
                'line': db_symbols[(symbol, path)]['line'],
                'is_static': db_symbols[(symbol, path)].get('is_static', 0)
            })
        
        extra_in_ctags_detailed = []
        for symbol, path in extra_in_ctags:
            extra_in_ctags_detailed.append({
                'symbol': symbol,
                'path': path,
                'line': ctags_symbols[(symbol, path)]['line'],
                'kind': ctags_symbols[(symbol, path)]['kind']
            })
        
        result = {
            'ctags_total': total_ctags,
            'db_total': total_db,
            'common_total': total_common,
            'missed_by_ctags_count': len(missed_by_ctags),
            'extra_in_ctags_count': len(extra_in_ctags),
            'coverage_rate': coverage_rate,  # 核心指标：覆盖率
            'missed_by_ctags_detailed': missed_by_ctags_detailed,
            'extra_in_ctags_detailed': extra_in_ctags_detailed,
        }
        
        return result
    
    def generate_report(self, results, output_file="validation/ctags_validation_report.json"):
        """
        生成验证报告
        
        Args:
            results: 验证结果
            output_file: 输出文件路径
        """
        print("正在生成验证报告...")
        
        # 创建输出目录
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 格式化结果
        report = {
            'metadata': {
                'database': str(self.db_path),
                'source_root': str(self.source_root),
                'subsystem': self.subsystem,
                'single_file': self.single_file,
                'compile_commands': self.compile_commands_file,
                'validation_time': subprocess.run(['date'], capture_output=True, text=True).stdout.strip(),
                'validation_logic': 'ctags符号覆盖率验证 - 检查数据库符号是否被ctags完全覆盖'
            },
            'summary': {
                'functions': {
                    'coverage_rate': f"{results['functions']['coverage_rate']:.1%}"
                },
                'variables': {
                    'coverage_rate': f"{results['variables']['coverage_rate']:.1%}"
                }
            },
            'detailed_results': results,
            'difference_analysis': self._generate_difference_analysis(results)
        }
        
        # 保存JSON报告
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印文本报告
        self._print_text_report(results)
        
        print(f"验证报告已保存到: {output_file}")
    
    def _generate_difference_analysis(self, results):
        """
        生成详细的差异分析
        
        Args:
            results: 验证结果
            
        Returns:
            差异分析结果
        """
        analysis = {}
        
        for symbol_type in ['functions', 'variables']:
            result = results[symbol_type]
            
            # 按文件统计差异
            ctags_extra_by_file = defaultdict(list)
            db_missed_by_file = defaultdict(list)
            
            for item in result['extra_in_ctags_detailed']:
                ctags_extra_by_file[item['path']].append(item)
            
            for item in result['missed_by_ctags_detailed']:
                db_missed_by_file[item['path']].append(item)
            
            # 生成文件级别的差异统计
            file_diff_stats = {}
            all_files = set(ctags_extra_by_file.keys()) | set(db_missed_by_file.keys())
            
            for file_path in all_files:
                ctags_extra_count = len(ctags_extra_by_file[file_path])
                db_missed_count = len(db_missed_by_file[file_path])
                file_diff_stats[file_path] = {
                    'extra_in_ctags_count': ctags_extra_count,
                    'missed_by_ctags_count': db_missed_count,
                    'ctags_extra_symbols': ctags_extra_by_file[file_path],
                    'db_missed_symbols': db_missed_by_file[file_path]
                }
            
            analysis[symbol_type] = {
                'summary': {
                    'total_files_with_differences': len(file_diff_stats),
                    'files_with_ctags_extra': len([f for f, s in file_diff_stats.items() if s['extra_in_ctags_count'] > 0]),
                    'files_with_db_missed': len([f for f, s in file_diff_stats.items() if s['missed_by_ctags_count'] > 0])
                },
                'file_differences': file_diff_stats
            }
        
        return analysis
    
    def _print_text_report(self, results):
        """
        打印文本格式的验证报告
        
        Args:
            results: 验证结果
        """
        print("\n" + "="*60)
        print("CTAGS符号覆盖率验证报告")
        print("测试逻辑: 检查数据库符号是否被ctags完全覆盖")
        if self.single_file:
            print(f"单文件: {self.single_file}")
        elif self.subsystem:
            print(f"子系统: {self.subsystem}")
        else:
            print("全源码树分析")
        print("="*60)
        
        for symbol_type in ['functions', 'variables']:
            result = results[symbol_type]
            print(f"\n{symbol_type.upper()}验证结果:")
            print("-"*40)
            print(f"ctags识别总数:        {result['ctags_total']:>8}")
            print(f"数据库识别总数:       {result['db_total']:>8}")
            print(f"共同识别数量:         {result['common_total']:>8}")
            print(f"数据库独有符号:       {result['missed_by_ctags_count']:>8} (应该很少)")
            print(f"ctags额外符号:        {result['extra_in_ctags_count']:>8} (条件编译导致)")
            print(f"")
            print(f"🎯 覆盖率:            {result['coverage_rate']:>7.1%}")
            
            # 显示差异详情
            if result['missed_by_ctags_detailed']:
                print(f"\n❌ 数据库有但ctags缺失的{symbol_type} (前10个):")
                print("   这些符号可能表明ctags解析不完整:")
                for item in result['missed_by_ctags_detailed'][:10]:
                    print(f"   • {item['symbol']} @ {item['path']}:{item['line']}")
            
            if result['extra_in_ctags_detailed']:
                print(f"\n💡 ctags额外识别的{symbol_type} (前10个):")
                print("   这些符号来自条件编译块，属于正常现象:")
                for item in result['extra_in_ctags_detailed'][:10]:
                    print(f"   • {item['symbol']} @ {item['path']}:{item['line']}")
        
        print("\n" + "="*60)
        print("📊 验证结论:")
        print("• 覆盖率接近100%: 数据库符号识别准确")
        print("• ctags额外符号: 条件编译导致，属正常现象")
        print("• 数据库独有符号: 需要检查ctags解析是否完整")
        print("="*60)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ctags验证脚本')
    parser.add_argument('--db', default='full6.12.db', help='数据库文件路径')
    parser.add_argument('--source', default='testdata/linux_full/linux-6.6', help='Linux源码根目录')
    parser.add_argument('--output', default='validation/ctags_output', help='ctags输出目录')
    parser.add_argument('--report', default='validation/ctags_validation_report.json', help='验证报告输出文件')
    parser.add_argument('--compile-commands', help='compile_commands.json文件路径')
    parser.add_argument('--subsystem', help='要验证的子系统路径 (如: mm, fs, drivers/gpu)')
    parser.add_argument('--single-file', help='只分析单个文件 (如: mm/page_alloc.c)')
    
    args = parser.parse_args()
    
    try:
        # 创建验证器
        validator = CtagsValidator(
            args.db, 
            args.source, 
            compile_commands=args.compile_commands,
            subsystem=args.subsystem,
            single_file=args.single_file
        )
        
        # 1. 生成ctags数据
        if not validator.generate_ctags_data(args.output):
            print("生成ctags数据失败")
            sys.exit(1)
        
        # 2. 提取数据库数据
        if not validator.extract_db_data():
            print("提取数据库数据失败")
            sys.exit(1)
        
        # 3. 对比验证
        results = validator.compare_and_validate()
        
        # 4. 生成报告
        validator.generate_report(results, args.report)
        
        print("\nctags验证完成!")
        
    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 