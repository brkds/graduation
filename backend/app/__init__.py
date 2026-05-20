from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__, static_folder='../static')
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    CORS(app)
    
    # 注册蓝图 - 带前缀的API
    from app.api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix=Config.API_PREFIX)
    
    # 创建兼容的根路由蓝图
    from flask import Blueprint
    compat_bp = Blueprint('compat', __name__)
    
    # 导入路由函数并添加到兼容蓝图
    from app.api.routes import re_func_tree, get_graph, get_dir_children ,search, search_suggest, search_detail, get_func_body, get_hot_access_variables, get_hot_functions, get_hot_access_functions, get_file_statistics, get_global_statistics, get_function_calls, analyze_path, get_file_content, get_node_graph, ai_analyze_overview, ai_analyze_file, ai_analyze_function, ai_analyze_call_chain, ai_analyze_variable, ai_analyze_pointer
    compat_bp.add_url_rule('/func_tree', 'func_tree', re_func_tree, methods=['GET'])
    compat_bp.add_url_rule('/graph', 'graph', get_graph, methods=['GET'])
    compat_bp.add_url_rule('/search', 'search', search, methods=['GET'])
    compat_bp.add_url_rule('/search_suggest', 'search_suggest', search_suggest, methods=['GET'])
    compat_bp.add_url_rule('/search_detail', 'search_detail', search_detail, methods=['GET'])
    compat_bp.add_url_rule('/func_body', 'func_body', get_func_body, methods=['GET'])
    compat_bp.add_url_rule('/file_content', 'file_content', get_file_content, methods=['GET'])
    compat_bp.add_url_rule('/file_statistics', 'file_statistics', get_file_statistics, methods=['GET'])
    compat_bp.add_url_rule('/global_statistics', 'global_statistics', get_global_statistics, methods=['GET'])
    compat_bp.add_url_rule('/function_calls', 'function_calls', get_function_calls, methods=['GET'])
    # 新增路径分析API
    compat_bp.add_url_rule('/directory_children', 'directory_children', get_dir_children, methods=['GET'])
    compat_bp.add_url_rule('/api/path_analysis', 'path_analysis', analyze_path, methods=['GET'])
    compat_bp.add_url_rule('/node_graph', 'node_graph', get_node_graph, methods=['GET'])
    # 为了兼容性，保持旧的hot_variables路由指向新的函数
    compat_bp.add_url_rule('/hot_variables', 'hot_variables', get_hot_access_variables, methods=['GET'])
    # 添加热点函数相关路由
    compat_bp.add_url_rule('/hot_functions', 'hot_functions', get_hot_functions, methods=['GET'])
    compat_bp.add_url_rule('/hot_access_functions', 'hot_access_functions', get_hot_access_functions, methods=['GET'])
    compat_bp.add_url_rule('/hot_access_variables', 'hot_access_variables', get_hot_access_variables, methods=['GET'])
    
    # 添加AI分析路由
    compat_bp.add_url_rule('/ai/analyze_overview', 'ai_analyze_overview', ai_analyze_overview, methods=['POST'])
    compat_bp.add_url_rule('/ai/analyze_file', 'ai_analyze_file', ai_analyze_file, methods=['POST'])
    compat_bp.add_url_rule('/ai/analyze_function', 'ai_analyze_function', ai_analyze_function, methods=['POST'])
    compat_bp.add_url_rule('/ai/analyze_call_chain', 'ai_analyze_call_chain', ai_analyze_call_chain, methods=['POST'])
    # 补充遗漏的AI变量/指针诊断兼容路由
    compat_bp.add_url_rule('/ai/analyze_variable', 'ai_analyze_variable', ai_analyze_variable, methods=['POST'])
    compat_bp.add_url_rule('/ai/analyze_pointer', 'ai_analyze_pointer', ai_analyze_pointer, methods=['POST'])
    
    # 注册兼容蓝图（不带前缀）
    app.register_blueprint(compat_bp)
    
    # 添加根路由，返回静态页面
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')
    
    return app 