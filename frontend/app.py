from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import requests
import func_tree

app = Flask(__name__)
CORS(app)

# 后端API配置
BACKEND_URL = "http://localhost:5002"  # 真实后端API地址

@app.route('/')
def start():
    return send_file('templates/main.html')

@app.route('/test')
def test():
    return send_file('test_simple.html')

@app.route('/debug')
def debug():
    return send_file('debug.html')

@app.route('/simple')
def simple():
    return send_file('simple_main.html')

@app.route('/debug-data')
def debug_data():
    return send_file('debug_data.html')

@app.route('/test-fix')
def test_fix():
    return send_file('test_fix.html')

@app.route('/directory_children', methods=['GET'])
def get_directory_children():
    """代理：获取目录子节点"""
    try:
        params = dict(request.args)
        response = requests.get(f"{BACKEND_URL}/directory_children", params=params)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify([])
    except requests.exceptions.RequestException as e:
        print(f"连接后端API失败: {e}")
        return jsonify([])

@app.route('/func_tree', methods=['GET'])
def get_func_tree():
    """从真实后端获取文件树数据"""
    try:
        response = requests.get(f"{BACKEND_URL}/func_tree")
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"后端API错误: {response.status_code}")
            # 返回模拟文件树数据
            return jsonify([
                {
                    "name": "kernel",
                    "type": "folder",
                    "children": [
                        {"name": "kernel/sched.c", "type": "file", "full_path": "kernel/sched.c"},
                        {"name": "kernel/fork.c", "type": "file", "full_path": "kernel/fork.c"},
                        {"name": "kernel/signal.c", "type": "file", "full_path": "kernel/signal.c"}
                    ]
                },
                {
                    "name": "mm",
                    "type": "folder", 
                    "children": [
                        {"name": "mm/memory.c", "type": "file", "full_path": "mm/memory.c"},
                        {"name": "mm/slab.c", "type": "file", "full_path": "mm/slab.c"},
                        {"name": "mm/page_alloc.c", "type": "file", "full_path": "mm/page_alloc.c"}
                    ]
                },
                {
                    "name": "fs",
                    "type": "folder",
                    "children": [
                        {"name": "fs/namei.c", "type": "file", "full_path": "fs/namei.c"},
                        {"name": "fs/read_write.c", "type": "file", "full_path": "fs/read_write.c"},
                        {"name": "fs/inode.c", "type": "file", "full_path": "fs/inode.c"}
                    ]
                }
            ])
    except requests.exceptions.RequestException as e:
        print(f"连接后端API失败: {e}")
        # 返回模拟文件树数据
        return jsonify([
            {
                "name": "kernel",
                "type": "folder",
                "children": [
                    {"name": "kernel/sched.c", "type": "file", "full_path": "kernel/sched.c"},
                    {"name": "kernel/fork.c", "type": "file", "full_path": "kernel/fork.c"},
                    {"name": "kernel/signal.c", "type": "file", "full_path": "kernel/signal.c"}
                ]
            },
            {
                "name": "mm",
                "type": "folder", 
                "children": [
                    {"name": "mm/memory.c", "type": "file", "full_path": "mm/memory.c"},
                    {"name": "mm/slab.c", "type": "file", "full_path": "mm/slab.c"},
                    {"name": "mm/page_alloc.c", "type": "file", "full_path": "mm/page_alloc.c"}
                ]
            },
            {
                "name": "fs",
                "type": "folder",
                "children": [
                    {"name": "fs/namei.c", "type": "file", "full_path": "fs/namei.c"},
                    {"name": "fs/read_write.c", "type": "file", "full_path": "fs/read_write.c"},
                    {"name": "fs/inode.c", "type": "file", "full_path": "fs/inode.c"}
                ]
            }
        ])

@app.route('/node_graph')
def get_node_graph():
    """代理：获取以节点为中心的连通关系图"""
    try:
        node_id = request.args.get("node_id", "")
        max_depth = request.args.get("max_depth", "3")
        response = requests.get(f"{BACKEND_URL}/node_graph", params={
            "node_id": node_id, "max_depth": max_depth
        })
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"nodes": [], "edges": []})
    except requests.exceptions.RequestException as e:
        print(f"连接后端API失败: {e}")
        return jsonify({"nodes": [], "edges": []})

