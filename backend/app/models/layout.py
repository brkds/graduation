import networkx as nx
from typing import List, Dict, Any


#该函数不仅仅是布局，还有连通图
import networkx as nx
from typing import List, Dict, Any

def compute_graph_layout(
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        layout: str = "spring",
        scale: float = 1000,
        **layout_kwargs
) -> Dict[str, List[Dict[str, Any]]]:
    """
    NetworkX 版本 (支持多种布局算法)
    支持布局类型:
    - "spring" (默认, 力导向)
    - "kamada_kawai" (另一种力导向)
    - "circular"
    - "random"
    - "shell" (同心圆)
    """
    G = nx.Graph()
    G.add_nodes_from(str(n['id']) for n in nodes)

    # 先加边
    valid_edges = []
    for edge in edges:
        if all(k in edge for k in ('from', 'to')):
            valid_edges.append((str(edge['from']), str(edge['to'])))
    if valid_edges:
        G.add_edges_from(valid_edges)

    # 计算连通分组
    connected_components = list(nx.connected_components(G))
    node_to_group = {}
    for i, component in enumerate(connected_components):
        for node_id in component:
            node_to_group[node_id] = i  # group 编号用数字即可

    # 选择布局算法
    layout_selector = {
        "spring": lambda: nx.spring_layout(
            G,
            k=layout_kwargs.get('k', 0.9),
            iterations=layout_kwargs.get('iterations', 50),
            seed=42
        ),
        "kamada_kawai": lambda: nx.kamada_kawai_layout(G, scale=2),
        "circular": nx.circular_layout,
        "random": nx.random_layout,
        "shell": lambda: nx.shell_layout(G, nlist=[list(G.nodes)[i::3] for i in range(3)])
    }

    # 快速硬编码布局：按类型分组并在网格上定位，避免迭代计算
    if layout in ("fast", "hardcoded", "static"):
        # 分组顺序与每组的基准 Y 行
        group_order = [
            ("function", 0),
            ("variable", 1),
            ("data_pointer", 2),
            ("function_pointer", 3)
        ]
        type_to_row = {t: row for t, row in group_order}

        # 将节点按类型分组
        grouped = {t: [] for t, _ in group_order}
        for n in nodes:
            grouped.setdefault(n.get("type", "function"), []).append(n)

        # 计算每组的网格布局
        pos = {}
        x_gap = layout_kwargs.get('x_gap', 140)
        y_gap = layout_kwargs.get('y_gap', 160)
        max_cols = layout_kwargs.get('max_cols', 8)

        for t, row in group_order:
            items = grouped.get(t, [])
            if not items:
                continue
            cols = min(max_cols, max(1, int(len(items) ** 0.5) + 1))
            for idx, n in enumerate(items):
                col = idx % cols
                r = idx // cols
                x = (col - cols / 2) * x_gap
                y = (row * y_gap) + (r * (y_gap * 0.8))
                pos[str(n['id'])] = (x / scale, y / scale)
    else:
        try:
            pos = layout_selector.get(layout, layout_selector["spring"])()
        except Exception as e:
            print(f"布局计算失败，使用圆形布局: {str(e)}")
            pos = nx.circular_layout(G)

    # 返回节点时添加 group 信息
    return {
        "nodes": [{
            **node,
            "x": round(float(pos[str(node['id'])][0]) * scale, 2),
            "y": round(float(pos[str(node['id'])][1]) * scale, 2),
            "size": node.get('size', 20),
            "originalSize": node.get('size', 20),
            "originalLabel": node.get("label", ""),
            "connectivity_group": node_to_group.get(str(node['id']), -1)  # 没找到归为 -1
        } for node in nodes],
        "edges": [  # 边列表
            {
                **edge,
                "connectivity_group": node_to_group.get(str(edge['from']), -1),
                "originalLabel": edge.get("label", ""),
            }
            for edge in edges
        ]
    }



from typing import List, Dict

