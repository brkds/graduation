#!/usr/bin/env python3
"""
数据库导出脚本
从 full.db 中提取分析结果用于与基准数据对比
"""

import sqlite3
import json
from pathlib import Path
import argparse

class DatabaseExtractor:
    def __init__(self, db_path="full6.12.db", output_dir="cross_validation/database_export", filter_modules=None):
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.filter_modules = filter_modules or []  # 模块过滤列表
        
    def should_include_path(self, file_path):
        """判断文件路径是否应该被包含在分析中"""
        if not self.filter_modules or not file_path:
            return True
        
        # 标准化路径 - 处理各种可能的路径格式
        normalized_path = str(file_path)
        
        # 移除常见的前缀
        prefixes_to_remove = [
            '/home/zwy/project2721707-302151/testdata/linux_full/linux-6.6/',
            'testdata/linux_full/linux-6.6/',
            'testdata/linux_full/',
            'linux-6.6/'
        ]
        
        for prefix in prefixes_to_remove:
            if normalized_path.startswith(prefix):
                normalized_path = normalized_path[len(prefix):]
                break
        
        # 检查是否匹配任何过滤模块
        for module in self.filter_modules:
            if normalized_path.startswith(module):
                return True
        return False
        
    def connect_db(self):
        """连接数据库"""
        try:
            return sqlite3.connect(self.db_path)
        except Exception as e:
            print(f"错误: 连接数据库失败: {e}")
            return None
    
    def extract_global_variables(self):
        """提取全局变量"""
        conn = self.connect_db()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            if self.filter_modules:
                # 构建 WHERE 子句来过滤模块
                where_conditions = []
                for module in self.filter_modules:
                    where_conditions.append(f"file_path LIKE '%{module}%'")
                where_clause = "WHERE " + " OR ".join(where_conditions)
                
                query = f"""
                SELECT name, type, file_path, line_number, is_static, definition_code
                FROM GlobalVariables
                {where_clause}
                ORDER BY name
                """
            else:
                query = """
                SELECT name, type, file_path, line_number, is_static, definition_code
                FROM GlobalVariables
                ORDER BY name
                """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            variables = []
            for row in results:
                # 应用额外的路径过滤
                if self.should_include_path(row[2]):
                    variables.append({
                        'name': row[0],
                        'type': row[1],
                        'file_path': row[2],
                        'line_number': row[3],
                        'is_static': bool(row[4]),
                        'definition_code': row[5]
                    })
            
            # 保存到文件
            with open(self.output_dir / 'global_variables.json', 'w') as f:
                json.dump(variables, f, indent=2)
            
            filter_info = f" (模块过滤: {', '.join(self.filter_modules)})" if self.filter_modules else ""
            print(f"提取到 {len(variables)} 个全局变量{filter_info}")
            return variables
            
        except Exception as e:
            print(f"错误: 提取全局变量失败: {e}")
            return []
        finally:
            conn.close()
    
    def extract_functions(self):
        """提取函数"""
        conn = self.connect_db()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            if self.filter_modules:
                # 构建 WHERE 子句来过滤模块
                where_conditions = []
                for module in self.filter_modules:
                    where_conditions.append(f"file_path LIKE '%{module}%'")
                where_clause = "WHERE " + " OR ".join(where_conditions)
                
                query = f"""
                SELECT name, return_type, parameters, file_path, start_line, start_col, 
                       end_line, end_col, is_static, definition_code
                FROM Functions
                {where_clause}
                ORDER BY name
                """
            else:
                query = """
                SELECT name, return_type, parameters, file_path, start_line, start_col, 
                       end_line, end_col, is_static, definition_code
                FROM Functions
                ORDER BY name
                """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            functions = []
            for row in results:
                # 应用额外的路径过滤
                if self.should_include_path(row[3]):
                    functions.append({
                        'name': row[0],
                        'return_type': row[1],
                        'parameters': row[2],
                        'file_path': row[3],
                        'start_line': row[4],
                        'start_col': row[5],
                        'end_line': row[6],
                        'end_col': row[7],
                        'is_static': bool(row[8]),
                        'definition_code': row[9]
                    })
            
            # 保存到文件
            with open(self.output_dir / 'functions.json', 'w') as f:
                json.dump(functions, f, indent=2)
            
            filter_info = f" (模块过滤: {', '.join(self.filter_modules)})" if self.filter_modules else ""
            print(f"提取到 {len(functions)} 个函数{filter_info}")
            return functions
            
        except Exception as e:
            print(f"错误: 提取函数失败: {e}")
            return []
        finally:
            conn.close()
    
    def extract_access_relations(self):
        """提取访问关系"""
        conn = self.connect_db()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            if self.filter_modules:
                # 构建 WHERE 子句来过滤模块
                where_conditions = []
                for module in self.filter_modules:
                    where_conditions.append(f"ar.access_file_path LIKE '%{module}%'")
                where_clause = "WHERE " + " OR ".join(where_conditions)
                
                query = f"""
                SELECT ar.variable_id, ar.function_id, ar.access_type, 
                       ar.access_file_path, ar.access_line_number,
                       gv.name as variable_name, f.name as function_name
                FROM AccessRelations ar
                JOIN GlobalVariables gv ON ar.variable_id = gv.id
                JOIN Functions f ON ar.function_id = f.id
                {where_clause}
                ORDER BY variable_name, function_name
                """
            else:
                query = """
                SELECT ar.variable_id, ar.function_id, ar.access_type, 
                       ar.access_file_path, ar.access_line_number,
                       gv.name as variable_name, f.name as function_name
                FROM AccessRelations ar
                JOIN GlobalVariables gv ON ar.variable_id = gv.id
                JOIN Functions f ON ar.function_id = f.id
                ORDER BY variable_name, function_name
                """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            access_relations = []
            for row in results:
                # 应用额外的路径过滤
                if self.should_include_path(row[3]):
                    access_relations.append({
                        'variable_id': row[0],
                        'function_id': row[1],
                        'access_type': row[2],
                        'access_file_path': row[3],
                        'access_line_number': row[4],
                        'variable_name': row[5],
                        'function_name': row[6]
                    })
            
            # 保存到文件
            with open(self.output_dir / 'access_relations.json', 'w') as f:
                json.dump(access_relations, f, indent=2)
            
            filter_info = f" (模块过滤: {', '.join(self.filter_modules)})" if self.filter_modules else ""
            print(f"提取到 {len(access_relations)} 个访问关系{filter_info}")
            return access_relations
            
        except Exception as e:
            print(f"错误: 提取访问关系失败: {e}")
            return []
        finally:
            conn.close()
    
    def extract_call_relations(self):
        """提取调用关系"""
        conn = self.connect_db()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            if self.filter_modules:
                # 构建 WHERE 子句来过滤模块
                where_conditions = []
                for module in self.filter_modules:
                    where_conditions.append(f"cr.call_site_file_path LIKE '%{module}%'")
                where_clause = "WHERE " + " OR ".join(where_conditions)
                
                query = f"""
                SELECT cr.caller_function_id, cr.callee_function_id,
                       cr.call_site_file_path, cr.call_site_line_number,
                       f1.name as caller_name, f2.name as callee_name
                FROM CallRelations cr
                JOIN Functions f1 ON cr.caller_function_id = f1.id
                JOIN Functions f2 ON cr.callee_function_id = f2.id
                {where_clause}
                ORDER BY caller_name, callee_name
                """
            else:
                query = """
                SELECT cr.caller_function_id, cr.callee_function_id,
                       cr.call_site_file_path, cr.call_site_line_number,
                       f1.name as caller_name, f2.name as callee_name
                FROM CallRelations cr
                JOIN Functions f1 ON cr.caller_function_id = f1.id
                JOIN Functions f2 ON cr.callee_function_id = f2.id
                ORDER BY caller_name, callee_name
                """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            call_relations = []
            for row in results:
                # 应用额外的路径过滤
                if self.should_include_path(row[2]):
                    call_relations.append({
                        'caller_function_id': row[0],
                        'callee_function_id': row[1],
                        'call_site_file_path': row[2],
                        'call_site_line_number': row[3],
                        'caller_name': row[4],
                        'callee_name': row[5]
                    })
            
            # 保存到文件
            with open(self.output_dir / 'call_relations.json', 'w') as f:
                json.dump(call_relations, f, indent=2)
            
            filter_info = f" (模块过滤: {', '.join(self.filter_modules)})" if self.filter_modules else ""
            print(f"提取到 {len(call_relations)} 个调用关系{filter_info}")
            return call_relations
            
        except Exception as e:
            print(f"错误: 提取调用关系失败: {e}")
            return []
        finally:
            conn.close()
    
    def extract_data_pointers(self):
        """提取数据指针"""
        conn = self.connect_db()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            if self.filter_modules:
                # 构建 WHERE 子句来过滤模块
                where_conditions = []
                for module in self.filter_modules:
                    where_conditions.append(f"dp.file_path LIKE '%{module}%'")
                where_clause = "WHERE " + " OR ".join(where_conditions)
                
                query = f"""
                SELECT dp.pointer_name, dp.points_to_var_id, dp.file_path, dp.line_number,
                       gv.name as variable_name
                FROM DataPointers dp
                JOIN GlobalVariables gv ON dp.points_to_var_id = gv.id
                {where_clause}
                ORDER BY pointer_name
                """
            else:
                query = """
                SELECT dp.pointer_name, dp.points_to_var_id, dp.file_path, dp.line_number,
                       gv.name as variable_name
                FROM DataPointers dp
                JOIN GlobalVariables gv ON dp.points_to_var_id = gv.id
                ORDER BY pointer_name
                """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            data_pointers = []
            for row in results:
                # 应用额外的路径过滤
                if self.should_include_path(row[2]):
                    data_pointers.append({
                        'pointer_name': row[0],
                        'points_to_var_id': row[1],
                        'file_path': row[2],
                        'line_number': row[3],
                        'variable_name': row[4]
                    })
            
            # 保存到文件
            with open(self.output_dir / 'data_pointers.json', 'w') as f:
                json.dump(data_pointers, f, indent=2)
            
            filter_info = f" (模块过滤: {', '.join(self.filter_modules)})" if self.filter_modules else ""
            print(f"提取到 {len(data_pointers)} 个数据指针{filter_info}")
            return data_pointers
            
        except Exception as e:
            print(f"错误: 提取数据指针失败: {e}")
            return []
        finally:
            conn.close()
    
    def extract_function_pointers(self):
        """提取函数指针"""
        conn = self.connect_db()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            if self.filter_modules:
                # 构建 WHERE 子句来过滤模块
                where_conditions = []
                for module in self.filter_modules:
                    where_conditions.append(f"fp.file_path LIKE '%{module}%'")
                where_clause = "WHERE " + " OR ".join(where_conditions)
                
                query = f"""
                SELECT fp.pointer_name, fp.points_to_func_id, fp.file_path, fp.line_number,
                       f.name as function_name
                FROM FunctionPointers fp
                JOIN Functions f ON fp.points_to_func_id = f.id
                {where_clause}
                ORDER BY pointer_name
                """
            else:
                query = """
                SELECT fp.pointer_name, fp.points_to_func_id, fp.file_path, fp.line_number,
                       f.name as function_name
                FROM FunctionPointers fp
                JOIN Functions f ON fp.points_to_func_id = f.id
                ORDER BY pointer_name
                """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            function_pointers = []
            for row in results:
                # 应用额外的路径过滤
                if self.should_include_path(row[2]):
                    function_pointers.append({
                        'pointer_name': row[0],
                        'points_to_func_id': row[1],
                        'file_path': row[2],
                        'line_number': row[3],
                        'function_name': row[4]
                    })
            
            # 保存到文件
            with open(self.output_dir / 'function_pointers.json', 'w') as f:
                json.dump(function_pointers, f, indent=2)
            
            filter_info = f" (模块过滤: {', '.join(self.filter_modules)})" if self.filter_modules else ""
            print(f"提取到 {len(function_pointers)} 个函数指针{filter_info}")
            return function_pointers
            
        except Exception as e:
            print(f"错误: 提取函数指针失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_database_stats(self):
        """获取数据库统计信息"""
        conn = self.connect_db()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            stats = {}
            
            tables = ['GlobalVariables', 'Functions', 'AccessRelations', 
                     'CallRelations', 'DataPointers', 'FunctionPointers']
            
            for table in tables:
                if self.filter_modules:
                    # 如果有模块过滤，计算过滤后的数量
                    if table in ['GlobalVariables', 'Functions']:
                        file_path_col = 'file_path'
                    elif table in ['AccessRelations']:
                        file_path_col = 'access_file_path'
                    elif table in ['CallRelations']:
                        file_path_col = 'call_site_file_path'
                    elif table in ['DataPointers', 'FunctionPointers']:
                        file_path_col = 'file_path'
                    else:
                        # 如果不知道如何过滤，就获取全部
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        stats[table] = count
                        continue
                    
                    where_conditions = []
                    for module in self.filter_modules:
                        where_conditions.append(f"{file_path_col} LIKE '%{module}%'")
                    where_clause = "WHERE " + " OR ".join(where_conditions)
                    
                    cursor.execute(f"SELECT COUNT(*) FROM {table} {where_clause}")
                    count = cursor.fetchone()[0]
                else:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                
                stats[table] = count
            
            return stats
            
        except Exception as e:
            print(f"错误: 获取统计信息失败: {e}")
            return {}
        finally:
            conn.close()
    
    def extract_all(self):
        """提取所有数据"""
        filter_info = f" (模块过滤: {', '.join(self.filter_modules)})" if self.filter_modules else ""
        print(f"开始从 {self.db_path} 提取数据{filter_info}...")
        
        # 获取统计信息
        stats = self.get_database_stats()
        print("数据库统计信息:")
        for table, count in stats.items():
            print(f"  {table}: {count} 条记录")
        
        # 提取所有数据
        results = {
            'global_variables': self.extract_global_variables(),
            'functions': self.extract_functions(),
            'access_relations': self.extract_access_relations(),
            'call_relations': self.extract_call_relations(),
            'data_pointers': self.extract_data_pointers(),
            'function_pointers': self.extract_function_pointers()
        }
        
        # 生成汇总报告
        summary = {
            'database_path': self.db_path,
            'filter_modules': self.filter_modules,
            'extraction_stats': {
                'global_variables_count': len(results['global_variables']),
                'functions_count': len(results['functions']),
                'access_relations_count': len(results['access_relations']),
                'call_relations_count': len(results['call_relations']),
                'data_pointers_count': len(results['data_pointers']),
                'function_pointers_count': len(results['function_pointers'])
            },
            'database_stats': stats
        }
        
        with open(self.output_dir / 'extraction_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n数据提取完成!{filter_info}")
        print(f"结果保存在: {self.output_dir}")
        print(f"提取汇总: {summary['extraction_stats']}")
        
        return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="从数据库中提取分析结果用于验证")
    parser.add_argument('modules', nargs='*', default=[], help="要提取的内核模块 (例如 mm fs)，默认提取所有")
    parser.add_argument('--db', default="../full6.12.db", help="数据库文件路径")
    parser.add_argument('--output-dir', default="database_export", help="输出目录")
    
    args = parser.parse_args()
    
    extractor = DatabaseExtractor(
        db_path=args.db,
        output_dir=args.output_dir,
        filter_modules=args.modules if args.modules else None
    )
    extractor.extract_all() 