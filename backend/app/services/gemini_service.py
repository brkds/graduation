import google.generativeai as genai
import logging
import time
from typing import Dict, List, Optional, Any
from flask import current_app
import json

logger = logging.getLogger(__name__)

class GeminiService:
    """Gemini API服务类"""
    
    def __init__(self):
        self.api_key = None
        self.model_name = None
        self.max_tokens = None
        self.temperature = None
        self.top_p = None
        self.top_k = None
        self.client = None
        
        # 延迟初始化，在应用上下文中获取配置
        self._initialized = False
    
    def _initialize(self):
        """延迟初始化，在应用上下文中获取配置"""
        if self._initialized:
            return
            
        try:
            self.api_key = current_app.config.get('GEMINI_API_KEY')
            self.model_name = current_app.config.get('GEMINI_MODEL', 'gemini-2.5-flash')
            self.max_tokens = current_app.config.get('GEMINI_MAX_TOKENS', 8192)
            self.temperature = current_app.config.get('GEMINI_TEMPERATURE', 0.1)
            self.top_p = current_app.config.get('GEMINI_TOP_P', 0.8)
            self.top_k = current_app.config.get('GEMINI_TOP_K', 40)
            
            if not self.api_key:
                logger.warning("Gemini API密钥未配置")
                self._initialized = True
                return
            
            # 配置代理
            proxy_host = current_app.config.get('GEMINI_PROXY_HOST', '192.168.93.1')
            proxy_port = current_app.config.get('GEMINI_PROXY_PORT', '7890')
            
            # 设置环境变量
            import os
            os.environ['HTTP_PROXY'] = f'http://{proxy_host}:{proxy_port}'
            os.environ['HTTPS_PROXY'] = f'http://{proxy_host}:{proxy_port}'
            
            logger.info(f"配置代理: {proxy_host}:{proxy_port}")
                
            # 使用与test_gemini.py相同的方式
            from google import genai
            self.client = genai.Client()
            
            logger.info(f"Gemini服务初始化成功，使用模型: {self.model_name}")
        except Exception as e:
            logger.error(f"Gemini服务初始化失败: {str(e)}")
            self.client = None
        finally:
            self._initialized = True
    
    def is_available(self) -> bool:
        """检查Gemini服务是否可用"""
        self._initialize()
        return self.client is not None and self.api_key
    
    def analyze_function(self, function_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析函数信息"""
        self._initialize()
        if not self.is_available():
            return {"error": "Gemini服务不可用"}
        
        try:
            prompt = self._build_function_analysis_prompt(function_data)
            response = self._call_gemini(prompt)
            return self._parse_analysis_response(response, "function_analysis")
        except Exception as e:
            logger.error(f"函数分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def analyze_file(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析文件信息"""
        self._initialize()
        if not self.is_available():
            return {"error": "Gemini服务不可用"}
        
        try:
            prompt = self._build_file_analysis_prompt(file_data)
            response = self._call_gemini(prompt)
            return self._parse_analysis_response(response, "file_analysis")
        except Exception as e:
            logger.error(f"文件分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def analyze_relationship(self, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析关系信息"""
        self._initialize()
        if not self.is_available():
            return {"error": "Gemini服务不可用"}
        
        try:
            prompt = self._build_relationship_analysis_prompt(relationship_data)
            response = self._call_gemini(prompt)
            return self._parse_analysis_response(response, "relationship_analysis")
        except Exception as e:
            logger.error(f"关系分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def analyze_code_pattern(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析代码模式"""
        self._initialize()
        if not self.is_available():
            return {"error": "Gemini服务不可用"}
        
        try:
            prompt = self._build_pattern_analysis_prompt(pattern_data)
            response = self._call_gemini(prompt)
            return self._parse_analysis_response(response, "pattern_analysis")
        except Exception as e:
            logger.error(f"代码模式分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def analyze_overview(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """概览分析"""
        self._initialize()
        if not self.is_available():
            return {"error": "Gemini服务不可用"}
        
        try:
            system_prompt = analysis_data.get('system_prompt', '')
            backend_data = analysis_data.get('backend_data', {})
            user_prompt = analysis_data.get('user_prompt', '')
            
            prompt = f"{system_prompt}\n\n后端数据：{json.dumps(backend_data, ensure_ascii=False, indent=2)}\n\n用户需求：{user_prompt}"
            response = self._call_gemini(prompt)
            return self._parse_analysis_response(response, "overview_analysis")
        except Exception as e:
            logger.error(f"概览分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def analyze_file_structure(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """文件结构分析"""
        self._initialize()
        if not self.is_available():
            return {"error": "Gemini服务不可用"}
        
        try:
            system_prompt = analysis_data.get('system_prompt', '')
            backend_data = analysis_data.get('backend_data', {})
            user_prompt = analysis_data.get('user_prompt', '')
            
            prompt = f"{system_prompt}\n\n后端数据：{json.dumps(backend_data, ensure_ascii=False, indent=2)}\n\n用户需求：{user_prompt}"
            response = self._call_gemini(prompt)
            return self._parse_analysis_response(response, "file_structure_analysis")
        except Exception as e:
            logger.error(f"文件结构分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def analyze_function_detail(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """函数详细分析"""
        self._initialize()
        if not self.is_available():
            return {"error": "Gemini服务不可用"}
        
        try:
            system_prompt = analysis_data.get('system_prompt', '')
            backend_data = analysis_data.get('backend_data', {})
            user_prompt = analysis_data.get('user_prompt', '')
            
            prompt = f"{system_prompt}\n\n后端数据：{json.dumps(backend_data, ensure_ascii=False, indent=2)}\n\n用户需求：{user_prompt}"
            response = self._call_gemini(prompt)
            return self._parse_analysis_response(response, "function_detail_analysis")
        except Exception as e:
            logger.error(f"函数详细分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def analyze_call_chain(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用链分析"""
        self._initialize()
        if not self.is_available():
            return {"error": "Gemini服务不可用"}
        
        try:
            system_prompt = analysis_data.get('system_prompt', '')
            backend_data = analysis_data.get('backend_data', {})
            user_prompt = analysis_data.get('user_prompt', '')
            
            prompt = f"{system_prompt}\n\n后端数据：{json.dumps(backend_data, ensure_ascii=False, indent=2)}\n\n用户需求：{user_prompt}"
            response = self._call_gemini(prompt)
            return self._parse_analysis_response(response, "call_chain_analysis")
        except Exception as e:
            logger.error(f"调用链分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def analyze_variable(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """变量分析"""
        self._initialize()
        if not self.is_available():
            return {"error": "Gemini服务不可用"}
        
        try:
            system_prompt = analysis_data.get('system_prompt', '')
            backend_data = analysis_data.get('backend_data', {})
            user_prompt = analysis_data.get('user_prompt', '')
            
            prompt = f"{system_prompt}\n\n后端数据：{json.dumps(backend_data, ensure_ascii=False, indent=2)}\n\n用户需求：{user_prompt}"
            response = self._call_gemini(prompt)
            return self._parse_analysis_response(response, "variable_analysis")
        except Exception as e:
            logger.error(f"变量分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def analyze_pointer(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """指针分析"""
        self._initialize()
        if not self.is_available():
            return {"error": "Gemini服务不可用"}
        
        try:
            system_prompt = analysis_data.get('system_prompt', '')
            backend_data = analysis_data.get('backend_data', {})
            user_prompt = analysis_data.get('user_prompt', '')
            
            prompt = f"{system_prompt}\n\n后端数据：{json.dumps(backend_data, ensure_ascii=False, indent=2)}\n\n用户需求：{user_prompt}"
            response = self._call_gemini(prompt)
            return self._parse_analysis_response(response, "pointer_analysis")
        except Exception as e:
            logger.error(f"指针分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def _call_gemini(self, prompt: str, max_retries: int = 3) -> str:
        """调用Gemini API，带重试机制和超时处理"""
        for attempt in range(max_retries):
            try:
                import threading
                import queue
                
                # 使用队列来传递结果
                result_queue = queue.Queue()
                
                def api_call():
                    try:
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt
                        )
                        if response.text:
                            result_queue.put(("success", response.text))
                        else:
                            result_queue.put(("empty", "AI分析完成，但返回内容为空。"))
                    except Exception as e:
                        result_queue.put(("error", str(e)))
                
                # 创建线程执行API调用
                api_thread = threading.Thread(target=api_call)
                api_thread.daemon = True
                api_thread.start()
                
                # 等待结果，最多30秒
                try:
                    result_type, result_data = result_queue.get(timeout=30)
                    if result_type == "success":
                        return result_data
                    elif result_type == "empty":
                        logger.warning(f"Gemini返回空响应，尝试次数: {attempt + 1}")
                        return result_data
                    else:
                        raise Exception(result_data)
                except queue.Empty:
                    logger.error(f"Gemini API调用超时 (尝试 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        return "AI分析超时，请稍后重试。"
                        
            except Exception as e:
                logger.error(f"Gemini API调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return f"AI分析失败: {str(e)}"
        
        return "AI分析失败，已达到最大重试次数"
    
    def _build_function_analysis_prompt(self, function_data: Dict[str, Any]) -> str:
        """构建函数分析提示词"""
        return f"""
你是一个专业的C语言代码分析专家。请分析以下函数信息并提供详细的分析报告。

函数信息：
- 函数名: {function_data.get('name', 'N/A')}
- 文件路径: {function_data.get('file_path', 'N/A')}
- 函数签名: {function_data.get('signature', 'N/A')}
- 函数体: {function_data.get('body', 'N/A')}
- 调用次数: {function_data.get('call_count', 0)}
- 被调用函数: {function_data.get('called_functions', [])}
- 访问的全局变量: {function_data.get('accessed_variables', [])}

请从以下角度进行分析：
1. 函数功能分析：这个函数的主要作用是什么？
2. 复杂度分析：函数的复杂度和可读性如何？
3. 性能分析：是否存在性能问题？
4. 安全性分析：是否存在潜在的安全风险？
5. 代码质量：代码风格和最佳实践如何？
6. 优化建议：如何改进这个函数？

如果需要查询更多数据来支持分析，请使用以下格式输出结构化请求：
{{"command": "query", "type": "function", "params": {{"name": "函数名", "file": "文件名"}}}}

请用中文回答，并给出具体的建议。
"""
    
    def _build_file_analysis_prompt(self, file_data: Dict[str, Any]) -> str:
        """构建文件分析提示词"""
        return f"""
你是一个专业的C语言代码分析专家。请分析以下文件信息并提供详细的分析报告。

文件信息：
- 文件路径: {file_data.get('file_path', 'N/A')}
- 文件大小: {file_data.get('file_size', 'N/A')}
- 函数数量: {file_data.get('function_count', 0)}
- 全局变量数量: {file_data.get('variable_count', 0)}
- 主要函数: {file_data.get('main_functions', [])}
- 文件依赖: {file_data.get('dependencies', [])}

请从以下角度进行分析：
1. 文件结构分析：文件的整体架构如何？
2. 功能模块分析：文件包含哪些主要功能模块？
3. 依赖关系分析：文件的依赖关系是否合理？
4. 代码组织：代码的组织结构是否清晰？
5. 可维护性：代码的可维护性如何？
6. 改进建议：如何优化这个文件？

如果需要查询更多数据来支持分析，请使用以下格式输出结构化请求：
{{"command": "query", "type": "function", "params": {{"file": "文件名"}}}}

请用中文回答，并给出具体的建议。
"""
    
    def _build_relationship_analysis_prompt(self, relationship_data: Dict[str, Any]) -> str:
        """构建关系分析提示词"""
        return f"""
你是一个专业的C语言代码分析专家。请分析以下函数调用关系信息并提供详细的分析报告。

关系信息：
- 源函数: {relationship_data.get('source_function', 'N/A')}
- 目标函数: {relationship_data.get('target_function', 'N/A')}
- 调用路径: {relationship_data.get('call_path', [])}
- 调用深度: {relationship_data.get('call_depth', 0)}
- 相关变量: {relationship_data.get('related_variables', [])}

请从以下角度进行分析：
1. 调用关系分析：这个调用关系是否合理？
2. 依赖分析：是否存在循环依赖？
3. 性能影响：这个调用关系对性能有什么影响？
4. 设计模式：是否遵循良好的设计模式？
5. 重构建议：如何优化这个调用关系？

请用中文回答，并给出具体的建议。
"""
    
    def _build_pattern_analysis_prompt(self, pattern_data: Dict[str, Any]) -> str:
        """构建代码模式分析提示词"""
        return f"""
你是一个专业的C语言代码分析专家。请分析以下代码模式信息并提供详细的分析报告。

模式信息：
- 模式类型: {pattern_data.get('pattern_type', 'N/A')}
- 相关函数: {pattern_data.get('related_functions', [])}
- 代码片段: {pattern_data.get('code_snippets', [])}
- 使用频率: {pattern_data.get('usage_frequency', 0)}

请从以下角度进行分析：
1. 模式识别：这是什么类型的代码模式？
2. 模式分析：这个模式的使用是否合理？
3. 最佳实践：是否符合C语言的最佳实践？
4. 性能影响：这个模式对性能有什么影响？
5. 改进建议：如何优化这个代码模式？

请用中文回答，并给出具体的建议。
"""
    
    def _parse_analysis_response(self, response: str, analysis_type: str) -> Dict[str, Any]:
        """解析分析响应"""
        try:
            return {
                "success": True,
                "analysis_type": analysis_type,
                "content": response,
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"解析分析响应失败: {str(e)}")
            return {
                "success": False,
                "error": f"解析失败: {str(e)}",
                "raw_response": response
            }

# 创建全局Gemini服务实例（延迟初始化）
gemini_service = GeminiService() 