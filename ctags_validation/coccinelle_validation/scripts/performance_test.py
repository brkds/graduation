#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coccinelle性能测试脚本
测试单文件和子系统的分析时间，分析性能瓶颈
"""

import os
import sqlite3
import subprocess
import sys
import time
import argparse
from pathlib import Path
from collections import defaultdict
import json

class CoccinellePerformanceTester:
    def __init__(self, db_path, source_root):
        self.db_path = Path(db_path)
        self.source_root = Path(source_root)
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
        
        if not self.source_root.exists():
            raise FileNotFoundError(f"源码目录不存在: {self.source_root}")
        
        self.coccinelle_available = self._check_coccinelle()
        
        print(f"Coccinelle性能测试器初始化完成")
        print(f"数据库: {self.db_path}")
        print(f"源码目录: {self.source_root}")
        print(f"Coccinelle可用: {self.coccinelle_available}")
    
    def _check_coccinelle(self):
        try:
            result = subprocess.run(['spatch', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"Coccinelle版本: {version}")
                return True
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_file_info(self, file_path):
        full_path = self.source_root / file_path
        if not full_path.exists():
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
        except:
            line_count = 0
        
        file_size = full_path.stat().st_size
        
        return {
            'line_count': line_count,
            'file_size': file_size,
            'file_path': file_path
        }
    
    def get_access_relations_count(self, target_file=None, subsystem=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if target_file:
                path_filter = f"AND ar.access_file_path LIKE '%{target_file}'"
            elif subsystem:
                path_filter = f"AND ar.access_file_path LIKE '%linux-6.6/{subsystem}/%'"
            else:
                path_filter = "AND ar.access_file_path LIKE '%linux-6.6/%'"
            
            query = f"""
                SELECT COUNT(*), 
                       COUNT(DISTINCT ar.access_file_path) as file_count,
                       COUNT(CASE WHEN ar.access_type = 'read' THEN 1 END) as read_count,
                       COUNT(CASE WHEN ar.access_type = 'write' THEN 1 END) as write_count
                FROM AccessRelations ar 
                WHERE 1=1 {path_filter}
            """
            
            cursor.execute(query)
            total_count, file_count, read_count, write_count = cursor.fetchone()
            
            conn.close()
            
            return {
                'total_accesses': total_count,
                'file_count': file_count,
                'read_accesses': read_count,
                'write_accesses': write_count
            }
            
        except Exception as e:
            print(f"获取访问关系数量时发生错误: {e}")
            return None
    
    def create_simple_test_rules(self, output_dir="test_rules"):
        rules_path = Path(output_dir)
        rules_path.mkdir(exist_ok=True)
        
        read_rule = """
@rule@
identifier func, var;
position p;
@@

func(...) {
    ...
    var@p
    ...
}

@script:python@
func << rule.func;
var << rule.var;
p << rule.p;
@@

print(f"read|{func}|{var}|{p[0].file}|{p[0].line}")
"""
        
        with open(rules_path / "simple_read.cocci", 'w', encoding='utf-8') as f:
            f.write(read_rule)
        
        write_rule = """
@rule@
identifier func, var;
position p;
@@

func(...) {
    ...
    var@p = ...;
    ...
}

@script:python@
func << rule.func;
var << rule.var;
p << rule.p;
@@

