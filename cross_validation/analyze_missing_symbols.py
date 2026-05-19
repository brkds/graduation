#!/usr/bin/env python3
"""
分析未被数据库覆盖的nm符号
详细分析每个未覆盖符号的特征和可能原因
"""

import json
import os
import re
from pathlib import Path
from collections import defaultdict, Counter
import argparse

class MissingSymbolAnalyzer:
    def __init__(self, groundtruth_dir="groundtruth_full", 
                 database_export_dir="database_export_full",
                 output_dir="missing_symbol_analysis"):
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
        """标准化文件路径"""
        if not path:
            return ""
        
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
    
    def extract_symbols(self):
        """提取nm和数据库的符号数据"""
        print("正在提取符号数据...")
        
        # 提取nm符号
        nm_file = self.groundtruth_dir / 'nm_symbols.json'
        nm_symbols = self.load_json_file(nm_file)
        
        nm_data = {
            'functions': {},  # name -> symbol_info
            'variables': {}   # name -> symbol_info
        }
        
        for symbol in nm_symbols:
            name = symbol.get('name', '')
            kind = symbol.get('kind', '')
            file_path = self.normalize_file_path(symbol.get('file', ''))
            
            if not name or not file_path:
                continue
            
            symbol_info = {
                'name': name,
                'file': file_path,
                'type': symbol.get('type', ''),
                'module': symbol.get('module', ''),
                'signature': f"{name}@{file_path}"
            }
                
            if kind == 'function':
                nm_data['functions'][f"{name}@{file_path}"] = symbol_info
            elif kind == 'variable':
                nm_data['variables'][f"{name}@{file_path}"] = symbol_info
        
        # 提取数据库符号
        db_signatures = set()
        
        # 提取函数
        func_file = self.database_export_dir / 'functions.json'
        if func_file.exists():
            functions = self.load_json_file(func_file)
            for func in functions:
                name = func.get('name', '')
                file_path = self.normalize_file_path(func.get('file_path', ''))
                if name and file_path:
                    db_signatures.add(f"{name}@{file_path}")
        
        # 提取变量
        var_file = self.database_export_dir / 'global_variables.json'
        if var_file.exists():
            variables = self.load_json_file(var_file)
            for var in variables:
                name = var.get('name', '')
                file_path = self.normalize_file_path(var.get('file_path', ''))
                if name and file_path:
                    db_signatures.add(f"{name}@{file_path}")
        
        print(f"nm函数: {len(nm_data['functions'])}, nm变量: {len(nm_data['variables'])}")
        print(f"数据库符号签名: {len(db_signatures)}")
        
        return nm_data, db_signatures
    
    def classify_symbol_pattern(self, symbol_name):
        """根据符号名称特征分类"""
        categories = []
        
        # 编译器优化产物
        if any(suffix in symbol_name for suffix in ['.cold', '.part.', '.constprop.', '.isra.', '.lto_priv.']):
            categories.append('compiler_optimization')
        
        # 调试符号
        if any(pattern in symbol_name for pattern in ['trace_', 'debug_', '__debug', '_trace', 'ftrace_']):
            categories.append('debug_symbols')
        
        # 系统调用相关
        if any(pattern in symbol_name for pattern in ['__ia32_sys_', '__do_sys_', '__x64_sys_', 'compat_sys_', 'sys_ni_']):
            categories.append('syscall_related')
        
        # 内核基础设施
        if any(pattern in symbol_name for pattern in ['__export_symbol_', '__kstrtab_', '__ksymtab_', '__param_']):
            categories.append('kernel_infrastructure')
        
        # 架构相关
        if any(pattern in symbol_name for pattern in ['arch_', 'x86_', '__arch', 'acpi_', 'apic_']):
            categories.append('architecture_specific')
        
        # 驱动相关
        if any(pattern in symbol_name for pattern in ['pci_', 'usb_', 'i915_', 'driver_']):
            categories.append('driver_related')
        
        # 网络相关
        if any(pattern in symbol_name for pattern in ['tcp_', 'udp_', 'ip_', 'net_', 'sk_', 'skb_']):
            categories.append('network_related')
        
        # 内存管理
        if any(pattern in symbol_name for pattern in ['mm_', 'page_', 'mem_', 'alloc_', 'free_', 'kmem_']):
            categories.append('memory_management')
        
        # 锁和同步
        if any(pattern in symbol_name for pattern in ['_lock', '_mutex', '_sem', '_wait', '_completion']):
            categories.append('synchronization')
        
        # 文件系统
        if any(pattern in symbol_name for pattern in ['vfs_', 'ext4_', 'fs_', 'file_', 'inode_']):
            categories.append('filesystem')
        
        # 如果没有明确分类，标记为其他
        if not categories:
            categories.append('other')
        
        return categories
    
    def analyze_file_patterns(self, missing_symbols):
        """分析文件路径模式"""
        file_patterns = defaultdict(list)
        module_counts = Counter()
        
        for symbol_info in missing_symbols:
            file_path = symbol_info['file']
            module = file_path.split('/')[0] if '/' in file_path else 'root'
            module_counts[module] += 1
            file_patterns[module].append(symbol_info)
        
        return dict(file_patterns), dict(module_counts)
    
    def find_potential_matches(self, missing_symbols, db_signatures):
        """查找可能的匹配（名称相同但文件不同）"""
        potential_matches = []
        
        for symbol_info in missing_symbols:
            symbol_name = symbol_info['name']
            
            # 查找名称相同但文件不同的符号
            name_matches = []
            for db_sig in db_signatures:
                if db_sig.startswith(f"{symbol_name}@"):
                    db_file = db_sig.split('@', 1)[1]
                    name_matches.append(db_file)
            
            if name_matches:
                potential_matches.append({
                    'missing_symbol': symbol_info,
                    'potential_files': name_matches[:5]  # 限制显示前5个
                })
        
        return potential_matches
    
    def analyze_missing_symbols(self):
        """分析未覆盖的符号"""
        print("开始分析未覆盖的符号...")
        
        # 提取数据
        nm_data, db_signatures = self.extract_symbols()
        
        # 找出未覆盖的符号
        missing_functions = []
        missing_variables = []
        
        for signature, symbol_info in nm_data['functions'].items():
            if signature not in db_signatures:
                missing_functions.append(symbol_info)
        
        for signature, symbol_info in nm_data['variables'].items():
            if signature not in db_signatures:
                missing_variables.append(symbol_info)
        
        print(f"未覆盖函数: {len(missing_functions)}")
        print(f"未覆盖变量: {len(missing_variables)}")
        
        # 分析函数
        func_analysis = self.analyze_symbol_category(missing_functions, "functions")
        
        # 分析变量
        var_analysis = self.analyze_symbol_category(missing_variables, "variables")
        
        # 查找潜在匹配
        func_potential = self.find_potential_matches(missing_functions, db_signatures)
        var_potential = self.find_potential_matches(missing_variables, db_signatures)
        
        # 生成报告
        self.generate_detailed_report(
            missing_functions, missing_variables,
            func_analysis, var_analysis,
            func_potential, var_potential
        )
        
        # 保存详细数据
        self.save_detailed_data(missing_functions, missing_variables)
        
        return {
            'missing_functions': len(missing_functions),
            'missing_variables': len(missing_variables),
            'function_analysis': func_analysis,
            'variable_analysis': var_analysis
        }
    
    def analyze_symbol_category(self, missing_symbols, symbol_type):
        """分析符号类别"""
        print(f"分析{symbol_type}分类...")
        
        category_counts = Counter()
        symbol_type_counts = Counter()
        file_patterns, module_counts = self.analyze_file_patterns(missing_symbols)
        
        for symbol_info in missing_symbols:
            # 分类符号
            categories = self.classify_symbol_pattern(symbol_info['name'])
            for category in categories:
                category_counts[category] += 1
            
            # 统计符号类型
            symbol_type_counts[symbol_info.get('type', 'unknown')] += 1
        
        return {
            'total_count': len(missing_symbols),
            'category_distribution': dict(category_counts),
            'symbol_type_distribution': dict(symbol_type_counts),
            'module_distribution': module_counts,
            'file_patterns': file_patterns
        }
    
    def generate_detailed_report(self, missing_functions, missing_variables, 
                               func_analysis, var_analysis, func_potential, var_potential):
        """生成详细的分析报告"""
        report = f"""
# 未覆盖符号详细分析报告

## 概览

### 未覆盖统计
- **未覆盖函数**: {len(missing_functions)}个
- **未覆盖变量**: {len(missing_variables)}个
- **总计**: {len(missing_functions) + len(missing_variables)}个

## 函数分析

### 分类分布
"""
        
        for category, count in sorted(func_analysis['category_distribution'].items(), key=lambda x: x[1], reverse=True):
            percentage = count / func_analysis['total_count'] * 100
            report += f"- **{category}**: {count}个 ({percentage:.1f}%)\n"
        
        report += f"""
### 符号类型分布
"""
        for sym_type, count in sorted(func_analysis['symbol_type_distribution'].items(), key=lambda x: x[1], reverse=True):
            percentage = count / func_analysis['total_count'] * 100
            report += f"- **{sym_type}**: {count}个 ({percentage:.1f}%)\n"
        
        report += f"""
### 模块分布（前10）
"""
        for module, count in sorted(func_analysis['module_distribution'].items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = count / func_analysis['total_count'] * 100
            report += f"- **{module}**: {count}个 ({percentage:.1f}%)\n"
        
        report += f"""

## 变量分析

### 分类分布
"""
        
        for category, count in sorted(var_analysis['category_distribution'].items(), key=lambda x: x[1], reverse=True):
            percentage = count / var_analysis['total_count'] * 100
            report += f"- **{category}**: {count}个 ({percentage:.1f}%)\n"
        
        report += f"""
### 符号类型分布
"""
        for sym_type, count in sorted(var_analysis['symbol_type_distribution'].items(), key=lambda x: x[1], reverse=True):
            percentage = count / var_analysis['total_count'] * 100
            report += f"- **{sym_type}**: {count}个 ({percentage:.1f}%)\n"
        
        report += f"""
### 模块分布（前10）
"""
        for module, count in sorted(var_analysis['module_distribution'].items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = count / var_analysis['total_count'] * 100
            report += f"- **{module}**: {count}个 ({percentage:.1f}%)\n"
        
        report += f"""

## 潜在匹配分析

### 函数潜在匹配
找到 {len(func_potential)} 个函数可能存在名称匹配但文件路径不同的情况。

### 变量潜在匹配  
找到 {len(var_potential)} 个变量可能存在名称匹配但文件路径不同的情况。

## 主要原因分析

基于符号特征分析，未覆盖的主要原因：

1. **编译器优化产物**: 包含.cold、.part.等后缀的函数，这些是编译器优化生成的代码
2. **调试符号**: trace_、debug_等调试相关符号
3. **系统调用包装器**: __ia32_sys_、__x64_sys_等系统调用相关符号
4. **内核基础设施**: 导出符号、参数表等内核内部机制
5. **架构特定代码**: x86、ACPI等平台相关实现
6. **条件编译差异**: 某些配置选项下才编译的代码

## 建议

1. **改进AST分析**: 增强对编译器优化产物的识别能力
2. **配置对齐**: 确保AST分析和编译配置一致
3. **符号过滤优化**: 进一步完善符号过滤逻辑
4. **路径匹配改进**: 处理文件路径不一致的问题

---
*报告生成时间: {self.get_timestamp()}*
"""
        
        # 保存报告
        with open(self.output_dir / 'missing_symbol_analysis_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"详细分析报告已保存到: {self.output_dir / 'missing_symbol_analysis_report.md'}")
    
    def save_detailed_data(self, missing_functions, missing_variables):
        """保存详细的未覆盖符号数据"""
        # 保存未覆盖函数详细数据
        func_data = []
        for symbol in missing_functions:
            categories = self.classify_symbol_pattern(symbol['name'])
            func_data.append({
                'name': symbol['name'],
                'file': symbol['file'],
                'type': symbol['type'],
                'module': symbol.get('module', ''),
                'categories': categories,
                'signature': symbol['signature']
            })
        
        with open(self.output_dir / 'missing_functions_detailed.json', 'w', encoding='utf-8') as f:
            json.dump(func_data, f, indent=2, ensure_ascii=False)
        
        # 保存未覆盖变量详细数据
        var_data = []
        for symbol in missing_variables:
            categories = self.classify_symbol_pattern(symbol['name'])
            var_data.append({
                'name': symbol['name'],
                'file': symbol['file'],
                'type': symbol['type'],
                'module': symbol.get('module', ''),
                'categories': categories,
                'signature': symbol['signature']
            })
        
        with open(self.output_dir / 'missing_variables_detailed.json', 'w', encoding='utf-8') as f:
            json.dump(var_data, f, indent=2, ensure_ascii=False)
        
        print(f"详细数据已保存到: {self.output_dir}")
        print(f"  - missing_functions_detailed.json: {len(func_data)}个未覆盖函数")
        print(f"  - missing_variables_detailed.json: {len(var_data)}个未覆盖变量")
    
    def get_timestamp(self):
        """获取当前时间戳"""
        import time
        return time.strftime("%Y-%m-%d %H:%M:%S")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="分析未覆盖符号的详细原因")
    parser.add_argument("--groundtruth_dir", type=str, default="groundtruth_full", help="基准数据目录")
    parser.add_argument("--database_export_dir", type=str, default="database_export_full", help="数据库导出目录")
    parser.add_argument("--output_dir", type=str, default="missing_symbol_analysis", help="输出目录")
    args = parser.parse_args()
    
    analyzer = MissingSymbolAnalyzer(args.groundtruth_dir, args.database_export_dir, args.output_dir)
    results = analyzer.analyze_missing_symbols()
    
    print("\n=== 分析完成 ===")
    print(f"未覆盖函数: {results['missing_functions']}")
    print(f"未覆盖变量: {results['missing_variables']}") 