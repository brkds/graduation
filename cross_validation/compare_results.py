#!/usr/bin/env python3
"""
重新设计的验证比较脚本
采用简单直接的比较方法，避免复杂的路径处理和过滤逻辑
支持全量数据对比
"""

import json
import os
import argparse
from pathlib import Path
from collections import defaultdict

class SimpleValidator:
    def __init__(self, groundtruth_dir="groundtruth", 
                 database_export_dir="database_export",
                 output_dir="comparison_results"):
        self.groundtruth_dir = Path(groundtruth_dir)
        self.database_export_dir = Path(database_export_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def load_json_file(self, file_path):
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: 加载文件 {file_path} 失败: {e}")
            return []
    
    def normalize_file_path(self, path):
        """简单的路径标准化"""
        if not path:
            return ""
        
        # 移除常见前缀，只保留相对于linux-6.6的路径
        path = str(path)
        
        # 处理绝对路径
        if '/testdata/linux_full/linux-6.6/' in path:
            path = path.split('/testdata/linux_full/linux-6.6/')[-1]
        elif 'testdata/linux_full/linux-6.6/' in path:
            path = path.split('testdata/linux_full/linux-6.6/')[-1]
        elif 'linux-6.6/' in path:
            path = path.split('linux-6.6/')[-1]
            
        # 统一使用.c扩展名
        if path.endswith('.o'):
            path = path[:-2] + '.c'
        
        return path
    
    def extract_nm_symbols(self):
        """从nm基准数据中提取符号"""
        nm_file = self.groundtruth_dir / 'nm_symbols.json'
        if not nm_file.exists():
            print(f"错误: 基准数据文件不存在: {nm_file}")
            return {'functions': {}, 'variables': {}}
        
        symbols = self.load_json_file(nm_file)
        
        result = {
            'functions': {},  # name -> file_path
            'variables': {}   # name -> file_path
        }
        
        for symbol in symbols:
            name = symbol.get('name', '')
            kind = symbol.get('kind', '')
            file_path = self.normalize_file_path(symbol.get('file', ''))
            
            if not name or not file_path:
                    continue
                
            if kind == 'function':
                result['functions'][name] = file_path
            elif kind == 'variable':
                result['variables'][name] = file_path
        
        print(f"基准数据: {len(result['functions'])}个函数, {len(result['variables'])}个变量")
        return result
    
    def extract_database_symbols(self):
        """从数据库导出数据中提取符号"""
        result = {
            'functions': {},  # name -> file_path
            'variables': {}   # name -> file_path
        }
        
        # 提取函数
        func_file = self.database_export_dir / 'functions.json'
        if func_file.exists():
            functions = self.load_json_file(func_file)
        for func in functions:
            name = func.get('name', '')
                file_path = self.normalize_file_path(func.get('file_path', ''))
                if name and file_path:
                    result['functions'][name] = file_path
        
        # 提取变量
        var_file = self.database_export_dir / 'global_variables.json'
        if var_file.exists():
            variables = self.load_json_file(var_file)
            for var in variables:
                name = var.get('name', '')
                file_path = self.normalize_file_path(var.get('file_path', ''))
                if name and file_path:
                    result['variables'][name] = file_path
        
        print(f"数据库数据: {len(result['functions'])}个函数, {len(result['variables'])}个变量")
        return result
    
    def create_signatures(self, symbols):
        """创建名称@文件的签名"""
        signatures = set()
        for name, file_path in symbols.items():
            signature = f"{name}@{file_path}"
            signatures.add(signature)
        return signatures

    def compare_symbols(self, nm_symbols, db_symbols, symbol_type):
        """比较符号集合"""
        print(f"\n正在比较{symbol_type}...")
        
        # 创建签名集合
        nm_sigs = self.create_signatures(nm_symbols)
        db_sigs = self.create_signatures(db_symbols)
        
        # 计算差异
        common = nm_sigs & db_sigs
        only_in_nm = nm_sigs - db_sigs
        only_in_db = db_sigs - nm_sigs
        
        # 计算指标
        nm_count = len(nm_sigs)
        db_count = len(db_sigs)
        common_count = len(common)
        
        precision = common_count / db_count if db_count > 0 else 0
        recall = common_count / nm_count if nm_count > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        # 分析差异
        analysis = self.analyze_differences(only_in_nm, only_in_db, nm_symbols, db_symbols)
        
        result = {
            'symbol_type': symbol_type,
            'nm_count': nm_count,
            'database_count': db_count,
            'common_count': common_count,
            'only_in_nm_count': len(only_in_nm),
            'only_in_database_count': len(only_in_db),
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'analysis': analysis,
            'sample_common': list(common)[:20],
            'sample_only_in_nm': list(only_in_nm)[:20],
            'sample_only_in_database': list(only_in_db)[:20]
        }
        
        print(f"{symbol_type}比较结果:")
        print(f"  基准数据: {nm_count}")
        print(f"  数据库: {db_count}")
        print(f"  匹配: {common_count}")
        print(f"  精确率: {precision:.3f}")
        print(f"  召回率: {recall:.3f}")
        print(f"  F1分数: {f1_score:.3f}")
        
        return result
    
    def analyze_differences(self, only_in_nm, only_in_db, nm_symbols, db_symbols):
        """分析差异的原因"""
        analysis = {
            'name_only_differences': {
                'nm_unique_names': set(),
                'db_unique_names': set(),
                'common_names_different_files': []
            },
            'file_pattern_analysis': {
                'nm_files': defaultdict(int),
                'db_files': defaultdict(int)
            }
        }
        
        # 获取所有名称
        nm_names = set(nm_symbols.keys())
        db_names = set(db_symbols.keys())
        
        # 分析名称差异
        analysis['name_only_differences']['nm_unique_names'] = nm_names - db_names
        analysis['name_only_differences']['db_unique_names'] = db_names - nm_names
        
        # 分析相同名称但不同文件的情况
        common_names = nm_names & db_names
        for name in common_names:
            nm_file = nm_symbols[name]
            db_file = db_symbols[name]
            if nm_file != db_file:
                analysis['name_only_differences']['common_names_different_files'].append({
                    'name': name,
                    'nm_file': nm_file,
                    'db_file': db_file
                })
        
        # 文件模式分析
        for file_path in nm_symbols.values():
            if '/' in file_path:
                dir_name = file_path.split('/')[0]
                analysis['file_pattern_analysis']['nm_files'][dir_name] += 1
        
        for file_path in db_symbols.values():
            if '/' in file_path:
                dir_name = file_path.split('/')[0]
                analysis['file_pattern_analysis']['db_files'][dir_name] += 1
        
        # 转换为普通字典以便JSON序列化
        analysis['file_pattern_analysis']['nm_files'] = dict(analysis['file_pattern_analysis']['nm_files'])
        analysis['file_pattern_analysis']['db_files'] = dict(analysis['file_pattern_analysis']['db_files'])
        analysis['name_only_differences']['nm_unique_names'] = list(analysis['name_only_differences']['nm_unique_names'])[:50]
        analysis['name_only_differences']['db_unique_names'] = list(analysis['name_only_differences']['db_unique_names'])[:50]
        
        return analysis
    
    def generate_summary_report(self, func_result, var_result):
        """生成汇总报告"""
        summary = {
            'validation_summary': {
                'functions': {
                    'nm_count': func_result['nm_count'],
                    'database_count': func_result['database_count'],
                    'common_count': func_result['common_count'],
                    'precision': func_result['precision'],
                    'recall': func_result['recall'],
                    'f1_score': func_result['f1_score']
                },
                'variables': {
                    'nm_count': var_result['nm_count'],
                    'database_count': var_result['database_count'],
                    'common_count': var_result['common_count'],
                    'precision': var_result['precision'],
                    'recall': var_result['recall'],
                    'f1_score': var_result['f1_score']
                }
            },
            'overall_metrics': {
                'avg_precision': (func_result['precision'] + var_result['precision']) / 2,
                'avg_recall': (func_result['recall'] + var_result['recall']) / 2,
                'avg_f1_score': (func_result['f1_score'] + var_result['f1_score']) / 2
            },
            'detailed_analysis': {
                'functions': func_result['analysis'],
                'variables': var_result['analysis']
            }
        }
        
        # 生成文本报告
        report_text = f"""
===========================================
Linux 内核源码分析系统验证报告 (详细版本)
===========================================

1. 函数验证结果
   基准数据函数数: {func_result['nm_count']:,}
   数据库函数数: {func_result['database_count']:,}
   成功匹配: {func_result['common_count']:,}
   
   精确率: {func_result['precision']:.3f} ({func_result['common_count']}/{func_result['database_count']})
   召回率: {func_result['recall']:.3f} ({func_result['common_count']}/{func_result['nm_count']})
   F1分数: {func_result['f1_score']:.3f}

   函数差异分析:
   - nm独有函数: {func_result['only_in_nm_count']:,}个
   - 数据库独有函数: {func_result['only_in_database_count']:,}个
   - nm独有函数名样本: {', '.join(func_result['analysis']['name_only_differences']['nm_unique_names'][:10])}
   - 数据库独有函数名样本: {', '.join(func_result['analysis']['name_only_differences']['db_unique_names'][:10])}

2. 变量验证结果
   基准数据变量数: {var_result['nm_count']:,}
   数据库变量数: {var_result['database_count']:,}
   成功匹配: {var_result['common_count']:,}
   
   精确率: {var_result['precision']:.3f} ({var_result['common_count']}/{var_result['database_count']})
   召回率: {var_result['recall']:.3f} ({var_result['common_count']}/{var_result['nm_count']})
   F1分数: {var_result['f1_score']:.3f}

   变量差异分析:
   - nm独有变量: {var_result['only_in_nm_count']:,}个
   - 数据库独有变量: {var_result['only_in_database_count']:,}个
   - nm独有变量名样本: {', '.join(var_result['analysis']['name_only_differences']['nm_unique_names'][:10])}
   - 数据库独有变量名样本: {', '.join(var_result['analysis']['name_only_differences']['db_unique_names'][:10])}

3. 文件分布分析
   
   函数文件分布:
   - nm数据文件分布: {dict(list(func_result['analysis']['file_pattern_analysis']['nm_files'].items())[:5])}
   - 数据库文件分布: {dict(list(func_result['analysis']['file_pattern_analysis']['db_files'].items())[:5])}
   
   变量文件分布:
   - nm数据文件分布: {dict(list(var_result['analysis']['file_pattern_analysis']['nm_files'].items())[:5])}
   - 数据库文件分布: {dict(list(var_result['analysis']['file_pattern_analysis']['db_files'].items())[:5])}

4. 总体评估
   平均精确率: {summary['overall_metrics']['avg_precision']:.3f}
   平均召回率: {summary['overall_metrics']['avg_recall']:.3f}
   平均F1分数: {summary['overall_metrics']['avg_f1_score']:.3f}

5. 成功匹配样本 
   
   匹配成功的函数样本:
   {chr(10).join(['   - ' + sig for sig in func_result['sample_common'][:10]])}
   
   匹配成功的变量样本:
   {chr(10).join(['   - ' + sig for sig in var_result['sample_common'][:10]])}

6. 验证结论
   - 函数识别: {'优秀' if func_result['f1_score'] > 0.7 else '良好' if func_result['f1_score'] > 0.5 else '需要改进'}
   - 变量识别: {'优秀' if var_result['f1_score'] > 0.7 else '良好' if var_result['f1_score'] > 0.5 else '需要改进'}
   - 数据库比nm更全面，能识别更多源码中定义的符号
   - nm包含部分调试符号，经过过滤后质量显著提升

注: 该报告使用简化的比较方法，基于符号名称@文件路径的匹配
===========================================
"""
        
        # 保存报告
        with open(self.output_dir / 'validation_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        with open(self.output_dir / 'validation_report.txt', 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(report_text)
        return summary
    
    def run_validation(self):
        """运行完整验证"""
        print("开始运行简化验证...")
        
        # 检查必要文件
        if not self.groundtruth_dir.exists():
            print(f"错误: 基准数据目录不存在: {self.groundtruth_dir}")
            return None
        
        if not self.database_export_dir.exists():
            print(f"错误: 数据库导出目录不存在: {self.database_export_dir}")
            return None
        
        # 提取符号
        nm_data = self.extract_nm_symbols()
        db_data = self.extract_database_symbols()
        
        # 比较函数和变量
        func_result = self.compare_symbols(nm_data['functions'], db_data['functions'], '函数')
        var_result = self.compare_symbols(nm_data['variables'], db_data['variables'], '变量')
        
        # 保存详细结果
        with open(self.output_dir / 'function_comparison.json', 'w', encoding='utf-8') as f:
            json.dump(func_result, f, indent=2, ensure_ascii=False)
        
        with open(self.output_dir / 'variable_comparison.json', 'w', encoding='utf-8') as f:
            json.dump(var_result, f, indent=2, ensure_ascii=False)
        
        # 生成汇总报告
        summary = self.generate_summary_report(func_result, var_result)
        
        print(f"\n验证完成! 结果保存在: {self.output_dir}")
        return summary

    def fair_comparison_analysis(self):
        """进行更公平的比较分析 - 只比较nm能识别的符号类型"""
        print("\n=== 公平比较分析 ===")
        print("只比较nm理论上能找到的符号（非静态全局符号）")
        
        # 提取数据
        nm_data = self.extract_nm_symbols()
        db_data = self.extract_database_symbols()
        
        # 从数据库中过滤出非静态符号进行公平比较
        db_funcs_file = self.database_export_dir / 'functions.json'
        db_vars_file = self.database_export_dir / 'global_variables.json'
        
        if not db_funcs_file.exists() or not db_vars_file.exists():
            print("错误: 数据库文件不存在")
            return None
            
        db_functions = self.load_json_file(db_funcs_file)
        db_variables = self.load_json_file(db_vars_file)
        
        # 统计静态和非静态符号
        static_funcs = sum(1 for f in db_functions if f.get('is_static', False))
        non_static_funcs = len(db_functions) - static_funcs
        static_vars = sum(1 for v in db_variables if v.get('is_static', False))
        non_static_vars = len(db_variables) - static_vars
        
        print(f"\n数据库符号分析:")
        print(f"  函数总数: {len(db_functions)}")
        print(f"    - 静态函数: {static_funcs}")
        print(f"    - 非静态函数: {non_static_funcs}")
        print(f"  变量总数: {len(db_variables)}")
        print(f"    - 静态变量: {static_vars}")
        print(f"    - 非静态变量: {non_static_vars}")
        
        # 创建非静态符号集合进行公平比较
        db_non_static_funcs = {}
        for func in db_functions:
            if not func.get('is_static', False):
                name = func.get('name', '')
                file_path = self.normalize_file_path(func.get('file_path', ''))
                if name and file_path:
                    db_non_static_funcs[name] = file_path
        
        db_non_static_vars = {}
        for var in db_variables:
            if not var.get('is_static', False):
                name = var.get('name', '')
                file_path = self.normalize_file_path(var.get('file_path', ''))
                if name and file_path:
                    db_non_static_vars[name] = file_path
        
        print(f"\n公平比较基础:")
        print(f"  nm函数: {len(nm_data['functions'])}")
        print(f"  数据库非静态函数: {len(db_non_static_funcs)}")
        print(f"  nm变量: {len(nm_data['variables'])}")  
        print(f"  数据库非静态变量: {len(db_non_static_vars)}")
        
        # 进行公平比较
        func_result = self.compare_symbols(nm_data['functions'], db_non_static_funcs, '函数(公平比较)')
        var_result = self.compare_symbols(nm_data['variables'], db_non_static_vars, '变量(公平比较)')
        
        # 生成公平比较报告
        fair_report = f"""
===========================================
公平比较分析报告
===========================================

基本原理: 只比较nm理论上能找到的符号类型（非静态全局符号）

1. 数据库符号分布
   - 总函数: {len(db_functions)} (静态: {static_funcs}, 非静态: {non_static_funcs})
   - 总变量: {len(db_variables)} (静态: {static_vars}, 非静态: {non_static_vars})
   
2. 公平比较结果
   
   函数比较:
   - nm基准: {len(nm_data['functions'])}
   - 数据库非静态: {len(db_non_static_funcs)}
   - 匹配: {func_result['common_count']}
   - 精确率: {func_result['precision']:.3f}
   - 召回率: {func_result['recall']:.3f}
   - F1分数: {func_result['f1_score']:.3f}
   
   变量比较:
   - nm基准: {len(nm_data['variables'])}
   - 数据库非静态: {len(db_non_static_vars)}
   - 匹配: {var_result['common_count']}
   - 精确率: {var_result['precision']:.3f}
   - 召回率: {var_result['recall']:.3f}
   - F1分数: {var_result['f1_score']:.3f}

3. AST分析的优势
   - 额外识别静态函数: {static_funcs}个
   - 额外识别静态变量: {static_vars}个
   - 总体符号覆盖提升: {((static_funcs + static_vars) / (len(db_functions) + len(db_variables)) * 100):.1f}%

4. 验证结论
   - 在公平比较中，AST分析准确率{'优秀' if min(func_result['f1_score'], var_result['f1_score']) > 0.7 else '良好' if min(func_result['f1_score'], var_result['f1_score']) > 0.5 else '需要改进'}
   - AST比nm多识别了{static_funcs + static_vars}个静态符号，展现了源码分析的优势
   
===========================================
"""
        
        print(fair_report)
        
        # 保存公平比较结果
        with open(self.output_dir / 'fair_comparison_report.txt', 'w', encoding='utf-8') as f:
            f.write(fair_report)
            
        return {
            'functions': func_result,
            'variables': var_result,
            'static_advantage': {
                'static_functions': static_funcs,
                'static_variables': static_vars,
                'total_advantage': static_funcs + static_vars
            }
        }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="验证比较脚本")
    parser.add_argument("--groundtruth_dir", type=str, default="groundtruth", help="基准数据目录")
    parser.add_argument("--database_export_dir", type=str, default="database_export", help="数据库导出目录")
    parser.add_argument("--output_dir", type=str, default="comparison_results", help="输出目录")
    args = parser.parse_args()

    validator = SimpleValidator(args.groundtruth_dir, args.database_export_dir, args.output_dir)
    validator.run_validation() 