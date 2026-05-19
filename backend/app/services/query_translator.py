import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from app.models import Function, GlobalVariable, CallRelation, AccessRelation, DataPointer, FunctionPointer

logger = logging.getLogger(__name__)

class QueryTranslator:
    """查询翻译器 - 将自然语言转换为安全的数据库查询"""
    
    def __init__(self):
        # 预定义的安全查询模式
        self.safe_patterns = {
            'function': {
                'name': r'函数名[是为](.+)',
                'file': r'文件[是为](.+)',
                'call_depth': r'调用深度[是为](.+)',
                'complexity': r'复杂度[是为](.+)'
            },
            'variable': {
                'name': r'变量名[是为](.+)',
                'type': r'类型[是为](.+)',
                'access_point': r'访问点[是为](.+)'
            },
            'call_relation': {
                'source': r'源函数[是为](.+)',
                'target': r'目标函数[是为](.+)',
                'depth': r'深度[是为](.+)'
            }
        }
        
        # 查询模板
        self.query_templates = {
            'function_by_name': {
                'sql': 'SELECT * FROM function WHERE name LIKE :name LIMIT :limit',
                'params': ['name', 'limit'],
                'max_limit': 50
            },
            'function_by_file': {
                'sql': 'SELECT * FROM function WHERE file_path LIKE :file_path LIMIT :limit',
                'params': ['file_path', 'limit'],
                'max_limit': 100
            },
            'variable_by_name': {
                'sql': 'SELECT * FROM global_variable WHERE name LIKE :name LIMIT :limit',
                'params': ['name', 'limit'],
                'max_limit': 50
            },
            'variable_by_type': {
                'sql': 'SELECT * FROM global_variable WHERE type LIKE :type LIMIT :limit',
                'params': ['type', 'limit'],
                'max_limit': 100
            },
            'call_chain': {
                'sql': '''
                    WITH RECURSIVE call_tree AS (
                        SELECT caller_function_id, callee_function_id, 1 as depth
                        FROM call_relation 
                        WHERE caller_function_id = (SELECT id FROM function WHERE name = :source_name)
                        UNION ALL
                        SELECT cr.caller_function_id, cr.callee_function_id, ct.depth + 1
                        FROM call_relation cr
                        JOIN call_tree ct ON cr.caller_function_id = ct.callee_function_id
                        WHERE ct.depth < :max_depth
                    )
                    SELECT DISTINCT f.name, ct.depth
                    FROM call_tree ct
                    JOIN function f ON ct.callee_function_id = f.id
                    ORDER BY ct.depth
                    LIMIT :limit
                ''',
                'params': ['source_name', 'max_depth', 'limit'],
                'max_limit': 200
            }
        }
        
        # 敏感字段过滤
        self.sensitive_fields = {
            'function': ['password', 'secret', 'key', 'token'],
            'variable': ['password', 'secret', 'key', 'token'],
            'pointer': ['password', 'secret', 'key', 'token']
        }
    
    def translate_query(self, natural_query: str, query_type: str = None) -> Dict[str, Any]:
        """将自然语言查询转换为安全的数据库查询"""
        try:
            # 解析查询类型
            if not query_type:
                query_type = self._detect_query_type(natural_query)
            
            # 提取查询参数
            params = self._extract_params(natural_query, query_type)
            
            # 选择查询模板
            template = self._select_template(query_type, params)
            
            # 构建查询
            query_result = self._build_query(template, params)
            
            return {
                'success': True,
                'query_type': query_type,
                'template': template['name'],
                'params': params,
                'sql': query_result['sql'],
                'bind_params': query_result['bind_params']
            }
            
        except Exception as e:
            logger.error(f"查询翻译失败: {str(e)}")
            return {
                'success': False,
                'error': f'查询翻译失败: {str(e)}'
            }
    
    def _detect_query_type(self, query: str) -> str:
        """检测查询类型"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['函数', 'function']):
            return 'function'
        elif any(word in query_lower for word in ['变量', 'variable']):
            return 'variable'
        elif any(word in query_lower for word in ['调用', 'call', '关系', 'relation']):
            return 'call_relation'
        elif any(word in query_lower for word in ['指针', 'pointer']):
            return 'pointer'
        else:
            return 'function'  # 默认类型
    
    def _extract_params(self, query: str, query_type: str) -> Dict[str, Any]:
        """提取查询参数"""
        params = {}
        
        if query_type == 'function':
            # 提取函数名
            name_match = re.search(r'函数名[是为](.+)', query)
            if name_match:
                params['name'] = f"%{name_match.group(1).strip()}%"
            
            # 提取文件名
            file_match = re.search(r'文件[是为](.+)', query)
            if file_match:
                params['file_path'] = f"%{file_match.group(1).strip()}%"
            
            # 提取调用深度
            depth_match = re.search(r'调用深度[是为](\d+)', query)
            if depth_match:
                params['call_depth'] = int(depth_match.group(1))
        
        elif query_type == 'variable':
            # 提取变量名
            name_match = re.search(r'变量名[是为](.+)', query)
            if name_match:
                params['name'] = f"%{name_match.group(1).strip()}%"
            
            # 提取类型
            type_match = re.search(r'类型[是为](.+)', query)
            if type_match:
                params['type'] = f"%{type_match.group(1).strip()}%"
        
        elif query_type == 'call_relation':
            # 提取源函数
            source_match = re.search(r'源函数[是为](.+)', query)
            if source_match:
                params['source_name'] = source_match.group(1).strip()
            
            # 提取目标函数
            target_match = re.search(r'目标函数[是为](.+)', query)
            if target_match:
                params['target_name'] = target_match.group(1).strip()
            
            # 提取深度
            depth_match = re.search(r'深度[是为](\d+)', query)
            if depth_match:
                params['max_depth'] = min(int(depth_match.group(1)), 10)  # 限制最大深度
            else:
                params['max_depth'] = 5  # 默认深度
        
        return params
    
    def _select_template(self, query_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """选择查询模板"""
        if query_type == 'function':
            if 'name' in params:
                return {'name': 'function_by_name', **self.query_templates['function_by_name']}
            elif 'file_path' in params:
                return {'name': 'function_by_file', **self.query_templates['function_by_file']}
            else:
                return {'name': 'function_by_name', **self.query_templates['function_by_name']}
        
        elif query_type == 'variable':
            if 'name' in params:
                return {'name': 'variable_by_name', **self.query_templates['variable_by_name']}
            elif 'type' in params:
                return {'name': 'variable_by_type', **self.query_templates['variable_by_type']}
            else:
                return {'name': 'variable_by_name', **self.query_templates['variable_by_name']}
        
        elif query_type == 'call_relation':
            return {'name': 'call_chain', **self.query_templates['call_chain']}
        
        else:
            return {'name': 'function_by_name', **self.query_templates['function_by_name']}
    
    def _build_query(self, template: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """构建查询"""
        sql = template['sql']
        bind_params = {}
        
        # 设置默认限制
        limit = min(params.get('limit', 50), template.get('max_limit', 100))
        bind_params['limit'] = limit
        
        # 绑定参数
        for param_name in template['params']:
            if param_name in params:
                bind_params[param_name] = params[param_name]
            elif param_name == 'limit':
                bind_params[param_name] = limit
        
        return {
            'sql': sql,
            'bind_params': bind_params
        }
    
    def execute_query(self, query_info: Dict[str, Any], db_session) -> Dict[str, Any]:
        """执行查询并返回结果"""
        try:
            if not query_info['success']:
                return query_info
            
            # 执行查询
            result = db_session.execute(
                text(query_info['sql']), 
                query_info['bind_params']
            )
            
            # 获取结果
            rows = result.fetchall()
            
            # 过滤敏感信息
            filtered_rows = self._filter_sensitive_data(rows, query_info['query_type'])
            
            return {
                'success': True,
                'query_type': query_info['query_type'],
                'row_count': len(filtered_rows),
                'data': filtered_rows,
                'execution_time': 0  # 可以添加实际执行时间
            }
            
        except SQLAlchemyError as e:
            logger.error(f"查询执行失败: {str(e)}")
            return {
                'success': False,
                'error': f'查询执行失败: {str(e)}'
            }
        except Exception as e:
            logger.error(f"查询执行异常: {str(e)}")
            return {
                'success': False,
                'error': f'查询执行异常: {str(e)}'
            }
    
    def _filter_sensitive_data(self, rows: List, query_type: str) -> List:
        """过滤敏感数据"""
        filtered_rows = []
        
        for row in rows:
            row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            
            # 检查敏感字段
            is_sensitive = False
            for field in self.sensitive_fields.get(query_type, []):
                for key, value in row_dict.items():
                    if field in str(key).lower() or field in str(value).lower():
                        is_sensitive = True
                        break
                if is_sensitive:
                    break
            
            if not is_sensitive:
                filtered_rows.append(row_dict)
        
        return filtered_rows

# 创建全局查询翻译器实例
query_translator = QueryTranslator() 