@app.route('/graph')
def get_graph():
    """从真实后端获取关系图数据"""
    try:
        filename = request.args.get("file", "")
        response = requests.get(f"{BACKEND_URL}/graph", params={"file": filename})
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"后端API错误: {response.status_code}")
            # 返回模拟关系图数据
            return jsonify({
                "nodes": [
                    {"id": 1, "label": "main", "type": "function", "color": "#3b82f6", "file_path": filename or "example.c"},
                    {"id": 2, "label": "init_process", "type": "function", "color": "#3b82f6", "file_path": filename or "example.c"},
                    {"id": 3, "label": "global_var", "type": "variable", "color": "#10b981", "file_path": filename or "example.c"},
                    {"id": 4, "label": "ptr_to_data", "type": "data_pointer", "color": "#8b5cf6", "file_path": filename or "example.c"},
                    {"id": 5, "label": "func_ptr", "type": "function_pointer", "color": "#ec4899", "file_path": filename or "example.c"}
                ],
                "edges": [
                    {"from": 1, "to": 2, "color": "#FF0000", "arrows": "to", "label": "calls"},
                    {"from": 1, "to": 3, "color": "#00C853", "arrows": "to", "label": "reads"},
                    {"from": 2, "to": 4, "color": "#AA00FF", "arrows": "to", "label": "points_to"},
                    {"from": 4, "to": 3, "color": "#AA00FF", "arrows": "to", "label": "points_to"},
                    {"from": 5, "to": 2, "color": "#FF0000", "arrows": "to", "label": "func_points_to"}
                ]
            })
    except requests.exceptions.RequestException as e:
        print(f"连接后端API失败: {e}")
        # 返回模拟关系图数据
        return jsonify({
            "nodes": [
                {"id": 1, "label": "main", "type": "function", "color": "#3b82f6", "file_path": filename or "example.c"},
                {"id": 2, "label": "init_process", "type": "function", "color": "#3b82f6", "file_path": filename or "example.c"},
                {"id": 3, "label": "global_var", "type": "variable", "color": "#10b981", "file_path": filename or "example.c"},
                {"id": 4, "label": "ptr_to_data", "type": "data_pointer", "color": "#8b5cf6", "file_path": filename or "example.c"},
                {"id": 5, "label": "func_ptr", "type": "function_pointer", "color": "#ec4899", "file_path": filename or "example.c"}
            ],
            "edges": [
                {"from": 1, "to": 2, "color": "#FF0000", "arrows": "to", "label": "calls"},
                {"from": 1, "to": 3, "color": "#00C853", "arrows": "to", "label": "reads"},
                {"from": 2, "to": 4, "color": "#AA00FF", "arrows": "to", "label": "points_to"},
                {"from": 4, "to": 3, "color": "#AA00FF", "arrows": "to", "label": "points_to"},
                {"from": 5, "to": 2, "color": "#FF0000", "arrows": "to", "label": "func_points_to"}
            ]
        })

@app.route('/search_suggest', methods=['GET'])
def search_suggest():
    """从真实后端获取搜索建议"""
    try:
        # 传递所有请求参数到后端
        params = dict(request.args)
        response = requests.get(f"{BACKEND_URL}/search_suggest", params=params)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"后端API错误: {response.status_code}")
            return jsonify([])
    except requests.exceptions.RequestException as e:
        print(f"连接后端API失败: {e}")
        return jsonify([])

@app.route('/search_detail', methods=['GET'])
def search_detail():
    """从真实后端获取搜索详情"""
    try:
        # 前端可能传递name或id参数
        name = request.args.get("name", "")
        item_id = request.args.get("id", "")
        
        # 优先使用id参数，如果没有则使用name参数
        search_param = item_id if item_id else name
        
        if not search_param:
            return jsonify({"error": True, "message": "缺少搜索参数"})
        
        # 向后端传递id参数（后端期望的参数名）
        response = requests.get(f"{BACKEND_URL}/search_detail", params={"id": search_param})
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"后端API错误: {response.status_code}")
            return jsonify({"error": True, "message": f"后端API错误: {response.status_code}"})
    except requests.exceptions.RequestException as e:
        print(f"连接后端API失败: {e}")
        return jsonify({"error": True, "message": f"连接后端API失败: {e}"})

@app.route('/func_body', methods=['GET'])
def get_func_body():
    """从真实后端获取函数体源码"""
    try:
        func_id = request.args.get("id", "")
        response = requests.get(f"{BACKEND_URL}/func_body", params={"id": func_id})
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"后端API错误: {response.status_code}")
            return jsonify({"functions": []})
    except requests.exceptions.RequestException as e:
        print(f"连接后端API失败: {e}")
        return jsonify({"functions": []})

