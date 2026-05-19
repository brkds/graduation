#!/usr/bin/env python3
"""
A script to generate groundtruth data from Linux kernel object files using nm.
支持分模块处理以避免内存占用过高
"""

import argparse
import subprocess
import json
import traceback
import time
from pathlib import Path
from collections import defaultdict

class GroundTruthGenerator:
    def __init__(self, linux_src_path="../testdata/linux_full/linux-6.6", output_dir="groundtruth", filter_modules=None, modular_processing=False):
        self.linux_src_path = Path(linux_src_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.filter_modules = filter_modules or []  # Module filter list
        self.modular_processing = modular_processing  # 是否使用分模块处理
        
        # 分模块处理相关
        if self.modular_processing:
            self.modules_dir = self.output_dir / "modules"
            self.modules_dir.mkdir(exist_ok=True)
            self.log_file = self.output_dir / "generation_log.txt"
        
    def log_message(self, message):
        """记录日志信息（仅在分模块模式下使用）"""
        if not self.modular_processing:
            print(message)
            return
            
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
            f.flush()
        
    def should_include_file(self, file_path):
        """Check if a file should be included based on module filters"""
        if not self.filter_modules:
            return True
        
        try:
            rel_path = file_path.relative_to(self.linux_src_path)
            str_path = str(rel_path)
            
            for module in self.filter_modules:
                if str_path.startswith(module):
                    return True
            return False
        except ValueError:
            return False

    def should_filter_variable(self, symbol_name):
        """统一的符号过滤逻辑 - 过滤编译器生成和内部符号"""
        if not symbol_name:
            return True
            
        # 编译器生成的符号模式
        compiler_patterns = [
            '__key', '__already_done', '_rs', '__warned', '__once',
            '__kstrtab_', '__kstrtabns_', '__ksymtab_', '__kcrctab_',
            '__UNIQUE_ID_', '__addressable_', '__export_symbol_',
            '__param_', '__module_', 'descriptor.', '__initcall_',
            '__SCT__tp_func_', '__traceiter_', '__probestub_',
            '__ia32_sys_', '__do_sys_', '__x64_sys_', 'sys_ni_',
            '__se_sys_', '__weak_', '__always_inline_',
            '.LCPI', '.L__const', '__const', '__stack_chk',
            '__ubsan_', '__asan_', '__kasan_'
        ]
        
        # 调试和跟踪符号
        debug_patterns = [
            'TRACE_SYSTEM_', 'trace_event_', 'event_class_', 'event_', 
            'print_fmt_', 'str__', '_trace_system_name', 'trace_raw_output_',
            'perf_trace_', 'trace_event_fields_', 'trace_event_type_funcs_',
            '__tpstrtab_', '__SCT__', '__SCK__', '__probe', '__trace',
            '__tracepoint_', '__event_', 'ftrace_', '__bpf_trace_',
            '_tpstrtab_', '__tpstrtab_', '__tpgfp_'
        ]
        
        # 内核基础设施符号
        kernel_patterns = [
            'boot_', 'early_', '_lock', '_mutex', '_sem', '_completion',
            '_wait_queue', '_workqueue', '_timer', '_tasklet',
            '__percpu_', '__initdata_', '__exitdata_', '__ro_after_init',
            '_syscall_', '__syscall_', 'compat_sys_',
            'init_', 'exit_', 'resume'
        ]
        
        # 调试和基础设施符号
        infra_patterns = [
            '_fops', '_sops', '_op', '_ops', '_attr', '_attrs', '_ktype', 
            '_group', '_groups', 'dev_attr_', 'device_attribute_',
            'driver_attribute_', 'bus_attribute_', 'class_attribute_',
            'shepherd', 'slot_virt', 'swp_slots', 'bdp_ratelimits'
        ]
        
        # 内存管理和调试专用符号
        memory_debug_patterns = [
            'kmsan_', 'kasan_', 'kfence_', '__msan_', 'damon_',
            '_debug_', '_test_', 'debug_', 'test_',
            'kmemleak_', 'slub_debug'
        ]
        
        # 编译器优化产物
        optimization_patterns = [
            '.cold', '.part.', '.constprop.', '.isra.', '.lto_priv.'
        ]
        
        all_patterns = (compiler_patterns + debug_patterns + kernel_patterns + 
                       infra_patterns + memory_debug_patterns + optimization_patterns)
        
        # 检查模式匹配
        for pattern in all_patterns:
            if pattern in symbol_name:
                return True
        
        # 检查特殊模式
        if (symbol_name.startswith('_') or 
            symbol_name.endswith('_lock') or
            symbol_name.endswith('_mutex') or
            symbol_name.endswith('_work') or
            symbol_name.endswith('_ops') or
            symbol_name.endswith('_fops') or
            '.' in symbol_name or  # LLVM generated symbols
            symbol_name.startswith('srcu_')):
            return True
            
        return False
        
    def run_command(self, cmd, cwd=None):
        """Run a shell command and return its output"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
            if result.returncode != 0:
                print(f"Warning: Command failed '{cmd}': {result.stderr}")
                return ""
            return result.stdout
        except Exception as e:
            print(f"Error: Failed to execute command '{cmd}': {e}")
            return ""
    
    def discover_kernel_modules(self):
        """发现Linux内核的主要模块目录（分模块模式使用）"""
        modules = []
        
        # 预定义的主要内核模块目录
        known_modules = [
            'mm', 'fs', 'net', 'drivers', 'kernel', 'arch', 'lib', 'security',
            'sound', 'crypto', 'block', 'ipc', 'init', 'virt'
        ]
        
        for module in known_modules:
            module_path = self.linux_src_path / module
            if module_path.exists() and module_path.is_dir():
                # 检查是否有.o文件
                o_files = list(module_path.rglob("*.o"))
                if o_files:
                    modules.append({
                        'name': module,
                        'path': module_path,
                        'object_files': len(o_files)
                    })
        
        # 查找其他可能的模块目录
        for item in self.linux_src_path.iterdir():
            if (item.is_dir() and 
                item.name not in known_modules and 
                not item.name.startswith('.') and
                item.name not in ['Documentation', 'scripts', 'tools']):
                o_files = list(item.rglob("*.o"))
                if o_files:
                    modules.append({
                        'name': item.name,
                        'path': item,
                        'object_files': len(o_files)
                    })
        
        # 按.o文件数量排序
        modules.sort(key=lambda x: x['object_files'])
        
        self.log_message(f"发现 {len(modules)} 个内核模块:")
        for module in modules:
            self.log_message(f"  {module['name']}: {module['object_files']} 个目标文件")
        
        return modules
    
    def find_object_files(self):
        """Find all .o object files"""
        o_files = []
        
        if self.filter_modules:
            for module in self.filter_modules:
                module_path = self.linux_src_path / module
                if not module_path.exists():
                    print(f"Warning: Module path {module_path} does not exist, skipping")
                    continue
                o_files.extend(module_path.glob('**/*.o'))
        else:
            o_files.extend(self.linux_src_path.glob('**/*.o'))
        
        return o_files
    
    def get_symbol_kind(self, o_file, symbol_name, symbol_type, objdump_cache=None):
        """Determine symbol kind (function or variable) based on type and section"""
        if symbol_type in ('T', 't'):
            return 'function'
        if symbol_type in ('D', 'B', 'R', 'd', 'b', 'r', 'V', 'v'):
            return 'variable'
        if symbol_type in ('W', 'w'):
            if objdump_cache is None:
                try:
                    objdump_cache = self.run_command(f"objdump -t {o_file}").strip().split('\n')
                except Exception as e:
                    print(f"Error checking section info for {o_file}: {e}")
                    return 'function'  # Default
            for line in objdump_cache:
                if symbol_name in line and ' ' in line:
                    if '.text' in line:
                        return 'function'
                    elif '.data' in line or '.bss' in line or '.rodata' in line:
                        return 'variable'
            print(f"Warning: No section info found for {symbol_type} {symbol_name} in {o_file}, defaulting to function")
            return 'function'
        print(f"Warning: Unknown symbol type {symbol_type} {symbol_name} in {o_file}, ignored")
        return None

    def process_single_module(self, module_info):
        """处理单个模块的nm符号提取（分模块模式使用）"""
        module_name = module_info['name']
        module_path = module_info['path']
        
        self.log_message(f"开始处理模块: {module_name}")
        
        # 查找模块中的所有.o文件
        o_files = list(module_path.rglob("*.o"))
        
        # 过滤掉特殊目录
        excluded_dirs = {'.git', 'Documentation', 'scripts', 'tools'}
        filtered_files = []
        
        for o_file in o_files:
            if not any(excluded_dir in o_file.parts for excluded_dir in excluded_dirs):
                filtered_files.append(o_file)
        
        self.log_message(f"  模块 {module_name}: 找到 {len(filtered_files)} 个目标文件")
        
        symbols = []
        filtered_count = 0
        processed_files = 0
        
        for i, o_file in enumerate(filtered_files):
            if i % 50 == 0:
                self.log_message(f"  {module_name}: 进度 {i}/{len(filtered_files)} ({i/len(filtered_files)*100:.1f}%)")
            
            try:
                nm_output = self.run_command(f"nm {o_file}")
                if not nm_output.strip():
                    continue
                
                objdump_cache = None
                for line in nm_output.strip().split('\n'):
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 3:
                        addr, symbol_type, symbol_name = parts[0], parts[1], parts[2]
                        
                        # 只分析相关的符号类型
                        if symbol_type in ('T', 't', 'D', 'B', 'R', 'd', 'b', 'r', 'W', 'w', 'V', 'v'):
                            # 基础过滤
                            if any(suffix in symbol_name for suffix in ['__UNIQUE_ID_', '__SCK__', '__addressable_']):
                                continue
                            
                            kind = self.get_symbol_kind(o_file, symbol_name, symbol_type, objdump_cache)
                            if kind:
                                # 应用统一过滤
                                if self.should_filter_variable(symbol_name):
                                    filtered_count += 1
                                    continue
                                    
                                symbols.append({
                                    'name': symbol_name,
                                    'type': symbol_type,
                                    'file': str(o_file),
                                    'tool': 'nm',
                                    'kind': kind,
                                    'module': module_name
                                })
                
                processed_files += 1
                
            except Exception as e:
                self.log_message(f"  错误处理文件 {o_file}: {e}")
                continue
        
        # 保存模块符号到单独文件
        module_output_file = self.modules_dir / f"{module_name}_symbols.json"
        with open(module_output_file, 'w', encoding='utf-8') as f:
            json.dump(symbols, f, indent=2, ensure_ascii=False)
        
        # 生成模块统计
        functions = sum(1 for s in symbols if s['kind'] == 'function')
        variables = sum(1 for s in symbols if s['kind'] == 'variable')
        
        module_stats = {
            'module_name': module_name,
            'total_symbols': len(symbols),
            'functions': functions,
            'variables': variables,
            'filtered_symbols': filtered_count,
            'processed_files': processed_files,
            'total_object_files': len(filtered_files)
        }
        
        # 保存模块统计
        stats_file = self.modules_dir / f"{module_name}_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(module_stats, f, indent=2, ensure_ascii=False)
        
        self.log_message(f"  模块 {module_name} 完成:")
        self.log_message(f"    符号总数: {len(symbols)} (函数: {functions}, 变量: {variables})")
        self.log_message(f"    过滤符号: {filtered_count}")
        
        # 清理内存
        del symbols
        
        return module_stats

    def extract_with_nm(self):
        """Extract function and variable symbols using nm"""
        print("Extracting symbols with nm...")
        if self.filter_modules:
            print(f"  Module filters: {', '.join(self.filter_modules)}")
        
        o_files = self.find_object_files()
        symbols = []
        filtered_count = 0
        
        print(f"Found {len(o_files)} object files")
        
        for o_file in o_files:
            if not self.should_include_file(o_file):
                continue
            try:
                nm_output = self.run_command(f"nm {o_file}")
                if not nm_output.strip():
                    print(f"Warning: Empty nm output for {o_file}, verify file compilation or contents")
                    continue
                objdump_cache = None
                for line in nm_output.strip().split('\n'):
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 3:
                        addr, symbol_type, symbol_name = parts[0], parts[1], parts[2]
                        if symbol_type in ('T', 't', 'D', 'B', 'R', 'd', 'b', 'r', 'W', 'w', 'V', 'v'):
                            if any(suffix in symbol_name for suffix in ['__UNIQUE_ID_', '__SCK__', '__addressable_']):
                                continue
                            
                            kind = self.get_symbol_kind(o_file, symbol_name, symbol_type, objdump_cache)
                            if kind:
                                # Apply unified filtering for both functions and variables
                                if self.should_filter_variable(symbol_name):
                                    filtered_count += 1
                                    continue
                                    
                                symbols.append({
                                    'name': symbol_name,
                                    'type': symbol_type,
                                    'file': str(o_file),
                                    'tool': 'nm',
                                    'kind': kind
                                })
                        # else:
                        #     print(f"Warning: Ignoring non-target symbol type {symbol_type} {symbol_name} in {o_file}")
                    # elif len(parts) == 2:
                    #     symbol_type, symbol_name = parts[0], parts[1]
                    #     print(f"Warning: {symbol_type} {symbol_name} in {o_file} is a two-field symbol (possibly undefined), ignored")
            except Exception as e:
                print(f"Error processing file {o_file}: {e}\nTraceback: {traceback.format_exc()}")
                continue
        
        output_file = self.output_dir / 'nm_symbols.json'
        with open(output_file, 'w') as f:
            json.dump(symbols, f, indent=2)
        
        print(f"Extracted {len(symbols)} symbols with nm (filtered {filtered_count} internal symbols), saved to {output_file}")
        return symbols
    
    def merge_module_results(self):
        """合并所有模块的结果（分模块模式使用）"""
        self.log_message("开始合并模块结果...")
        
        all_symbols = []
        all_stats = []
        
        # 收集所有模块的符号和统计
        for symbol_file in self.modules_dir.glob("*_symbols.json"):
            try:
                with open(symbol_file, 'r', encoding='utf-8') as f:
                    module_symbols = json.load(f)
                    all_symbols.extend(module_symbols)
                
                self.log_message(f"  合并模块: {symbol_file.stem} ({len(module_symbols)} 个符号)")
            except Exception as e:
                self.log_message(f"  错误合并文件 {symbol_file}: {e}")
        
        # 收集统计信息
        for stats_file in self.modules_dir.glob("*_stats.json"):
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    module_stats = json.load(f)
                    all_stats.append(module_stats)
            except Exception as e:
                self.log_message(f"  错误读取统计文件 {stats_file}: {e}")
        
        # 保存合并后的全量符号文件
        output_file = self.output_dir / 'nm_symbols.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_symbols, f, indent=2, ensure_ascii=False)
        
        # 生成全量统计
        total_functions = sum(1 for s in all_symbols if s['kind'] == 'function')
        total_variables = sum(1 for s in all_symbols if s['kind'] == 'variable')
        total_filtered = sum(stats['filtered_symbols'] for stats in all_stats)
        
        # 模块分布统计
        module_distribution = defaultdict(int)
        for symbol in all_symbols:
            module_distribution[symbol.get('module', 'unknown')] += 1
        
        summary = {
            'total_nm_symbols': len(all_symbols),
            'num_functions': total_functions,
            'num_variables': total_variables,
            'source_path': str(self.linux_src_path),
            'filter_modules': self.filter_modules,
            'object_files_found': sum(stats['total_object_files'] for stats in all_stats),
            'total_filtered': total_filtered,
            'total_modules': len(all_stats),
            'module_distribution': dict(module_distribution),
            'generation_completed': time.strftime("%Y-%m-%d %H:%M:%S"),
            'modular_processing': True
        }
        
        # 保存统计
        with open(self.output_dir / 'summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.log_message("全量合并完成!")
        self.log_message(f"  全量符号文件: {output_file}")
        self.log_message(f"  总符号数: {len(all_symbols)} (函数: {total_functions}, 变量: {total_variables})")
        self.log_message(f"  过滤符号数: {total_filtered}")
        self.log_message(f"  处理模块数: {len(all_stats)}")
        
        return all_symbols
    
    def generate_all_modular(self):
        """使用分模块处理生成全量nm符号"""
        start_time = time.time()
        self.log_message("开始分模块nm符号生成...")
        
        # 发现模块
        modules = self.discover_kernel_modules()
        
        if not modules:
            self.log_message("错误: 未发现任何内核模块")
            return None
        
        # 处理每个模块
        completed_modules = 0
        for i, module_info in enumerate(modules):
            self.log_message(f"处理模块 {i+1}/{len(modules)}: {module_info['name']}")
            
            try:
                module_stats = self.process_single_module(module_info)
                completed_modules += 1
                
                # 定期输出进度
                progress = (i + 1) / len(modules) * 100
                elapsed = time.time() - start_time
                self.log_message(f"整体进度: {progress:.1f}% (已完成 {completed_modules} 个模块, 用时 {elapsed:.1f}s)")
                
            except Exception as e:
                self.log_message(f"错误处理模块 {module_info['name']}: {e}")
                self.log_message(f"跟踪: {traceback.format_exc()}")
                continue
        
        # 合并结果
        all_symbols = self.merge_module_results()
        
        total_time = time.time() - start_time
        self.log_message(f"全量生成完成! 总用时: {total_time:.1f}s")
        
        return {'nm_symbols': all_symbols}
    
    def generate_all(self):
        """Generate all groundtruth data using nm"""
        if self.modular_processing:
            return self.generate_all_modular()
            
        if self.filter_modules:
            print(f"Generating groundtruth data for {self.linux_src_path} (module filters: {', '.join(self.filter_modules)})...")
        else:
            print(f"Generating groundtruth data for {self.linux_src_path}...")
        
        results = {
            'nm_symbols': self.extract_with_nm(),
        }
        
        # 统计函数和变量的数量
        num_functions = sum(1 for s in results['nm_symbols'] if s.get('kind') == 'function')
        num_variables = sum(1 for s in results['nm_symbols'] if s.get('kind') == 'variable')
        summary = {
            'total_nm_symbols': len(results['nm_symbols']),
            'num_functions': num_functions,
            'num_variables': num_variables,
            'source_path': str(self.linux_src_path),
            'filter_modules': self.filter_modules,
            'object_files_found': len(self.find_object_files()),
            'modular_processing': False
        }
        
        with open(self.output_dir / 'summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("\nGroundtruth data generation completed!")
        print(f"Results saved to: {self.output_dir}")
        print(f"Summary: {summary}")
        
        return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate groundtruth data from Linux kernel object files using nm")
    parser.add_argument('modules', nargs='*', default=[], help="Kernel modules to analyze (e.g., mm fs), default is all modules")
    parser.add_argument('--output-dir', default="groundtruth_full", help="Output directory for full scale generation")
    parser.add_argument('--modular', action='store_true', help="Use modular processing to avoid memory issues")
    args = parser.parse_args()
    
    # 根据参数确定输出目录和处理模式
    output_dir = "groundtruth_full" if args.modular else "groundtruth"
    if args.output_dir != "groundtruth_full":
        output_dir = args.output_dir
    
    generator = GroundTruthGenerator(
        filter_modules=args.modules if args.modules else None,
        output_dir=output_dir,
        modular_processing=args.modular
    )
    generator.generate_all()