EDGE_COLOR_MAP = {
    "func_points_to": "#FF0000",
    "data_points_to": "#AA00FF",
    "access.read": "#00C853",
    "access.write": "#FF6D00",
    "default": "#757575"
}

def get_edge_color(edge: Dict) -> str:
    if "access_type" in edge and edge["access_type"]:
        full_type = f"{edge['type']}.{edge['access_type']}"
        return EDGE_COLOR_MAP.get(full_type, EDGE_COLOR_MAP["default"])
    return EDGE_COLOR_MAP.get(edge.get("type"), EDGE_COLOR_MAP["default"])

def process_edges_with_color(edges: List[Dict]) -> List[Dict]:
    return [
        {**edge, "color": get_edge_color(edge),"original_color": get_edge_color(edge)}
        for edge in edges
    ]


GROUP_COLOR_MAP = {
    "function": {
        "background": "#3b82f6",
        "border": "#3b82f6",
    },
    "variable": {
        "background": "#10b981",
        "border": "#10b981",
    },
    "data_pointer": {
        "background": "#8b5cf6",
        "border": "#8b5cf6",
    },
    "function_pointer": {
        "background": "#ec4899",
        "border": "#ec4899",
    },
    "default": {
        "background": "#BDBDBD",
        "border": "#9E9E9E"
    }
}

def process_nodes_with_color(nodes: List[Dict]) -> List[Dict]:
    result = []
    for node in nodes:
        group = node.get("type", "default")
        color = GROUP_COLOR_MAP.get(group, GROUP_COLOR_MAP["default"])
        # 外部节点统一灰色显示
        label_text = str(node.get("label", ""))
        if "外部" in label_text:
            color = {
                "background": "#9CA3AF",  # gray-400
                "border": "#6B7280"       # gray-500
            }
        result.append({
            **node,
            "color": color,
            "original_color": color
        })
    return result


def get_connected_subgraph(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    target_node_id: str,
    max_depth: int = 3
) -> Dict[str, List[Dict[str, Any]]]:
    """
    获取与指定节点连通的所有节点和边（限制深度避免过大的子图）
    
    Args:
        nodes: 所有节点列表
        edges: 所有边列表
        target_node_id: 目标节点ID
        max_depth: 最大连通深度，避免过大的子图
    
    Returns:
        包含连通节点和边的字典
    """
    if not nodes or not edges:
        return {"nodes": [], "edges": []}
    
    # 构建图结构
    G = nx.Graph()
    
    # 添加所有节点
    for node in nodes:
        G.add_node(str(node['id']))
    
    # 添加所有边
    for edge in edges:
        if 'from' in edge and 'to' in edge:
            G.add_edge(str(edge['from']), str(edge['to']))
    
    # 检查目标节点是否存在
    target_id_str = str(target_node_id)
    if target_id_str not in G:
        return {"nodes": [], "edges": []}
    
    # 使用BFS查找连通节点（限制深度）
    connected_nodes = set()
    connected_edges = set()
    
    # BFS队列：(节点ID, 深度)
    queue = [(target_id_str, 0)]
    visited = {target_id_str}
    
    while queue:
        current_node, depth = queue.pop(0)
        connected_nodes.add(current_node)
        
        # 如果达到最大深度，不再继续扩展
        if depth >= max_depth:
            continue
        
        # 查找所有相邻节点
        for neighbor in G.neighbors(current_node):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, depth + 1))
                
                # 添加连接边
                edge_key = tuple(sorted([current_node, neighbor]))
                connected_edges.add(edge_key)
    
    # 过滤节点和边
    filtered_nodes = [
        node for node in nodes 
        if str(node['id']) in connected_nodes
    ]
    
    filtered_edges = [
        edge for edge in edges
        if ('from' in edge and 'to' in edge and 
             tuple(sorted([str(edge['from']), str(edge['to'])])) in connected_edges)
    ]
    
    return {
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "filtered_nodes": len(filtered_nodes),
        "filtered_edges": len(filtered_edges),
        "target_node": target_node_id
    }
