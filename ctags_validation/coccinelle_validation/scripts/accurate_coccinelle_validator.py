#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确的Coccinelle访问关系验证器
只检测函数对变量的访问关系，且要求函数和变量都在数据库中存在
"""

import os
import sqlite3
import subprocess
import sys
import argparse
from pathlib import Path
from collections import defaultdict
import json
import time
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import math

class AccurateCoccinelleValidator:
    def __init__(self, db_path, source_root, subsystem=None, target_file=None):
        """
        初始化精确的Coccinelle访问关系验证器
        
        Args:
            db_path: 数据库文件路径
            source_root: Linux源码根目录
            subsystem: 要验证的子系统 (如 'mm')
            target_file: 指定验证单个文件 (如 'mm/backing-dev.c')
        """
        self.db_path = Path(db_path)
        self.source_root = Path(source_root)
        self.subsystem = subsystem
        self.target_file = target_file
        
        # 验证输入
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
        
        if not self.source_root.exists():
            raise FileNotFoundError(f"源码目录不存在: {self.source_root}")
        
        # 检查Coccinelle是否可用
        self.coccinelle_available = self._check_coccinelle()
        
        # 数据存储
        self.db_functions = set()  # 数据库中的函数
        self.db_variables = set()  # 数据库中的变量
        self.db_access_relations = {}  # 数据库中的访问关系
        self.coccinelle_detections = {}  # Coccinelle检测结果（过滤后）
        self.validation_results = {}  # 验证结果
        
        # 新增：处理统计
        self.processing_stats = {
            'processed_files': 0,
            'error_files': 0,
            'interrupted_files': 0,
            'total_files': 0
        }
        
        print(f"精确的Coccinelle访问关系验证器初始化完成")
        if target_file:
            print(f"验证目标文件: {target_file}")
        elif subsystem:
            print(f"验证目标子系统: {subsystem}")
        else:
            print("验证目标: 全部")
    
    def _check_coccinelle(self):
        """检查Coccinelle工具是否可用"""
        try:
            result = subprocess.run(['spatch', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _build_path_filter(self):
        """构建路径过滤条件"""
        if self.target_file:
            return f"AND file_path LIKE '%{self.target_file}'"
        elif self.subsystem:
            return f"AND file_path LIKE '%linux-6.6/{self.subsystem}/%'"
        else:
            return "AND file_path LIKE '%linux-6.6/%'"
    
    def extract_database_entities(self):
        """从数据库提取函数和变量实体"""
        print("正在从数据库提取函数和变量实体...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建路径过滤条件
            path_filter = self._build_path_filter()
            
            # 提取目标范围内的函数
            func_query = f"""
                SELECT DISTINCT name, file_path
                FROM Functions 
                WHERE 1=1 {path_filter}
            """
            cursor.execute(func_query)
            functions_data = cursor.fetchall()
            for name, file_path in functions_data:
                self.db_functions.add(name)
            
            # 提取目标范围内的变量
            var_query = f"""
                SELECT DISTINCT name, file_path
                FROM GlobalVariables 
                WHERE 1=1 {path_filter}
            """
            cursor.execute(var_query)
            variables_data = cursor.fetchall()
            for name, file_path in variables_data:
                self.db_variables.add(name)
            
            conn.close()
            
            print(f"数据库实体提取完成:")
            print(f"  函数: {len(self.db_functions)} 个")
            print(f"  变量: {len(self.db_variables)} 个")
            
            return True
            
        except Exception as e:
            print(f"从数据库提取实体时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def extract_database_access_relations(self):
        """从数据库提取访问关系作为基准"""
        print("正在从数据库提取访问关系...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建路径过滤条件
            if self.target_file:
                path_filter = f"AND ar.access_file_path LIKE '%{self.target_file}'"
            elif self.subsystem:
                path_filter = f"AND ar.access_file_path LIKE '%linux-6.6/{self.subsystem}/%'"
            else:
                path_filter = "AND ar.access_file_path LIKE '%linux-6.6/%'"
            
            # 提取访问关系
            query = f"""
                SELECT ar.access_type, ar.access_file_path, ar.access_line_number,
                       gv.name as var_name, f.name as func_name
                FROM AccessRelations ar 
                JOIN GlobalVariables gv ON ar.variable_id = gv.id 
                JOIN Functions f ON ar.function_id = f.id 
                WHERE 1=1 {path_filter}
                ORDER BY ar.access_file_path, ar.access_line_number
            """
            
            cursor.execute(query)
            access_data = cursor.fetchall()
            
            # 组织数据：按文件分组
            file_access_map = defaultdict(list)
            
            for row in access_data:
                access_type, file_path, line_num, var_name, func_name = row
                
                # 标准化文件路径
                normalized_path = self._normalize_path(file_path)
                
                access_record = {
                    'function': func_name,
                    'variable': var_name,
                    'access_type': access_type,
                    'line': line_num
                }
                
                file_access_map[normalized_path].append(access_record)
            
            conn.close()
            
            self.db_access_relations = dict(file_access_map)
            
            total_accesses = sum(len(accesses) for accesses in self.db_access_relations.values())
            print(f"数据库访问关系提取完成:")
            print(f"  涉及文件: {len(self.db_access_relations)} 个")
            print(f"  总访问关系: {total_accesses} 个")
            
            # 统计访问类型
            type_counts = defaultdict(int)
            for accesses in self.db_access_relations.values():
                for access in accesses:
                    type_counts[access['access_type']] += 1
            
            for access_type, count in type_counts.items():
                print(f"    {access_type}: {count} 个")
            
            return True
            
        except Exception as e:
            print(f"从数据库提取访问关系时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _normalize_path(self, db_path):
        """标准化数据库路径"""
        path_str = str(db_path)
        if 'linux-6.6/' in path_str:
            parts = path_str.split('linux-6.6/')
            if len(parts) > 1:
                return parts[-1]
        return db_path
    
    def create_selective_coccinelle_rules(self, rules_dir="selective_validation_rules"):
        """创建选择性验证规则，为每个文件只检测数据库中记录的具体函数-变量对"""
        rules_path = Path(rules_dir)
        rules_path.mkdir(exist_ok=True)
        
        print(f"正在创建选择性验证规则...")
        
        # 按文件分组数据库访问关系
        file_access_groups = {}
        for file_path, accesses in self.db_access_relations.items():
            read_pairs = set()
            write_pairs = set()
            
            for access in accesses:
                func = access['function']
                var = access['variable']
                access_type = access['access_type']
                
                if access_type == 'read':
                    read_pairs.add((func, var))
                elif access_type == 'write':
                    write_pairs.add((func, var))
            
            file_access_groups[file_path] = {
                'read_pairs': read_pairs,
                'write_pairs': write_pairs
            }
        
        print(f"为 {len(file_access_groups)} 个文件生成专门的验证规则")
        
        # 生成通用的选择性规则模板
        self._create_selective_rule_templates(rules_path, file_access_groups)
        
        return rules_path
    
    def _create_selective_rule_templates(self, rules_path, file_access_groups):
        """创建选择性验证的规则模板"""
        
        # 创建文件特定的访问对列表
        file_targets_path = rules_path / "file_targets.py"
        with open(file_targets_path, 'w') as f:
            f.write("# 每个文件的目标函数-变量对\n")
            f.write("FILE_TARGETS = {\n")
            
            for file_path, targets in file_access_groups.items():
                # 标准化文件路径用作Python key
                normalized_file = file_path.replace('/', '_').replace('.', '_').replace('-', '_')
                f.write(f"    '{file_path}': {{\n")
                f.write(f"        'read_pairs': {list(targets['read_pairs'])},\n")
                f.write(f"        'write_pairs': {list(targets['write_pairs'])}\n")
                f.write(f"    }},\n")
            
            f.write("}\n")
        
        # 创建选择性读访问规则
        read_rule = '''// 选择性检测函数对变量的读访问
@initialize:python@
@@

import os
import sys

# 导入目标文件配置
rule_dir = "selective_validation_rules"
sys.path.insert(0, rule_dir)
try:
    from file_targets import FILE_TARGETS
    print(f"加载了 {len(FILE_TARGETS)} 个文件的目标配置")
except:
    FILE_TARGETS = {}
    print("无法加载文件目标配置")

current_file = ""
target_read_pairs = set()

@variable_read@
identifier func;
identifier var;
position p;
@@

func(...) {
    <...
    var@p
    ...>
}

@script:python@
func << variable_read.func;
var << variable_read.var;
p << variable_read.p;
@@

# 获取当前文件路径
file_path = p[0].file
if file_path != current_file:
    current_file = file_path
    # 查找匹配的配置
    target_read_pairs = set()
    for target_file, config in FILE_TARGETS.items():
        if file_path.endswith(target_file):
            target_read_pairs = set(config.get('read_pairs', []))
            break

# 只输出目标函数-变量对
if (func, var) in target_read_pairs:
    print("READ|%s|%s|%s|%s" % (func, var, p[0].file, p[0].line))
'''
        
        # 创建选择性写访问规则
        write_rule = '''// 选择性检测函数对变量的写访问
@initialize:python@
@@

import os
import sys

# 导入目标文件配置
rule_dir = "selective_validation_rules"
sys.path.insert(0, rule_dir)
try:
    from file_targets import FILE_TARGETS
except:
    FILE_TARGETS = {}

current_file = ""
target_write_pairs = set()

@variable_write@
identifier func;
identifier var;
expression E;
position p;
@@

func(...) {
    <...
    var@p = E
    ...>
}

@script:python@
func << variable_write.func;
var << variable_write.var;
p << variable_write.p;
@@

# 获取当前文件路径
file_path = p[0].file
if file_path != current_file:
    current_file = file_path
    # 查找匹配的配置
    target_write_pairs = set()
    for target_file, config in FILE_TARGETS.items():
        if file_path.endswith(target_file):
            target_write_pairs = set(config.get('write_pairs', []))
            break

# 只输出目标函数-变量对
if (func, var) in target_write_pairs:
    print("WRITE|%s|%s|%s|%s" % (func, var, p[0].file, p[0].line))
'''
        
        # 保存规则文件
        with open(rules_path / "variable_read_selective.cocci", 'w') as f:
            f.write(read_rule)
        
        with open(rules_path / "variable_write_selective.cocci", 'w') as f:
            f.write(write_rule)
        
        print(f"选择性验证规则已创建在: {rules_path}")
        
        # 打印统计信息
        total_read_pairs = sum(len(targets['read_pairs']) for targets in file_access_groups.values())
        total_write_pairs = sum(len(targets['write_pairs']) for targets in file_access_groups.values())
        print(f"目标读访问对: {total_read_pairs} 个")
        print(f"目标写访问对: {total_write_pairs} 个")
    
    def _create_entity_whitelists(self, rules_path):
        """创建函数和变量白名单文件"""
        # 创建函数白名单
        func_file = rules_path / "valid_functions.txt"
        with open(func_file, 'w') as f:
            for func in sorted(self.db_functions):
                f.write(f"{func}\n")
        print(f"创建函数白名单: {func_file} ({len(self.db_functions)}个)")
        
        # 创建变量白名单
        var_file = rules_path / "valid_variables.txt"
        with open(var_file, 'w') as f:
            for var in sorted(self.db_variables):
                f.write(f"{var}\n")
        print(f"创建变量白名单: {var_file} ({len(self.db_variables)}个)")
    
    def _get_file_complexity_info(self, file_path, access_count):
        """获取文件复杂度信息，用于进度估算
        
        Args:
            file_path: 文件路径
            access_count: 该文件的目标访问关系数量
            
        Returns:
            tuple: (estimated_time_minutes, should_process, category, line_count)
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
            
            # 复杂度评估（仅用于进度显示，不用于超时限制）
            if line_count < 1000:
                estimated_time = max(0.5, access_count * 0.1)  # 小文件：每个目标0.1分钟
                category = "small"
            elif line_count < 3000:
                estimated_time = max(1, access_count * 0.2)    # 中等文件：每个目标0.2分钟
                category = "medium"
            elif line_count < 5000:
                estimated_time = max(2, access_count * 0.5)    # 大文件：每个目标0.5分钟
                category = "large"
            elif line_count < 8000:
                estimated_time = max(5, access_count * 1.0)    # 很大文件：每个目标1分钟
                category = "very_large"
            else:
                estimated_time = max(10, access_count * 2.0)   # 超大文件：每个目标2分钟
                category = "huge"
            
            return (estimated_time, True, category, line_count)
            
        except Exception:
            return (1, True, "unknown", 0)

    def _process_single_file_with_rule(self, args):
        """处理单个文件的单个规则（无超时限制，确保数据完整性）"""
        full_path, normalized_path, rule_file, access_type, target_access_count, estimated_time = args
        
        try:
            print(f"  处理 {normalized_path} (预计{estimated_time:.1f}分钟, {target_access_count}个目标) - {access_type}")
            start_time = time.time()
            
                    cmd = ['spatch', '--sp-file', str(rule_file), full_path]
            # 移除timeout参数，允许Coccinelle完整处理文件
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            detections = []
                    if result.returncode == 0 and result.stdout.strip():
                        # 解析输出
                        for line in result.stdout.strip().split('\n'):
                            if line.strip() and '|' in line and not line.startswith('加载了'):
                                parts = line.split('|')
                                
                                if len(parts) >= 4:
                                    detected_type = parts[0]
                                    func_name = parts[1]
                                    var_name = parts[2]
                                    file_path = parts[3]
                                    line_num = parts[4] if len(parts) > 4 else None
                                    
                                    # 如果行号在文件路径中，提取它
                                    if line_num is None and '|' in file_path:
                                        file_path, line_num = file_path.rsplit('|', 1)
                                    elif line_num is None:
                                        # 尝试从文件路径末尾提取行号
                                        try:
                                            line_num = file_path.split('|')[-1]
                                        except:
                                            continue
                                    
                                    try:
                                        line_num = int(line_num)
                                        detection_record = {
                                            'function': func_name,
                                            'variable': var_name,
                                            'access_type': access_type,
                                            'line': line_num
                                        }
                                detections.append(detection_record)
                                    except ValueError:
                                        continue
                                        
            # 计算实际处理时间
            actual_time = (time.time() - start_time) / 60  # 转换为分钟
            status_info = f"success|{actual_time:.1f}min|{len(detections)}detected"
            
            if actual_time > estimated_time * 2:
                print(f"  ⚠️  {normalized_path} 处理时间({actual_time:.1f}分钟)超出预期({estimated_time:.1f}分钟)")
            else:
                print(f"  ✅ {normalized_path} 完成 ({actual_time:.1f}分钟, 检测到{len(detections)}个关系)")
            
            return normalized_path, detections, status_info
            
        except KeyboardInterrupt:
            print(f"  ❌ 用户中断: {normalized_path}")
            return normalized_path, [], "interrupted"
                except Exception as e:
            actual_time = (time.time() - start_time) / 60
            print(f"  ❌ 处理错误: {normalized_path} ({actual_time:.1f}分钟后出错)")
            return normalized_path, [], f"error: {str(e)}"

    def run_coccinelle_detection(self, rules_dir):
        """运行选择性Coccinelle检测，只检测数据库中记录的具体函数-变量对"""
        if not self.coccinelle_available:
            print("Coccinelle不可用，跳过检测")
            return False
        
        print("正在运行选择性Coccinelle检测...")
        
        # 获取需要检测的文件列表及其复杂度信息
        files_to_check = []
        total_estimated_time = 0
        for file_path in self.db_access_relations.keys():
            full_path = self.source_root / file_path
            if full_path.exists():
                access_count = len(self.db_access_relations[file_path])
                estimated_time, should_process, category, line_count = self._get_file_complexity_info(str(full_path), access_count)
                files_to_check.append((str(full_path), file_path, access_count, estimated_time, category, line_count))
                total_estimated_time += estimated_time
        
        self.processing_stats['total_files'] = len(files_to_check)
        print(f"需要检测的文件: {len(files_to_check)} 个")
        
        # 分析文件复杂度分布
        complexity_stats = defaultdict(int)
        target_stats = defaultdict(int)
        total_targets = 0
        
        for _, _, access_count, estimated_time, category, line_count in files_to_check:
            total_targets += access_count
            complexity_stats[category] += 1
            
            if access_count <= 5:
                target_stats["少量(≤5)"] += 1
            elif access_count <= 15:
                target_stats["中等(6-15)"] += 1
            elif access_count <= 30:
                target_stats["较多(16-30)"] += 1
            else:
                target_stats["很多(>30)"] += 1
        
        print(f"文件复杂度分布: {dict(complexity_stats)}")
        print(f"目标访问关系分布: {dict(target_stats)}")
        print(f"总目标访问关系: {total_targets} 个")
        print(f"预计总处理时间: {total_estimated_time:.1f} 分钟 (无超时限制，确保数据完整性)")
        
        # 显示大文件警告
        large_files = [f for f in files_to_check if f[4] in ['very_large', 'huge']]
        if large_files:
            print(f"⚠️  检测到 {len(large_files)} 个复杂文件，可能需要较长处理时间:")
            for full_path, file_path, access_count, estimated_time, category, line_count in large_files:
                print(f"   {file_path}: {line_count}行, {access_count}个目标, 预计{estimated_time:.1f}分钟")
        
        # 运行检测
        detection_results = defaultdict(list)
        rules = ['variable_read_selective.cocci', 'variable_write_selective.cocci']
        
        for rule in rules:
            rule_file = rules_dir / rule
            if not rule_file.exists():
                continue
            
            access_type = 'read' if 'read' in rule else 'write'
            print(f"运行选择性 {rule} 检测...")
            
            # 准备并行处理的任务
            tasks = []
            for full_path, normalized_path, access_count, estimated_time, category, line_count in files_to_check:
                tasks.append((full_path, normalized_path, rule_file, access_type, access_count, estimated_time))
            
            # 使用线程池进行并行处理（较少线程数，避免系统过载）
            print(f"\n开始{access_type}检测 (使用2个并行线程)...")
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(self._process_single_file_with_rule, tasks))
            
            # 统计处理结果
            processed_count = 0
            total_detections = 0
            total_time = 0
            
            for normalized_path, detections, status_info in results:
                if status_info.startswith("success"):
                    detection_results[normalized_path].extend(detections)
                    processed_count += 1
                    total_detections += len(detections)
                    
                    # 解析处理时间
                    try:
                        time_part = status_info.split('|')[1]
                        file_time = float(time_part.replace('min', ''))
                        total_time += file_time
                    except:
                        pass
                        
                elif status_info == "interrupted":
                    print(f"❌ 用户中断处理")
                    self.processing_stats['interrupted_files'] += 1
                    return False  # 中断整个验证过程
                    
                elif status_info.startswith("error:"):
                    error_msg = status_info.split(":", 1)[1]
                    print(f"❌ 处理错误: {normalized_path} - {error_msg}")
                    self.processing_stats['error_files'] += 1
            
            print(f"✅ {access_type}检测完成: {total_detections}个关系, 总用时{total_time:.1f}分钟")
            
            # 更新成功处理统计（避免重复计算）
            if access_type == 'read':  # 只在第一次规则运行时统计
                self.processing_stats['processed_files'] = processed_count
        
        self.coccinelle_detections = dict(detection_results)
        
        total_detections = sum(len(detections) for detections in self.coccinelle_detections.values())
        print(f"选择性检测完成，发现访问关系: {total_detections} 个")
        
        # 打印处理统计
        stats = self.processing_stats
        print(f"\n处理统计:")
        print(f"  成功处理: {stats['processed_files']} 个文件")
        print(f"  错误文件: {stats['error_files']} 个文件")
        if stats.get('interrupted_files', 0) > 0:
            print(f"  中断文件: {stats['interrupted_files']} 个文件")
        print(f"  总文件数: {stats['total_files']} 个文件")
        print(f"  处理成功率: {stats['processed_files']/stats['total_files']*100:.1f}%")
        
        return True
    
    def compare_and_validate(self):
        """对比数据库记录与Coccinelle检测结果"""
        print("正在对比验证...")
        
        file_results = {}
        overall_stats = {
            'total_db_accesses': 0,
            'total_cocci_detections': 0,
            'matched_accesses': 0,
            'db_only_accesses': 0,
            'cocci_only_accesses': 0,
            'files_processed': 0
        }
        
        # 获取所有需要验证的文件
        all_files = set(self.db_access_relations.keys()) | set(self.coccinelle_detections.keys())
        
        for file_path in all_files:
            db_accesses = self.db_access_relations.get(file_path, [])
            cocci_accesses = self.coccinelle_detections.get(file_path, [])
            
            # 转换为可比较的格式 (function, variable, access_type)
            db_set = set()
            for access in db_accesses:
                key = (access['function'], access['variable'], access['access_type'])
                db_set.add(key)
            
            cocci_set = set()
            for access in cocci_accesses:
                key = (access['function'], access['variable'], access['access_type'])
                cocci_set.add(key)
            
            # 计算匹配情况
            matched = db_set & cocci_set
            db_only = db_set - cocci_set
            cocci_only = cocci_set - db_set
            
            # 计算准确性指标
            precision = len(matched) / len(cocci_set) if cocci_set else 0
            recall = len(matched) / len(db_set) if db_set else 0
            f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            file_result = {
                'file_path': file_path,
                'db_accesses_count': len(db_set),
                'cocci_detections_count': len(cocci_set),
                'matched_count': len(matched),
                'db_only_count': len(db_only),
                'cocci_only_count': len(cocci_only),
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score,
                'matched_accesses': list(matched),
                'db_only_accesses': list(db_only),
                'cocci_only_accesses': list(cocci_only)
            }
            
            file_results[file_path] = file_result
            
            # 更新总体统计
            overall_stats['total_db_accesses'] += len(db_set)
            overall_stats['total_cocci_detections'] += len(cocci_set)
            overall_stats['matched_accesses'] += len(matched)
            overall_stats['db_only_accesses'] += len(db_only)
            overall_stats['cocci_only_accesses'] += len(cocci_only)
            overall_stats['files_processed'] += 1
        
        # 计算总体准确性指标
        total_precision = overall_stats['matched_accesses'] / overall_stats['total_cocci_detections'] if overall_stats['total_cocci_detections'] > 0 else 0
        total_recall = overall_stats['matched_accesses'] / overall_stats['total_db_accesses'] if overall_stats['total_db_accesses'] > 0 else 0
        total_f1 = 2 * total_precision * total_recall / (total_precision + total_recall) if (total_precision + total_recall) > 0 else 0
        
        overall_stats.update({
            'overall_precision': total_precision,
            'overall_recall': total_recall,
            'overall_f1_score': total_f1
        })
        
        self.validation_results = {
            'overall_stats': overall_stats,
            'file_results': file_results,
            'validation_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print(f"验证完成! 总体结果:")
        print(f"  处理文件: {overall_stats['files_processed']} 个")
        print(f"  数据库访问关系: {overall_stats['total_db_accesses']} 个")
        print(f"  Coccinelle检测: {overall_stats['total_cocci_detections']} 个")
        print(f"  匹配成功: {overall_stats['matched_accesses']} 个")
        print(f"  准确率(Precision): {total_precision:.3f}")
        print(f"  召回率(Recall): {total_recall:.3f}")
        print(f"  F1分数: {total_f1:.3f}")
        
        return True
    
    def print_detailed_results(self, max_samples=5):
        """打印详细验证结果"""
        if not self.validation_results:
            print("没有验证结果")
            return
        
        print(f"\n=== 详细验证结果 ===")
        
        file_results = self.validation_results['file_results']
        
        # 找出最有代表性的文件进行展示
        interesting_files = []
        for file_path, result in file_results.items():
            if result['db_accesses_count'] > 0:  # 只看有数据库记录的文件
                interesting_files.append((file_path, result))
        
        # 按数据库访问关系数量排序，展示最丰富的几个文件
        interesting_files.sort(key=lambda x: x[1]['db_accesses_count'], reverse=True)
        
        for file_path, result in interesting_files[:3]:  # 只看前3个最丰富的文件
            print(f"\n文件: {file_path}")
            print(f"  数据库记录: {result['db_accesses_count']} 个")
            print(f"  Coccinelle检测: {result['cocci_detections_count']} 个")
            print(f"  匹配成功: {result['matched_count']} 个")
            print(f"  数据库独有: {result['db_only_count']} 个")
            print(f"  Coccinelle独有: {result['cocci_only_count']} 个")
            print(f"  F1分数: {result['f1_score']:.3f}")
            
            # 显示匹配的访问关系
            if result['matched_accesses']:
                print("  ✅ 匹配的访问关系:")
                for i, (func, var, access_type) in enumerate(result['matched_accesses'][:max_samples]):
                    print(f"    {i+1}. {func} -> {var} ({access_type})")
                if len(result['matched_accesses']) > max_samples:
                    print(f"    ... 还有 {len(result['matched_accesses']) - max_samples} 个")
            
            # 显示数据库独有的访问关系（Coccinelle遗漏）
            if result['db_only_accesses']:
                print("  ⚠️ 数据库独有访问关系（Coccinelle遗漏）:")
                for i, (func, var, access_type) in enumerate(result['db_only_accesses'][:max_samples]):
                    print(f"    {i+1}. {func} -> {var} ({access_type})")
                if len(result['db_only_accesses']) > max_samples:
                    print(f"    ... 还有 {len(result['db_only_accesses']) - max_samples} 个")
            
            # 显示Coccinelle独有的访问关系（数据库遗漏）
            if result['cocci_only_accesses']:
                print("  🔍 Coccinelle独有访问关系（数据库遗漏）:")
                for i, (func, var, access_type) in enumerate(result['cocci_only_accesses'][:max_samples]):
                    print(f"    {i+1}. {func} -> {var} ({access_type})")
                if len(result['cocci_only_accesses']) > max_samples:
                    print(f"    ... 还有 {len(result['cocci_only_accesses']) - max_samples} 个")

    def generate_json_report(self, output_file=None):
        """生成JSON格式的验证报告"""
        if not self.validation_results:
            print("没有验证结果，无法生成报告")
            return False
        
        # 构建数据库独有访问关系的详细信息
        missed_by_coccinelle_detailed = []
        
        for file_path, result in self.validation_results['file_results'].items():
            # 获取完整的数据库访问记录
            db_accesses = self.db_access_relations.get(file_path, [])
            
            # 转换Coccinelle检测结果为可查找的集合
            cocci_set = set()
            for access in self.coccinelle_detections.get(file_path, []):
                key = (access['function'], access['variable'], access['access_type'])
                cocci_set.add(key)
            
            # 找出数据库有但Coccinelle没检测到的访问关系
            for access in db_accesses:
                key = (access['function'], access['variable'], access['access_type'])
                if key not in cocci_set:
                    missed_record = {
                        "function": access['function'],
                        "variable": access['variable'],
                        "access_type": access['access_type'],
                        "file_path": file_path,
                        "line": access['line']
                    }
                    missed_by_coccinelle_detailed.append(missed_record)
        
        # 构建报告
        overall_stats = self.validation_results['overall_stats']
        report = {
            "metadata": {
                "database": os.path.basename(self.db_path),
                "source_root": str(self.source_root),
                "subsystem": self.subsystem,
                "target_file": self.target_file,
                "validation_time": time.strftime('%Y年 %m月 %d日 星期%w %H:%M:%S '),
                "validation_logic": "Coccinelle访问关系验证 - 检查数据库AccessRelations表的准确性",
                "processing_stats": self.processing_stats
            },
            "summary": {
                "access_relations": {
                    "coverage_rate": f"{overall_stats['overall_recall']*100:.1f}%",
                    "precision_rate": f"{overall_stats['overall_precision']*100:.1f}%",
                    "f1_score": f"{overall_stats['overall_f1_score']:.3f}"
                }
            },
            "detailed_results": {
                "access_relations": {
                    "coccinelle_total": overall_stats['total_cocci_detections'],
                    "db_total": overall_stats['total_db_accesses'],
                    "matched_total": overall_stats['matched_accesses'],
                    "missed_by_coccinelle_count": len(missed_by_coccinelle_detailed),
                    "coverage_rate": overall_stats['overall_recall'],
                    "precision_rate": overall_stats['overall_precision'],
                    "missed_by_coccinelle_detailed": missed_by_coccinelle_detailed
                }
            }
        }
        
        # 输出文件名
        if output_file is None:
            if self.target_file:
                safe_filename = self.target_file.replace('/', '_').replace('.c', '')
                output_file = f"reports/coccinelle_validation_{safe_filename}.json"
            elif self.subsystem:
                output_file = f"reports/coccinelle_validation_{self.subsystem}.json"
            else:
                output_file = "reports/coccinelle_validation_full.json"
        
        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入JSON文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"JSON报告已生成: {output_path}")
            return True
            
        except Exception as e:
            print(f"生成JSON报告失败: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='精确的Coccinelle访问关系验证器')
    parser.add_argument('--db', required=True, help='数据库文件路径')
    parser.add_argument('--source', required=True, help='Linux源码根目录')
    parser.add_argument('--subsystem', help='指定子系统 (如: mm)')
    parser.add_argument('--target-file', help='指定单个文件 (如: mm/backing-dev.c)')
    parser.add_argument('--output', help='输出JSON报告文件路径')
    parser.add_argument('--show-details', action='store_true', help='显示详细结果')
    
    args = parser.parse_args()
    
    try:
        # 创建验证器
        validator = AccurateCoccinelleValidator(
            db_path=args.db,
            source_root=args.source,
            subsystem=args.subsystem,
            target_file=args.target_file
        )
        
        # 步骤1: 提取数据库实体
        print("\n步骤1: 从数据库提取函数和变量实体")
        if not validator.extract_database_entities():
            print("从数据库提取实体失败")
            return 1
        
        # 步骤2: 提取数据库访问关系
        print("\n步骤2: 从数据库提取访问关系基准")
        if not validator.extract_database_access_relations():
            print("从数据库提取访问关系失败")
            return 1
        
        # 步骤3: 创建选择性Coccinelle规则
        print("\n步骤3: 创建选择性Coccinelle规则")
        rules_dir = validator.create_selective_coccinelle_rules()
        
        # 步骤4: 运行Coccinelle检测
        print("\n步骤4: 运行Coccinelle检测")
        if not validator.run_coccinelle_detection(rules_dir):
            print("Coccinelle检测失败")
            return 1
        
        # 步骤5: 对比验证
        print("\n步骤5: 对比验证计算准确性")
        if not validator.compare_and_validate():
            print("对比验证失败")
            return 1
        
        # 步骤6: 生成JSON验证报告
        print("\n步骤6: 生成JSON验证报告")
        if not validator.generate_json_report(args.output):
            print("生成JSON报告失败")
            return 1
        
        # 显示详细结果（如果需要）
        if args.show_details:
            validator.print_detailed_results()
        
        print(f"\n=== 验证完成 ===")
        stats = validator.validation_results['overall_stats']
        print(f"数据库有但Coccinelle未检测到的关系: {stats['db_only_accesses']} 个")
        if args.output:
            print(f"详细报告: {args.output}")
        else:
            if args.target_file:
                safe_filename = args.target_file.replace('/', '_').replace('.c', '')
                print(f"详细报告: reports/coccinelle_validation_{safe_filename}.json")
            elif args.subsystem:
                print(f"详细报告: reports/coccinelle_validation_{args.subsystem}.json")
            else:
                print(f"详细报告: reports/coccinelle_validation_full.json")
        
        return 0
        
    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