print(f"write|{func}|{var}|{p[0].file}|{p[0].line}")
"""
        
        with open(rules_path / "simple_write.cocci", 'w', encoding='utf-8') as f:
            f.write(write_rule)
        
        print(f"简单测试规则已创建在: {rules_path}")
        return rules_path
    
    def test_single_file(self, file_path, timeout_seconds=300):
        print(f"\n=== 测试单文件性能: {file_path} ===")
        
        file_info = self.get_file_info(file_path)
        if not file_info:
            print(f"文件不存在: {file_path}")
            return None
        
        print(f"文件信息:")
        print(f"  行数: {file_info['line_count']:,}")
        print(f"  大小: {file_info['file_size']:,} 字节")
        
        access_info = self.get_access_relations_count(target_file=file_path)
        if access_info:
            print(f"数据库中的访问关系:")
            print(f"  读访问: {access_info['read_accesses']:,}")
            print(f"  写访问: {access_info['write_accesses']:,}")
            print(f"  总访问: {access_info['total_accesses']:,}")
        
        rules_path = self.create_simple_test_rules()
        
        results = {}
        full_path = self.source_root / file_path
        
        for rule_name in ['simple_read.cocci', 'simple_write.cocci']:
            rule_file = rules_path / rule_name
            access_type = 'read' if 'read' in rule_name else 'write'
            
            print(f"\n测试 {access_type} 访问检测...")
            
            start_time = time.time()
            try:
                cmd = ['spatch', '--sp-file', str(rule_file), str(full_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
                
                end_time = time.time()
                duration = end_time - start_time
                
                detections = []
                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        if line.strip() and '|' in line and line.startswith(access_type):
                            detections.append(line.strip())
                
                results[access_type] = {
                    'duration': duration,
                    'detections_count': len(detections),
                    'success': True,
                    'error': None
                }
                
                print(f"  用时: {duration:.2f} 秒")
                print(f"  检测到: {len(detections)} 个访问")
                
            except subprocess.TimeoutExpired:
                end_time = time.time()
                duration = end_time - start_time
                results[access_type] = {
                    'duration': duration,
                    'detections_count': 0,
                    'success': False,
                    'error': f'超时 (>{timeout_seconds}秒)'
                }
                print(f"  超时! (>{timeout_seconds}秒)")
                
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                results[access_type] = {
                    'duration': duration,
                    'detections_count': 0,
                    'success': False,
                    'error': str(e)
                }
                print(f"  错误: {e}")
        
        total_time = sum(r['duration'] for r in results.values())
        
        final_result = {
            'file_path': file_path,
            'file_info': file_info,
            'access_info': access_info,
            'results': results,
            'total_duration': total_time,
            'performance_summary': {
                'lines_per_second': file_info['line_count'] / total_time if total_time > 0 else 0,
                'bytes_per_second': file_info['file_size'] / total_time if total_time > 0 else 0
            }
        }
        
        print(f"\n单文件测试总结:")
        print(f"  总用时: {total_time:.2f} 秒")
        print(f"  处理速度: {final_result['performance_summary']['lines_per_second']:.0f} 行/秒")
        
        return final_result
    
    def test_subsystem_sample(self, subsystem, sample_count=10, timeout_seconds=60):
        print(f"\n=== 测试子系统抽样性能: {subsystem} ===")
        
        access_info = self.get_access_relations_count(subsystem=subsystem)
        if not access_info:
            print(f"无法获取子系统 {subsystem} 的信息")
            return None
        
        print(f"子系统 {subsystem} 信息:")
        print(f"  涉及文件: {access_info['file_count']:,}")
        print(f"  读访问: {access_info['read_accesses']:,}")
        print(f"  写访问: {access_info['write_accesses']:,}")
        print(f"  总访问: {access_info['total_accesses']:,}")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = f"""
                SELECT DISTINCT ar.access_file_path, COUNT(*) as access_count
                FROM AccessRelations ar 
                WHERE ar.access_file_path LIKE '%linux-6.6/{subsystem}/%'
                GROUP BY ar.access_file_path
                ORDER BY access_count DESC
                LIMIT {sample_count}
            """
            
            cursor.execute(query)
            sample_files = cursor.fetchall()
            conn.close()
            
        except Exception as e:
            print(f"获取文件列表时发生错误: {e}")
            return None
        
        print(f"\n选择前 {len(sample_files)} 个文件进行抽样测试:")
        for file_path, access_count in sample_files:
            rel_path = file_path.split('linux-6.6/')[-1]
            print(f"  {rel_path}: {access_count} 个访问关系")
        
        rules_path = self.create_simple_test_rules()
        
        sample_results = []
        total_duration = 0
        total_lines = 0
        total_detections = 0
        
        for i, (file_path, expected_accesses) in enumerate(sample_files, 1):
            rel_path = file_path.split('linux-6.6/')[-1]
            print(f"\n[{i}/{len(sample_files)}] 测试文件: {rel_path}")
            
            file_info = self.get_file_info(rel_path)
            if not file_info:
                print(f"  文件不存在，跳过")
                continue
            
            print(f"  文件大小: {file_info['line_count']} 行")
            
            full_path = self.source_root / rel_path
            file_duration = 0
            file_detections = 0
            
            for rule_name in ['simple_read.cocci', 'simple_write.cocci']:
                rule_file = rules_path / rule_name
                access_type = 'read' if 'read' in rule_name else 'write'
                
                start_time = time.time()
                try:
                    cmd = ['spatch', '--sp-file', str(rule_file), str(full_path)]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
                    
                    duration = time.time() - start_time
                    file_duration += duration
                    
                    detections = 0
                    if result.returncode == 0 and result.stdout.strip():
                        for line in result.stdout.strip().split('\n'):
                            if line.strip() and '|' in line and line.startswith(access_type):
                                detections += 1
                    
                    file_detections += detections
                    print(f"    {access_type}: {duration:.1f}秒, {detections}个检测")
                    
                except subprocess.TimeoutExpired:
                    duration = timeout_seconds
                    file_duration += duration
                    print(f"    {access_type}: 超时({timeout_seconds}秒)")
                except Exception as e:
                    print(f"    {access_type}: 错误 - {e}")
            
            total_duration += file_duration
            total_lines += file_info['line_count']
            total_detections += file_detections
            
            sample_results.append({
                'file_path': rel_path,
                'line_count': file_info['line_count'],
                'duration': file_duration,
                'detections': file_detections,
                'expected_accesses': expected_accesses,
                'lines_per_second': file_info['line_count'] / file_duration if file_duration > 0 else 0
            })
            
            print(f"  完成: {file_duration:.1f}秒, {file_detections}个检测")
        
        if sample_results:
            avg_lines_per_second = total_lines / total_duration if total_duration > 0 else 0
            
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                query = f"""
                    SELECT DISTINCT ar.access_file_path
                    FROM AccessRelations ar 
                    WHERE ar.access_file_path LIKE '%linux-6.6/{subsystem}/%'
                """
                
                cursor.execute(query)
                all_files = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                total_subsystem_lines = 0
                existing_files = 0
                for file_path in all_files:
                    rel_path = file_path.split('linux-6.6/')[-1]
                    file_info = self.get_file_info(rel_path)
                    if file_info:
                        total_subsystem_lines += file_info['line_count']
                        existing_files += 1
                
                estimated_total_time = total_subsystem_lines / avg_lines_per_second if avg_lines_per_second > 0 else 0
                
            except Exception as e:
                print(f"估算总时间时发生错误: {e}")
                estimated_total_time = 0
                existing_files = 0
                total_subsystem_lines = 0
        
        print(f"\n=== 抽样测试总结 ===")
        print(f"测试文件数: {len(sample_results)}")
        print(f"总处理时间: {total_duration:.1f} 秒")
        print(f"总处理行数: {total_lines:,}")
        print(f"平均处理速度: {avg_lines_per_second:.0f} 行/秒")
        print(f"总检测结果: {total_detections}")
        
        if estimated_total_time > 0:
            print(f"\n=== 整个子系统估算 ===")
            print(f"子系统存在文件: {existing_files}/{access_info['file_count']}")
            print(f"子系统总行数: {total_subsystem_lines:,}")
            print(f"估算总处理时间: {estimated_total_time:.0f} 秒 ({estimated_total_time/60:.1f} 分钟)")
            
            if estimated_total_time > 3600:
                print(f"⚠️  预估处理时间超过1小时！建议使用并行处理或增加超时限制")
        
        return {
            'subsystem': subsystem,
            'access_info': access_info,
            'sample_results': sample_results,
            'summary': {
                'total_duration': total_duration,
                'total_lines': total_lines,
                'avg_lines_per_second': avg_lines_per_second,
                'total_detections': total_detections,
                'estimated_total_time': estimated_total_time,
                'existing_files': existing_files,
                'total_subsystem_lines': total_subsystem_lines
            }
        }

def main():
    parser = argparse.ArgumentParser(description='Coccinelle性能测试工具')
    parser.add_argument('--db', required=True, help='数据库文件路径')
    parser.add_argument('--source', required=True, help='Linux源码根目录')
    parser.add_argument('--file', help='测试单个文件 (如: mm/memcontrol.c)')
    parser.add_argument('--subsystem', help='测试子系统 (如: mm)')
    parser.add_argument('--sample-count', type=int, default=10, help='子系统抽样文件数量')
    parser.add_argument('--timeout', type=int, default=300, help='单文件超时时间(秒)')
    parser.add_argument('--output', help='输出结果文件')
    
    args = parser.parse_args()
    
    try:
        tester = CoccinellePerformanceTester(args.db, args.source)
        
        results = {}
        
        if args.file:
            result = tester.test_single_file(args.file, args.timeout)
            if result:
                results['single_file'] = result
        
        if args.subsystem:
            result = tester.test_subsystem_sample(args.subsystem, args.sample_count, args.timeout)
            if result:
                results['subsystem_sample'] = result
        
        if not args.file and not args.subsystem:
            print("请指定 --file 或 --subsystem 参数")
            return 1
        
        if args.output and results:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n结果已保存到: {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
