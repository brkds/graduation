import json
import os
from pyvis.network import Network

json_path = "../output/random.json"
if not os.path.exists(json_path):
    print(f"File not found: {json_path}")
    exit(1)

with open(json_path) as f:
    data = json.load(f)

net = Network(height="900px", width="100%", directed=True, notebook=False)
net.barnes_hut()

edge_styles = {
    'read':      {'color': 'green',  'dashes': False},
    'write':     {'color': 'red',    'dashes': False},
    'points_to': {'color': 'blue',   'dashes': True},
    'func_ptr':  {'color': 'purple', 'dashes': [2, 2]},
}

node_info = {}
edges = []

for glob in data.get("globals", []):
    name = glob["name"]
    node_info[name] = f"[var] {name}"

for func in data.get("functions", []):
    name = func["name"]
    node_info[name] = f"[fn] {name}"

for var, accesses in data.get("accesses", {}).items():
    node_info.setdefault(var, f"[var] {var}")
    for acc in accesses:
        func = acc["function"]
        node_info.setdefault(func, f"[fn] {func}")
        edges.append((func, var, acc["access_type"]))

for entry in data.get("func_pointers", []):
    ptr, target = entry["pointer"], entry["points_to"]
    node_info.setdefault(ptr, f"[ptr] {ptr}")
    node_info.setdefault(target, f"[fn] {target}")
    edges.append((ptr, target, "func_ptr"))

for entry in data.get("pointers", []):
    ptr, target = entry["pointer"], entry["points_to"]
    node_info.setdefault(ptr, f"[ptr] {ptr}")
    node_info.setdefault(target, f"[var] {target}")
    edges.append((ptr, target, "points_to"))

# 添加节点时字体放大三倍 font_size 42
for node, label in node_info.items():
    if label.startswith("[var]"):
        group = "var"
    elif label.startswith("[fn]"):
        group = "fn"
    elif label.startswith("[ptr]"):
        group = "ptr"
    else:
        group = "other"
    net.add_node(
        node,
        label=label,
        title=node,
        group=group,
        font={'size': 42}  # 放大字体
    )

for src, dst, label in edges:
    style = edge_styles.get(label, {'color': 'gray', 'dashes': False})
    net.add_edge(
        src, dst, label=label, title=label,
        color=style["color"], arrows="to", dashes=style["dashes"]
    )

output_html = "../output/var_access_graph_interactive.html"
net.write_html(output_html)


def inject_filter_ui(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 下面这个 HTML+JS 代码块新增了：
    # - 搜索框input (id=search-input)
    # - 点击节点弹出详细面板（div#info-panel）
    # - 复选框过滤 (和之前一样)
    # - 放大字体无需修改这里，已在add_node设置完成

    filter_html = """
    <style>
      #info-panel {
        position: fixed;
        top: 10px;
        right: 10px;
        width: 250px;
        max-height: 90vh;
        overflow-y: auto;
        background: #f9f9f9;
        border: 1px solid #ccc;
        padding: 10px;
        font-family: sans-serif;
        font-size: 14px;
        z-index: 9999;
        display: none;
      }
      #search-container {
        position: fixed;
        top: 10px;
        left: 10px;
        background: white;
        padding: 10px;
        border: 1px solid black;
        z-index: 9999;
      }
    </style>

    <div id="search-container">
      <strong>Search node:</strong><br>
      <input type="text" id="search-input" placeholder="Type node label" style="width: 200px;">
      <br><br>
      <strong>Filter nodes by type:</strong><br>
      <label><input type="checkbox" class="group-filter" value="var" checked> Variables</label><br>
      <label><input type="checkbox" class="group-filter" value="fn" checked> Functions</label><br>
      <label><input type="checkbox" class="group-filter" value="ptr" checked> Pointers</label><br>
    </div>

    <div id="info-panel"></div>

    <script>
      // 复选框过滤节点显示/隐藏
      function updateVisibility() {
        var checkboxes = document.querySelectorAll('.group-filter');
        var selectedGroups = [];
        checkboxes.forEach(function(cb) {
          if (cb.checked) selectedGroups.push(cb.value);
        });
        nodes.update(nodes.get().map(function(n) {
          n.hidden = selectedGroups.indexOf(n.group) === -1;
          return n;
        }));
      }
      document.querySelectorAll('.group-filter').forEach(function(cb) {
        cb.addEventListener('change', updateVisibility);
      });

      // 搜索节点功能
      document.getElementById('search-input').addEventListener('input', function() {
        var term = this.value.toLowerCase();
        var allNodes = nodes.get();
        var matchedIds = [];
        allNodes.forEach(function(node) {
          if (node.label && node.label.toLowerCase().indexOf(term) !== -1) {
            matchedIds.push(node.id);
          }
        });

        // 高亮匹配节点，其他节点半透明
        nodes.update(allNodes.map(function(node) {
          if (matchedIds.length === 0) {
            node.color = undefined;  // 重置颜色
            node.hidden = false;    // 全显示
          } else if (matchedIds.indexOf(node.id) !== -1) {
            node.color = undefined; // 高亮节点颜色默认
            node.hidden = false;
          } else {
            node.color = 'rgba(200,200,200,0.4)'; // 半透明灰色
            // node.hidden = true; // 如果想隐藏非匹配节点，可以用这行
          }
          return node;
        }));

        // 如果匹配结果只有一个，自动聚焦
        if (matchedIds.length === 1) {
          network.focus(matchedIds[0], {scale: 1.5, animation: true});
        }
      });

      // 点击节点显示详细信息面板
      network.on("click", function(params) {
        var infoPanel = document.getElementById("info-panel");
        if (params.nodes.length === 1) {
          var nodeId = params.nodes[0];
          var node = nodes.get(nodeId);
          var html = "<h3>Node Details</h3>";
          html += "<b>ID:</b> " + node.id + "<br>";
          html += "<b>Label:</b> " + node.label + "<br>";
          html += "<b>Group:</b> " + node.group + "<br>";
          html += "<b>Title (tooltip):</b> " + (node.title || "N/A") + "<br>";
          infoPanel.innerHTML = html;
          infoPanel.style.display = "block";
        } else {
          // 点击空白或多选时隐藏面板
          infoPanel.style.display = "none";
        }
      });

      // 页面载入时执行一次过滤显示，确保状态正确
      updateVisibility();
    </script>
    """

    html = html.replace("<body>", "<body>\n" + filter_html)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

inject_filter_ui(output_html)

print(f"✅ Interactive graph with filtering, search and info panel saved to: {output_html}")