@app.route('/call_relations', methods=['GET'])
def get_call_relations():
    """从真实后端获取函数调用关系（保留兼容性）"""
    try:
        function_id = request.args.get("function_id", "")
        response = requests.get(f"{BACKEND_URL}/call_relations", params={"function_id": function_id})
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"调用关系API错误: {response.status_code}")
            # 返回模拟数据作为后备
            return jsonify({
                "calls": [
                    {
                        "id": 1,
                        "callee_name": "示例函数1",
                        "callee_file": "example1.c",
                        "call_line": 123
                    },
                    {
                        "id": 2,
                        "callee_name": "示例函数2", 
                        "callee_file": "example2.c",
                        "call_line": 456
                    }
                ],
                "called_by": [
                    {
                        "id": 3,
                        "caller_name": "调用方函数1",
                        "caller_file": "caller1.c",
                        "call_line": 789
                    }
                ]
            })
    except requests.exceptions.RequestException as e:
        print(f"连接调用关系API失败: {e}")
        # 返回模拟数据
        return jsonify({
            "calls": [],
            "called_by": []
        })

@app.route('/function_calls', methods=['GET'])
def get_function_calls():
    """从真实后端获取函数调用关系（新接口）"""
    try:
        function_id = request.args.get("function_id", "")
        print(f"前端代理调用: /function_calls?function_id={function_id}")
        
        if not function_id:
            return jsonify({
                'error': True,
                'message': '请提供函数ID'
            }), 400
        
        response = requests.get(f"{BACKEND_URL}/function_calls", params={"function_id": function_id})
        if response.status_code == 200:
            data = response.json()
            print(f"后端返回数据: {len(data.get('calls_made', []))} 个调用, {len(data.get('calls_received', []))} 个被调用")
            return jsonify(data)
        else:
            print(f"函数调用关系API错误: {response.status_code}, 响应: {response.text}")
            return jsonify({
                'error': True,
                'message': f'后端API错误: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"连接函数调用关系API失败: {e}")
        return jsonify({
            'error': True,
            'message': f'连接后端失败: {str(e)}'
        }), 500

@app.route('/file_statistics', methods=['GET'])
def get_file_statistics():
    """从真实后端获取文件统计信息"""
    try:
        file_path = request.args.get("file_path", "")
        response = requests.get(f"{BACKEND_URL}/file_statistics", params={"file_path": file_path})
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"后端API错误: {response.status_code}")
            return jsonify({})
    except requests.exceptions.RequestException as e:
        print(f"连接后端API失败: {e}")
        return jsonify({})

@app.route('/global_statistics', methods=['GET'])
def get_global_statistics():
    """从真实后端获取全局统计信息"""
    try:
        print(f"尝试连接后端API: {BACKEND_URL}/global_statistics")
        response = requests.get(f"{BACKEND_URL}/global_statistics", timeout=5)
        if response.status_code == 200:
            print("成功从后端获取全局统计数据")
            return jsonify(response.json())
        else:
            print(f"后端API错误: {response.status_code}, 响应: {response.text}")
            # 返回模拟数据作为后备
            return jsonify({
                "total_files": 2847,
                "total_functions": 45623,
                "total_variables": 18934,
                "total_data_pointers": 1234,
                "total_function_pointers": 567,
                "total_call_relations": 89012,
                "total_access_relations": 34567,
                "total_read_relations": 25000,
                "total_write_relations": 9567,
                "recent_files": [
                    {"file_path": "include/linux/mm.h"},
                    {"file_path": "drivers/char/hw_random/core.c"},
                    {"file_path": "arch/x86/kernel/cpu.c"}
                ],
                "hot_functions": [
                    {"name": "kmalloc", "file_path": "mm/slab.c", "call_count": 1523},
                    {"name": "printk", "file_path": "kernel/printk.c", "call_count": 892},
                    {"name": "mutex_lock", "file_path": "kernel/mutex.c", "call_count": 654}
                ],
                "hot_variables": [
                    {"name": "current", "file_path": "include/linux/current.h", "access_count": 2341},
                    {"name": "init_task", "file_path": "init/init_task.c", "access_count": 1205},
                    {"name": "system_wq", "file_path": "kernel/workqueue.c", "access_count": 876}
                ]
            })
    except requests.exceptions.RequestException as e:
        print(f"连接后端API失败: {e}")
        # 返回模拟数据
        return jsonify({
            "total_files": 2847,
            "total_functions": 45623,
            "total_variables": 18934,
            "total_data_pointers": 1234,
            "total_function_pointers": 567,
            "total_call_relations": 89012,
            "total_access_relations": 34567,
            "total_read_relations": 25000,
            "total_write_relations": 9567,
            "recent_files": [
                {"file_path": "include/linux/mm.h"},
                {"file_path": "drivers/char/hw_random/core.c"},
                {"file_path": "arch/x86/kernel/cpu.c"}
            ],
            "hot_functions": [
                {"name": "kmalloc", "file_path": "mm/slab.c", "call_count": 1523},
                {"name": "printk", "file_path": "kernel/printk.c", "call_count": 892},
                {"name": "mutex_lock", "file_path": "kernel/mutex.c", "call_count": 654}
            ],
            "hot_variables": [
                {"name": "current", "file_path": "include/linux/current.h", "access_count": 2341},
                {"name": "init_task", "file_path": "init/init_task.c", "access_count": 1205},
                {"name": "system_wq", "file_path": "kernel/workqueue.c", "access_count": 876}
            ]
        })

@app.route('/api/path_analysis', methods=['GET'])
def path_analysis():
    """路径分析代理接口"""
    try:
        source_id = request.args.get('source_id')
        target_id = request.args.get('target_id')
        max_depth = request.args.get('max_depth', '5')
        
        if not source_id or not target_id:
            return jsonify({'error': True, 'message': '缺少源函数ID或目标函数ID'}), 400
        
        response = requests.get(f"{BACKEND_URL}/api/path_analysis", params={
            'source_id': source_id,
            'target_id': target_id,
            'max_depth': max_depth
        })
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"路径分析API错误: {response.status_code}, 响应: {response.text}")
            return jsonify({
                'error': True,
                'message': f'后端API错误: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"连接路径分析API失败: {e}")
        return jsonify({
            'error': True,
            'message': f'连接后端失败: {str(e)}'
        }), 500

@app.route('/hot_functions', methods=['GET'])
def get_hot_functions():
    """热点函数代理接口（被调用次数最多的函数）"""
    try:
        count = request.args.get('count', '5')
        print(f"前端代理调用: /hot_functions?count={count}")
        
        response = requests.get(f"{BACKEND_URL}/hot_functions", params={"count": count})
        if response.status_code == 200:
            data = response.json()
            print(f"后端返回热点函数数据: {len(data.get('functions', []))} 个函数")
            return jsonify(data)
        else:
            print(f"热点函数API错误: {response.status_code}, 响应: {response.text}")
            return jsonify({
                'error': True,
                'message': f'后端API错误: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"连接热点函数API失败: {e}")
        return jsonify({
            'error': True,
            'message': f'连接后端失败: {str(e)}'
        }), 500

@app.route('/hot_access_functions', methods=['GET'])
def get_hot_access_functions():
    """访问热点函数代理接口（访问变量次数最多的函数）"""
    try:
        count = request.args.get('count', '5')
        print(f"前端代理调用: /hot_access_functions?count={count}")
        
        response = requests.get(f"{BACKEND_URL}/hot_access_functions", params={"count": count})
        if response.status_code == 200:
            data = response.json()
            print(f"后端返回访问热点函数数据: {len(data.get('functions', []))} 个函数")
            return jsonify(data)
        else:
            print(f"访问热点函数API错误: {response.status_code}, 响应: {response.text}")
            return jsonify({
                'error': True,
                'message': f'后端API错误: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"连接访问热点函数API失败: {e}")
        return jsonify({
            'error': True,
            'message': f'连接后端失败: {str(e)}'
        }), 500

@app.route('/hot_access_variables', methods=['GET'])
def get_hot_access_variables():
    """热点变量代理接口（被访问次数最多的变量）"""
    try:
        count = request.args.get('count', '5')
        print(f"前端代理调用: /hot_access_variables?count={count}")
        
        response = requests.get(f"{BACKEND_URL}/hot_access_variables", params={"count": count})
        if response.status_code == 200:
            data = response.json()
            print(f"后端返回热点变量数据: {len(data.get('variables', []))} 个变量")
            return jsonify(data)
        else:
            print(f"热点变量API错误: {response.status_code}, 响应: {response.text}")
            return jsonify({
                'error': True,
                'message': f'后端API错误: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"连接热点变量API失败: {e}")
        return jsonify({
            'error': True,
            'message': f'连接后端失败: {str(e)}'
        }), 500

@app.route('/file_content', methods=['GET'])
def get_file_content():
    """从真实后端获取文件内容"""
    try:
        file_path = request.args.get('file_path', '')
        print(f"前端代理调用: /file_content?file_path={file_path}")
        
        if not file_path:
            return jsonify({
                'error': True,
                'message': '请提供文件路径'
            }), 400
        
        response = requests.get(f"{BACKEND_URL}/file_content", params={"file_path": file_path})
        if response.status_code == 200:
            data = response.json()
            print(f"后端返回文件内容数据: 文件大小 {len(data.get('content', ''))} 字符")
            return jsonify(data)
        else:
            print(f"文件内容API错误: {response.status_code}, 响应: {response.text}")
            return jsonify({
                'error': True,
                'message': f'后端API错误: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"连接文件内容API失败: {e}")
        return jsonify({
            'error': True,
            'message': f'连接后端失败: {str(e)}'
        }), 500

# ==================== AI接口代理 ====================

@app.route('/ai/analyze_overview', methods=['POST'])
def ai_analyze_overview():
    """AI概览分析代理接口"""
    try:
        data = request.get_json()
        print(f"前端代理调用: /ai/analyze_overview")
        
        response = requests.post(f"{BACKEND_URL}/ai/analyze_overview", json=data)
        if response.status_code == 200:
            data = response.json()
            print(f"后端返回AI概览分析结果")
            return jsonify(data)
        else:
            print(f"AI概览分析API错误: {response.status_code}, 响应: {response.text}")
            return jsonify({
                'error': True,
                'message': f'后端API错误: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"连接AI概览分析API失败: {e}")
        return jsonify({
            'error': True,
            'message': f'连接后端失败: {str(e)}'
        }), 500

@app.route('/ai/analyze_file', methods=['POST'])
def ai_analyze_file():
    """AI文件分析代理接口"""
    try:
        data = request.get_json()
        print(f"前端代理调用: /ai/analyze_file")
        
        response = requests.post(f"{BACKEND_URL}/ai/analyze_file", json=data)
        if response.status_code == 200:
            data = response.json()
            print(f"后端返回AI文件分析结果")
            return jsonify(data)
        else:
            print(f"AI文件分析API错误: {response.status_code}, 响应: {response.text}")
            return jsonify({
                'error': True,
                'message': f'后端API错误: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"连接AI文件分析API失败: {e}")
        return jsonify({
            'error': True,
            'message': f'连接后端失败: {str(e)}'
        }), 500

@app.route('/ai/analyze_function', methods=['POST'])
def ai_analyze_function():
    """AI函数分析代理接口"""
    try:
        data = request.get_json()
        print(f"前端代理调用: /ai/analyze_function")
        
        response = requests.post(f"{BACKEND_URL}/ai/analyze_function", json=data)
        if response.status_code == 200:
            data = response.json()
            print(f"后端返回AI函数分析结果")
            return jsonify(data)
        else:
            print(f"AI函数分析API错误: {response.status_code}, 响应: {response.text}")
            return jsonify({
                'error': True,
                'message': f'后端API错误: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"连接AI函数分析API失败: {e}")
        return jsonify({
            'error': True,
            'message': f'连接后端失败: {str(e)}'
        }), 500

@app.route('/ai/analyze_call_chain', methods=['POST'])
def ai_analyze_call_chain():
    """调用链分析代理"""
    try:
        data = request.get_json()
        response = requests.post(f"{BACKEND_URL}/ai/analyze_call_chain", json=data)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': True, 'message': f'后端连接失败: {str(e)}'}), 500

@app.route('/ai/analyze_variable', methods=['POST'])
def ai_analyze_variable():
    """变量分析代理"""
    try:
        data = request.get_json()
        response = requests.post(f"{BACKEND_URL}/ai/analyze_variable", json=data)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': True, 'message': f'后端连接失败: {str(e)}'}), 500

@app.route('/ai/analyze_pointer', methods=['POST'])
def ai_analyze_pointer():
    """指针分析代理"""
    try:
        data = request.get_json()
        response = requests.post(f"{BACKEND_URL}/ai/analyze_pointer", json=data)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': True, 'message': f'后端连接失败: {str(e)}'}), 500

@app.route('/api/ai_query', methods=['POST'])
def ai_query_gateway():
    """AI查询网关代理"""
    try:
        data = request.get_json()
        response = requests.post(f"{BACKEND_URL}/api/ai_query", json=data)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': True, 'message': f'后端连接失败: {str(e)}'}), 500

if __name__ == "__main__":
    print("🚀 启动内核源码分析系统 - Tab版本")
    print("📡 连接后端API:", BACKEND_URL)
    print("🌐 前端服务地址: http://localhost:5001")
    print("")
    app.run(debug=True, port=5001)
