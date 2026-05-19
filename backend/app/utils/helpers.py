"""
辅助工具函数模块
"""
import os
from typing import List, Optional

def normalize_file_path(file_path: str, workspace_root: str = "/home/zwy/project2721707-302151") -> str:
    """
    标准化文件路径
    
    Args:
        file_path: 需要标准化的文件路径
        workspace_root: 工作空间根目录
    
    Returns:
        标准化后的相对路径
    """
    if file_path.startswith(workspace_root):
        return file_path[len(workspace_root):].lstrip('/')
    return file_path

def find_file_paths(file_path: str, workspace_root: str = "/home/zwy/project2721707-302151") -> List[str]:
    """
    根据给定路径生成多个可能的文件路径候选
    
    Args:
        file_path: 原始文件路径
        workspace_root: 工作空间根目录
    
    Returns:
        可能的文件路径列表
    """
    # ========== 路径映射配置区域 ==========
    # 配置说明：如果您的linux-6.6源码目录位置与原数据库不同，请修改此配置
    # 格式：{数据库中的路径前缀: 您本地的实际路径前缀}
    PATH_MAPPING_CONFIG = {
        # 原始数据库路径 -> 您的本地路径（请根据实际情况修改）
        "/home/zwy/project2721707-302151/testdata/linux_full/linux-6.6": "/home/zwy/project2721707-302151/testdata/linux_full/linux-6.6",
        "/home/lbz/test2/project2721707-302151/testdata/linux-6.6": "/home/zwy/project2721707-302151/testdata/linux_full/linux-6.6",
        
        # 可添加更多映射，如果您的linux-6.6在其他位置，请添加如下配置：
        # "/原始路径": "/您的linux-6.6路径",
        # 示例：
        # "/home/zwy/project2721707-302151/testdata/linux_full/linux-6.6": "/home/user/linux-6.6",
        # "/home/lbz/test2/project2721707-302151/testdata/linux-6.6": "/home/user/linux-6.6",
    }
    
    # 常用路径后缀，自动尝试添加这些后缀查找linux-6.6
    COMMON_LINUX_PATHS = [
        "testdata/linux_full/linux-6.6",
        "testdata/linux-6.6", 
        "linux-6.6",
        "data/linux-6.6",
        "src/linux-6.6"
    ]
    # ========================================
    
    possible_paths = []
    
    # 1. 原始路径
    possible_paths.append(file_path)
    
    # 2. 应用路径映射配置
    mapped_paths = []
    for old_prefix, new_prefix in PATH_MAPPING_CONFIG.items():
        if file_path.startswith(old_prefix):
            mapped_path = file_path.replace(old_prefix, new_prefix, 1)
            mapped_paths.append(mapped_path)
            print(f"路径映射: {file_path} -> {mapped_path}")
    
    possible_paths.extend(mapped_paths)
    
    # 3. 标准化路径
    normalized = normalize_file_path(file_path, workspace_root)
    if normalized != file_path:
        possible_paths.append(normalized)
    
    # 4. 绝对路径
    if not os.path.isabs(file_path):
        abs_path = os.path.join(workspace_root, file_path)
        possible_paths.append(abs_path)
    
    # 5. 当前目录相对路径
    if not file_path.startswith('./'):
        possible_paths.append(f"./{file_path}")
    
    # 6. 尝试常用linux-6.6路径组合
    # 提取相对于linux-6.6的路径部分
    if "linux-6.6/" in file_path:
        relative_part = file_path.split("linux-6.6/", 1)[1]
        for common_path in COMMON_LINUX_PATHS:
            # 尝试工作空间根目录 + 常用路径 + 相对路径
            candidate_path = os.path.join(workspace_root, common_path, relative_part)
            possible_paths.append(candidate_path)
            
            # 尝试当前目录 + 常用路径 + 相对路径
            candidate_path = os.path.join(common_path, relative_part)
            possible_paths.append(candidate_path)
    
    return list(set(possible_paths))  # 去重

def safe_read_file(file_path: str, start_line: int = None, end_line: int = None, 
                   encoding: str = 'utf-8') -> Optional[str]:
    """
    安全读取文件内容
    
    Args:
        file_path: 文件路径
        start_line: 开始行号（1开始）
        end_line: 结束行号（1开始，包含）
        encoding: 文件编码
    
    Returns:
        文件内容或None（如果读取失败）
    """
    try:
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            if start_line is None and end_line is None:
                return f.read()
            
            lines = f.readlines()
            
            if start_line is not None:
                start_idx = max(0, start_line - 1)  # 转为0索引
            else:
                start_idx = 0
            
            if end_line is not None:
                end_idx = min(len(lines), end_line)  # 包含结束行
            else:
                end_idx = len(lines)
            
            if start_idx < len(lines) and end_idx > start_idx:
                return ''.join(lines[start_idx:end_idx])
            else:
                return f"// 行号范围 {start_line}-{end_line} 超出文件范围 (1-{len(lines)})"
                
    except Exception as e:
        return f"// 读取文件失败: {str(e)}"

def validate_line_range(start_line: int, end_line: int, max_lines: int) -> tuple:
    """
    验证并修正行号范围
    
    Args:
        start_line: 开始行号
        end_line: 结束行号
        max_lines: 文件最大行数
    
    Returns:
        (有效的开始行号, 有效的结束行号)
    """
    start_line = max(1, start_line)
    end_line = min(max_lines, end_line)
    
    if start_line > end_line:
        start_line, end_line = end_line, start_line
    
    return start_line, end_line 