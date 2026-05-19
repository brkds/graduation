#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
过滤式快速Coccinelle验证器
只检测数据库中存在的函数和全局变量，不提取位置信息
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
from datetime import datetime

class FilteredFastValidator:
    def __init__(self, db_path, source_root, subsystem=None, target_file=None, output_file=None):
        self.db_path = Path(db_path)
        self.source_root = Path(source_root)
        self.subsystem = subsystem
        self.target_file = target_file
        self.output_file = output_file
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
        
        if not self.source_root.exists():
            raise FileNotFoundError(f"源码目录不存在: {self.source_root}")
        
        self.coccinelle_available = self._check_coccinelle()
        
        # 数据存储
        self.db_functions = set()  # 数据库中的函数
        self.db_variables = set()  # 数据库中的全局变量
        self.db_access_relations = {}  # {file_path: [(func, var, access_type), ...]}
        self.coccinelle_detections = {}  # {file_path: [(func, var, access_type), ...]}
        self.file_processing_details = {}  # 文件处理详情
        
        # 验证结果数据
        self.validation_results = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'validator_version': '3.0_filtered_fast',
                'database_path': str(self.db_path),
                'source_path': str(self.source_root),
                'target_subsystem': subsystem,
                'target_file': target_file,
                'coccinelle_available': self.coccinelle_available
            },
            'validation_summary': {},
            'coverage_analysis': {},
            'uncovered_data': {},
            'performance_metrics': {}
        }
        
        print(f"过滤式快速验证器初始化完成")
        if target_file:
            print(f"验证目标文件: {target_file}")
        elif subsystem:
            print(f"验证目标子系统: {subsystem}")
    
    def _check_coccinelle(self):
        try:
            result = subprocess.run(['spatch', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _build_path_filter(self):
        if self.target_file:
            return f"AND file_path LIKE '%{self.target_file}'"
        elif self.subsystem:
            return f"AND file_path LIKE '%linux-6.6/{self.subsystem}/%'"
        else:
            return "AND file_path LIKE '%linux-6.6/%'"
    
    def extract_database_entities(self):
        """从数据库提取函数和全局变量实体（基于访问关系，而非定义位置）"""
        print("正在从数据库提取函数和全局变量实体...")
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建路径过滤条件 - 与extract_database_access_relations保持一致
            source_root_str = str(self.source_root.resolve())  # 转换为绝对路径
            if self.target_file:
                # 精确匹配单个文件，使用完整路径
                exact_path = f"{source_root_str}/{self.target_file}"
                path_filter = f"AND ar.access_file_path = '{exact_path}'"
            elif self.subsystem:
                # 精确匹配子系统路径前缀，使用完整路径
                subsystem_prefix = f"{source_root_str}/{self.subsystem}/"
                path_filter = f"AND ar.access_file_path GLOB '{subsystem_prefix}*'"
            else:
                # 匹配整个源码目录
                source_prefix = f"{source_root_str}/"
                path_filter = f"AND ar.access_file_path GLOB '{source_prefix}*'"
            
            # 从AccessRelations表中提取实际涉及的函数
            func_query = f"""
                SELECT DISTINCT f.name
                FROM Functions f 
                JOIN AccessRelations ar ON f.id = ar.function_id 
                WHERE 1=1 {path_filter}
            """
            cursor.execute(func_query)
            functions_data = cursor.fetchall()
            
            for (name,) in functions_data:
                self.db_functions.add(name)
            
            # 从AccessRelations表中提取实际涉及的全局变量
            var_query = f"""
                SELECT DISTINCT gv.name
                FROM GlobalVariables gv 
                JOIN AccessRelations ar ON gv.id = ar.variable_id 
                WHERE 1=1 {path_filter}
            """
            cursor.execute(var_query)
            variables_data = cursor.fetchall()
            
            for (name,) in variables_data:
                self.db_variables.add(name)
            
            conn.close()
            
            duration = time.time() - start_time
            self.validation_results['performance_metrics']['entity_extraction_time'] = duration
            
            print(f"数据库实体提取完成:")
            print(f"  函数: {len(self.db_functions)} 个")
            print(f"  全局变量: {len(self.db_variables)} 个")
            print(f"  用时: {duration:.2f}秒")
            
            # 显示样本
            if self.db_functions:
                print(f"  函数样本: {list(self.db_functions)[:5]}")
            if self.db_variables:
                print(f"  变量样本: {list(self.db_variables)[:5]}")
            
            return True
            
        except Exception as e:
            print(f"从数据库提取实体时发生错误: {e}")
            return False
    
    def extract_database_access_relations(self):
        """从数据库提取访问关系作为基准（不包含行号）"""
        print("正在从数据库提取访问关系...")
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建路径过滤条件 - 使用完整路径匹配
            source_root_str = str(self.source_root.resolve())  # 转换为绝对路径
            if self.target_file:
                # 精确匹配单个文件，使用完整路径
                exact_path = f"{source_root_str}/{self.target_file}"
                path_filter = f"AND ar.access_file_path = '{exact_path}'"
            elif self.subsystem:
                # 精确匹配子系统路径前缀，使用完整路径
                subsystem_prefix = f"{source_root_str}/{self.subsystem}/"
                path_filter = f"AND ar.access_file_path GLOB '{subsystem_prefix}*'"
            else:
                # 匹配整个源码目录
                source_prefix = f"{source_root_str}/"
                path_filter = f"AND ar.access_file_path GLOB '{source_prefix}*'"
            
            # 提取访问关系（不需要行号）
            query = f"""
                SELECT ar.access_type, ar.access_file_path,
                       gv.name as var_name, f.name as func_name
                FROM AccessRelations ar 
                JOIN GlobalVariables gv ON ar.variable_id = gv.id 
                JOIN Functions f ON ar.function_id = f.id 
                WHERE 1=1 {path_filter}
                ORDER BY ar.access_file_path
            """
            
            cursor.execute(query)
            access_data = cursor.fetchall()
            
            # 组织数据：按文件分组，存储为(func, var, access_type)元组
            file_access_map = defaultdict(set)
            access_type_counts = defaultdict(int)
            
            for row in access_data:
                access_type, file_path, var_name, func_name = row
                
                # 标准化文件路径
                normalized_path = self._normalize_path(file_path)
                
                # 存储为元组，自动去重
                access_tuple = (func_name, var_name, access_type)
                file_access_map[normalized_path].add(access_tuple)
                access_type_counts[access_type] += 1
            
            conn.close()
            
            # 转换为列表格式
            self.db_access_relations = {
                file_path: list(accesses) 
                for file_path, accesses in file_access_map.items()
            }
            
            total_accesses = sum(len(accesses) for accesses in self.db_access_relations.values())
            
            duration = time.time() - start_time
            self.validation_results['performance_metrics']['access_relation_extraction_time'] = duration
            
            print(f"数据库访问关系提取完成:")
            print(f"  涉及文件: {len(self.db_access_relations)} 个")
            print(f"  总访问关系: {total_accesses} 个")
            print(f"  用时: {duration:.2f}秒")
            
            for access_type, count in access_type_counts.items():
                print(f"    {access_type}: {count} 个")
            
            # 显示样本
            if self.db_access_relations:
                sample_file = list(self.db_access_relations.keys())[0]
                sample_accesses = self.db_access_relations[sample_file][:3]
                print(f"  访问关系样本: {sample_accesses}")
            
            return True
            
        except Exception as e:
            print(f"从数据库提取访问关系时发生错误: {e}")
            return False
    
    def _normalize_path(self, db_path):
        """将数据库中的绝对路径转换为相对于源码根目录的相对路径"""
        source_root_str = str(self.source_root.resolve())  # 转换为绝对路径
        if source_root_str in db_path:
            return db_path.replace(f"{source_root_str}/", "")
        return db_path
    
    def create_filtered_rules(self, rules_dir="filtered_rules"):
        """创建过滤式Coccinelle规则，只匹配数据库中的函数和变量"""
        print(f"正在创建过滤式Coccinelle规则...")
        start_time = time.time()
        
        rules_path = Path(rules_dir)
        rules_path.mkdir(exist_ok=True)
        
        print(f"规则目录: {rules_path}")
        
        # 创建函数和变量白名单文件
        self._create_entity_whitelists(rules_path)
        
        # 获取当前工作目录的绝对路径
        current_dir = Path.cwd()
        whitelist_dir = current_dir / rules_path
        
        # 创建过滤式读访问规则
        read_rule = f"""// 过滤式检测函数中的全局变量读访问
@initialize:python@
@@

# 加载函数白名单
valid_functions = set()
try:
    with open("{whitelist_dir}/valid_functions.txt", "r") as f:
        for line in f:
            func_name = line.strip()
            if func_name:
                valid_functions.add(func_name)
    print(f"加载了 {{len(valid_functions)}} 个有效函数")
except Exception as e:
    print(f"无法加载函数白名单: {{e}}")

# 加载全局变量白名单
valid_variables = set()
try:
    with open("{whitelist_dir}/valid_variables.txt", "r") as f:
        for line in f:
            var_name = line.strip()
            if var_name:
                valid_variables.add(var_name)
    print(f"加载了 {{len(valid_variables)}} 个有效全局变量")
except Exception as e:
    print(f"无法加载变量白名单: {{e}}")

@rule@
identifier func, var;
@@

func(...) {{
    ...
    var
    ...
}}

@script:python@
func << rule.func;
var << rule.var;
@@

# 只处理白名单中的函数和全局变量
if func in valid_functions and var in valid_variables:
    print(f"read|{{func}}|{{var}}")
"""
        
        with open(rules_path / "filtered_read.cocci", 'w', encoding='utf-8') as f:
            f.write(read_rule)
        
        # 创建过滤式写访问规则
        write_rule = f"""// 过滤式检测函数中的全局变量写访问
@initialize:python@
@@

# 加载函数白名单
valid_functions = set()
try:
    with open("{whitelist_dir}/valid_functions.txt", "r") as f:
        for line in f:
            func_name = line.strip()
            if func_name:
                valid_functions.add(func_name)
    print(f"加载了 {{len(valid_functions)}} 个有效函数")
except Exception as e:
    print(f"无法加载函数白名单: {{e}}")

# 加载全局变量白名单
valid_variables = set()
try:
    with open("{whitelist_dir}/valid_variables.txt", "r") as f:
        for line in f:
            var_name = line.strip()
            if var_name:
                valid_variables.add(var_name)
    print(f"加载了 {{len(valid_variables)}} 个有效全局变量")
except Exception as e:
    print(f"无法加载变量白名单: {{e}}")

@rule@
identifier func, var;
@@

func(...) {{
    ...
    var = ...;
    ...
}}

@script:python@
func << rule.func;
var << rule.var;
@@

# 只处理白名单中的函数和全局变量
if func in valid_functions and var in valid_variables:
    print(f"write|{{func}}|{{var}}")
"""
        
        with open(rules_path / "filtered_write.cocci", 'w', encoding='utf-8') as f:
            f.write(write_rule)
        
        duration = time.time() - start_time
        self.validation_results['performance_metrics']['rule_creation_time'] = duration
        
        print(f"过滤式Coccinelle规则创建完成，用时: {duration:.2f}秒")
        return rules_path
    
    def _create_entity_whitelists(self, rules_path):
        """创建函数和变量白名单文件"""
        # 创建函数白名单
        with open(rules_path / "valid_functions.txt", 'w', encoding='utf-8') as f:
            for func_name in sorted(self.db_functions):
                f.write(f"{func_name}\n")
        
        # 创建变量白名单
        with open(rules_path / "valid_variables.txt", 'w', encoding='utf-8') as f:
            for var_name in sorted(self.db_variables):
                f.write(f"{var_name}\n")
        
        print(f"白名单文件创建完成:")
        print(f"  函数白名单: {len(self.db_functions)} 个")
        print(f"  变量白名单: {len(self.db_variables)} 个")
    
    def run_filtered_detection(self, rules_dir):
        """运行过滤式Coccinelle检测"""
        if not self.coccinelle_available:
            print("Coccinelle不可用，跳过检测")
            return False
        
        print("正在运行过滤式Coccinelle检测...")
        total_start_time = time.time()
        
        # 获取需要检测的文件列表
        files_to_check = []
        for file_path in self.db_access_relations.keys():
            full_path = self.source_root / file_path
            if full_path.exists():
                files_to_check.append((str(full_path), file_path))
        
        print(f"需要检测的文件: {len(files_to_check)} 个")
        
        # 运行检测
        detection_results = defaultdict(set)
        rules = ['filtered_read.cocci', 'filtered_write.cocci']
        
        for rule in rules:
            rule_file = rules_dir / rule
            if not rule_file.exists():
                continue
            
            access_type = 'read' if 'read' in rule else 'write'
            print(f"\n运行过滤式 {rule} 检测...")
            
            for full_path, normalized_path in files_to_check:
                print(f"  处理 {normalized_path} - {access_type}...")
                
                if normalized_path not in self.file_processing_details:
                    self.file_processing_details[normalized_path] = {
                        'read_time': 0, 'write_time': 0, 'read_detections': 0, 'write_detections': 0,
                        'read_status': 'pending', 'write_status': 'pending'
                    }
                
                start_time = time.time()
                try:
                    cmd = ['spatch', '--sp-file', str(rule_file), full_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=None)
                    
                    detections = []
                    if result.returncode == 0 and result.stdout.strip():
                        lines = result.stdout.strip().split('\n')
                        for line in lines:
                            line = line.strip()
                            # 跳过加载信息
                            if line.startswith('加载了') or line.startswith('无法加载') or not line:
                                continue
                            
                            if '|' in line:
                                parts = line.split('|')
                                if len(parts) >= 3:
                                    detected_type = parts[0]
                                    func_name = parts[1]
                                    var_name = parts[2]
                                    
                                    # 确认是我们期望的访问类型
                                    if detected_type == access_type:
                                        # 存储为元组 (func, var, access_type)
                                        detection_tuple = (func_name, var_name, access_type)
                                        detections.append(detection_tuple)
                    
                    detection_results[normalized_path].update(detections)
                    duration = time.time() - start_time
                    
                    # 记录处理详情
                    if access_type == 'read':
                        self.file_processing_details[normalized_path]['read_time'] = duration
                        self.file_processing_details[normalized_path]['read_detections'] = len(detections)
                        self.file_processing_details[normalized_path]['read_status'] = 'success'
                    else:
                        self.file_processing_details[normalized_path]['write_time'] = duration
                        self.file_processing_details[normalized_path]['write_detections'] = len(detections)
                        self.file_processing_details[normalized_path]['write_status'] = 'success'
                    
                    print(f"    ✅ 完成: {duration:.1f}秒, {len(detections)}个检测")
                    
                    # 显示检测样本
                    if detections:
                        print(f"    样本: {detections[:3]}")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    if access_type == 'read':
                        self.file_processing_details[normalized_path]['read_time'] = duration
                        self.file_processing_details[normalized_path]['read_status'] = f'error: {str(e)}'
                    else:
                        self.file_processing_details[normalized_path]['write_time'] = duration
                        self.file_processing_details[normalized_path]['write_status'] = f'error: {str(e)}'
                    print(f"    ❌ 错误: {duration:.1f}秒 - {e}")
        
        # 转换为列表格式
        self.coccinelle_detections = {
            file_path: list(detections) 
            for file_path, detections in detection_results.items()
        }
        
        total_duration = time.time() - total_start_time
        total_detections = sum(len(detections) for detections in self.coccinelle_detections.values())
        
        # 记录性能指标
        self.validation_results['performance_metrics']['coccinelle_detection_time'] = total_duration
        
        print(f"\n过滤式检测完成:")
        print(f"  总用时: {total_duration:.1f} 秒")
        print(f"  发现访问关系: {total_detections} 个")
        
        # 统计检测类型
        coccinelle_type_counts = defaultdict(int)
        for detections in self.coccinelle_detections.values():
            for func, var, access_type in detections:
                coccinelle_type_counts[access_type] += 1
        
        for access_type, count in coccinelle_type_counts.items():
            print(f"    {access_type}: {count} 个")
        
        return True
    
    def compare_and_validate(self):
        """分析数据库数据的Coccinelle覆盖率（专注数据库视角）"""
        print("正在分析数据库覆盖率...")
        start_time = time.time()
        
        # 数据库覆盖率统计
        total_db_accesses = 0
        covered_db_accesses = 0
        
        uncovered_relations = {}
        
        # 获取所有有数据库访问关系的文件
        for file_path, db_accesses_list in self.db_access_relations.items():
            db_accesses = set(db_accesses_list)
            cocci_accesses = set(self.coccinelle_detections.get(file_path, []))
            
            # 计算数据库数据的覆盖情况
            covered = db_accesses & cocci_accesses  # 被Coccinelle检测到的数据库关系
            uncovered = db_accesses - cocci_accesses  # 未被检测到的数据库关系
            
            # 文件级别的数据库覆盖率
            db_coverage = len(covered) / len(db_accesses) if db_accesses else 0
            
            # 收集未覆盖的数据库关系
            if uncovered:
                uncovered_relations[file_path] = list(uncovered)
            
            # 更新总体统计
            total_db_accesses += len(db_accesses)
            covered_db_accesses += len(covered)
            
            print(f"\n文件 {file_path}:")
            print(f"  数据库关系: {len(db_accesses)} | 被覆盖: {len(covered)} | 覆盖率: {db_coverage:.2%}")
            
            if covered:
                print(f"  ✅ 已覆盖样本: {list(covered)[:3]}")
            if uncovered:
                print(f"  ❌ 未覆盖样本: {list(uncovered)[:3]}")
        
        # 计算总体数据库覆盖率
        overall_db_coverage = covered_db_accesses / total_db_accesses if total_db_accesses > 0 else 0
        
        # 计算覆盖率统计
        coverage_stats = {
            'database_relation_coverage': overall_db_coverage,
            'covered_files': len([f for f in self.db_access_relations.keys() 
                                if f in self.coccinelle_detections and 
                                len(set(self.db_access_relations[f]) & set(self.coccinelle_detections[f])) > 0]),
            'total_files_with_db_relations': len(self.db_access_relations),
            'file_coverage': 0,
            'function_coverage': 0,
            'variable_coverage': 0
        }
        
        # 计算文件覆盖率
        coverage_stats['file_coverage'] = coverage_stats['covered_files'] / coverage_stats['total_files_with_db_relations'] if coverage_stats['total_files_with_db_relations'] > 0 else 0
        
        # 计算函数和变量覆盖率（基于数据库视角）
        covered_functions = set()
        covered_variables = set()
        all_db_functions = set()
        all_db_variables = set()
        
        # 从数据库关系中提取所有函数和变量
        for accesses in self.db_access_relations.values():
            for func, var, _ in accesses:
                all_db_functions.add(func)
                all_db_variables.add(var)
        
        # 从被覆盖的关系中提取函数和变量
        for file_path, db_accesses_list in self.db_access_relations.items():
            db_accesses = set(db_accesses_list)
            cocci_accesses = set(self.coccinelle_detections.get(file_path, []))
            covered = db_accesses & cocci_accesses
            
            for func, var, _ in covered:
                covered_functions.add(func)
                covered_variables.add(var)
        
        coverage_stats['function_coverage'] = len(covered_functions) / len(all_db_functions) if all_db_functions else 0
        coverage_stats['variable_coverage'] = len(covered_variables) / len(all_db_variables) if all_db_variables else 0
        
        duration = time.time() - start_time
        
        # 保存数据库覆盖率分析结果
        self.validation_results['validation_summary'] = {
            'database_coverage_metrics': {
                'total_database_relations': total_db_accesses,
                'covered_database_relations': covered_db_accesses,
                'database_coverage_rate': overall_db_coverage
            }
        }
        
        self.validation_results['coverage_analysis'] = {
            'coverage_statistics': coverage_stats,
            'covered_functions': sorted(list(covered_functions)),
            'covered_variables': sorted(list(covered_variables)),
            'uncovered_functions': sorted(list(all_db_functions - covered_functions)),
            'uncovered_variables': sorted(list(all_db_variables - covered_variables))
        }
        
        # 只保留未覆盖的数据库数据
        self.validation_results['uncovered_database_data'] = {
            'uncovered_relations_by_file': {
                file_path: [
                    {'function': func, 'variable': var, 'access_type': access_type}
                    for func, var, access_type in relations
                ]
                for file_path, relations in uncovered_relations.items()
            },
            'total_uncovered_relations': sum(len(relations) for relations in uncovered_relations.values()),
            'uncovered_files': len(uncovered_relations)
        }
        
        self.validation_results['performance_metrics']['validation_time'] = duration
        
        print(f"\n=== 数据库覆盖率分析 ===")
        print(f"数据库访问关系总数: {total_db_accesses}")
        print(f"被Coccinelle覆盖: {covered_db_accesses}")
        print(f"数据库覆盖率: {overall_db_coverage:.2%}")
        
        print(f"\n=== 覆盖率统计 ===")
        print(f"关系覆盖率: {coverage_stats['database_relation_coverage']:.2%}")
        print(f"文件覆盖率: {coverage_stats['file_coverage']:.2%} ({coverage_stats['covered_files']}/{coverage_stats['total_files_with_db_relations']})")
        print(f"函数覆盖率: {coverage_stats['function_coverage']:.2%}")
        print(f"变量覆盖率: {coverage_stats['variable_coverage']:.2%}")
        
        print(f"\n=== 未覆盖的数据库数据 ===")
        print(f"未覆盖的访问关系: {self.validation_results['uncovered_database_data']['total_uncovered_relations']}")
        print(f"未覆盖的文件: {self.validation_results['uncovered_database_data']['uncovered_files']}")
        print(f"未覆盖的函数: {len(self.validation_results['coverage_analysis']['uncovered_functions'])}")
        print(f"未覆盖的变量: {len(self.validation_results['coverage_analysis']['uncovered_variables'])}")
        
        return True
    
    def save_json_report(self):
        """保存详细的JSON验证报告"""
        # 确保docs目录存在
        docs_dir = Path("coccinelle_validation/docs")
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成输出文件名
        if self.output_file:
            output_path = docs_dir / Path(self.output_file).name
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if self.target_file:
                safe_filename = self.target_file.replace('/', '_').replace('.', '_')
                output_path = docs_dir / f"coccinelle_validation_{safe_filename}_{timestamp}.json"
            elif self.subsystem:
                output_path = docs_dir / f"coccinelle_validation_{self.subsystem}_{timestamp}.json"
            else:
                output_path = docs_dir / f"coccinelle_validation_full_{timestamp}.json"
        
        # 添加大文件处理时间统计
        large_file_stats = {}
        # 从file_processing_details中获取文件处理详情
        for file_path, details in self.file_processing_details.items():
            total_time = details.get('read_time', 0) + details.get('write_time', 0)
            if total_time > 10:
                large_file_stats[file_path] = {
                    'total_processing_time': total_time,
                    'read_time': details.get('read_time', 0),
                    'write_time': details.get('write_time', 0),
                    'read_status': details.get('read_status', 'unknown'),
                    'write_status': details.get('write_status', 'unknown')
                }
        
        # 添加最终的性能指标
        total_time = sum(
            self.validation_results['performance_metrics'].get(key, 0)
            for key in ['entity_extraction_time', 'access_relation_extraction_time', 
                       'rule_creation_time', 'coccinelle_detection_time', 'validation_time']
        )
        self.validation_results['performance_metrics']['total_validation_time'] = total_time
        self.validation_results['performance_metrics']['large_file_processing'] = large_file_stats
        
        # 保存JSON报告
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
            
            print(f"\n=== JSON报告已保存 ===")
            print(f"文件路径: {output_path.absolute()}")
            print(f"文件大小: {output_path.stat().st_size / 1024:.1f} KB")
            
            return str(output_path.absolute())
            
        except Exception as e:
            print(f"保存JSON报告时发生错误: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description='过滤式快速Coccinelle验证器')
    parser.add_argument('--db', required=True, help='数据库文件路径')
    parser.add_argument('--source', required=True, help='Linux源码根目录')
    parser.add_argument('--subsystem', help='验证子系统 (如: mm)')
    parser.add_argument('--file', help='验证单个文件 (如: mm/memcontrol.c)')
    parser.add_argument('--output', help='输出JSON报告文件路径')
    
    args = parser.parse_args()
    
    try:
        # 初始化验证器
        validator = FilteredFastValidator(
            args.db, args.source, 
            subsystem=args.subsystem, 
            target_file=args.file,
            output_file=args.output
        )
        
        # 执行验证流程
        print("\n=== 步骤1: 提取数据库实体 ===")
        if not validator.extract_database_entities():
            return 1
        
        print("\n=== 步骤2: 提取数据库访问关系 ===")
        if not validator.extract_database_access_relations():
            return 1
        
        print("\n=== 步骤3: 创建过滤式Coccinelle规则 ===")
        rules_dir = validator.create_filtered_rules()
        
        print("\n=== 步骤4: 运行过滤式Coccinelle检测 ===")
        if not validator.run_filtered_detection(rules_dir):
            return 1
        
        print("\n=== 步骤5: 对比验证结果 ===")
        validator.compare_and_validate()
        
        print("\n=== 步骤6: 保存JSON报告 ===")
        validator.save_json_report()
        
        return 0
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
