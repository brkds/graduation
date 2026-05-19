import json
import os
from pyvis.network import Network

json_path = "../output/single.json"
if not os.path.exists(json_path):
    print(f"File not found: {json_path}")
    exit(1)

with open(json_path) as f:
    data = json.load(f)

net = Network(height="900px", width="100%", directed=True, notebook=False)

# 关闭物理弹簧模拟，用静态布局
net.set_options("""
{
  "physics": {
    "enabled": false
  },
  "interaction": {
    "hover": true,
    "multiselect": false,
    "navigationButtons": true,
    "zoomView": true
  },
  "nodes": {
    "font": {
      "size": 24
    }
  }
}
""")

# 简化物理模拟
# net.set_options("""
# {
#   "layout": {
#     "randomSeed": 42
#   },
#   "physics": {
#     "enabled": true,
#     "barnesHut": {
#       "gravitationalConstant": -2000,
#       "centralGravity": 0.3,
#       "springLength": 150,
#       "springConstant": 0.01,
#       "damping": 0.09,
#       "avoidOverlap": 1
#     }
#   },
#   "interaction": {
#     "hover": true,
#     "multiselect": false,
#     "navigationButtons": true,
#     "zoomView": true
#   },
#   "nodes": {
#     "font": {
#       "size": 24
#     }
#   }
# }
# """)


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
        font={'size': 24}  # 适中字体，平衡性能
    )

for src, dst, label in edges:
    style = edge_styles.get(label, {'color': 'gray', 'dashes': False})
    net.add_edge(
        src, dst, label=label, title=label,
        color=style["color"], arrows="to", dashes=style["dashes"]
    )

output_html = "../output/var_access_graph_light.html"
net.write_html(output_html)


def inject_filter_ui_light(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 只保留复选框过滤和点击弹窗
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
      #filter-container {
        position: fixed;
        top: 10px;
        left: 10px;
        background: white;
        padding: 10px;
        border: 1px solid black;
        z-index: 9999;
      }
    </style>

    <div id="filter-container">
      <strong>Filter nodes by type:</strong><br>
      <label><input type="checkbox" class="group-filter" value="var" checked> Variables</label><br>
      <label><input type="checkbox" class="group-filter" value="fn" checked> Functions</label><br>
      <label><input type="checkbox" class="group-filter" value="ptr" checked> Pointers</label><br>
    </div>

    <div id="info-panel"></div>

    <script>
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

      network.on("click", function(params) {
        var infoPanel = document.getElementById("info-panel");
        if (params.nodes.length === 1) {
          var nodeId = params.nodes[0];
          var node = nodes.get(nodeId);
          var html = "<h3>Node Details</h3>";
          html += "<b>ID:</b> " + node.id + "<br>";
          html += "<b>Label:</b> " + node.label + "<br>";
          html += "<b>Group:</b> " + node.group + "<br>";
          html += "<b>Title:</b> " + (node.title || "N/A") + "<br>";
          infoPanel.innerHTML = html;
          infoPanel.style.display = "block";
        } else {
          infoPanel.style.display = "none";
        }
      });

      updateVisibility();
    </script>
    """

    html = html.replace("<body>", "<body>\n" + filter_html)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

inject_filter_ui_light(output_html)

print(f"✅ Lightweight interactive graph saved to: {output_html}")
