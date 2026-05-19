/**
 * 用 d3-force 预计算节点坐标
 * @param {Array} nodes - 节点数组 [{ id: string }, ...]
 * @param {Array} edges - 边数组 [{ source: string, target: string }, ...]
 * @param {number} iterations - 迭代次数（默认 50）
 * @returns {Array} - 带坐标的节点数组 [{ id, x, y }, ...]
 */
function computeLayout(nodes, edges, iterations = 50) {
  // 1. 深拷贝节点（避免修改原数据）
  const nodesWithPos = JSON.parse(JSON.stringify(nodes));

  // 2. 运行力导向布局
  const simulation = d3.forceSimulation(nodesWithPos)
    .force("charge", d3.forceManyBody().strength(-100))  // 节点斥力
    .force("link", d3.forceLink(edges).id(d => d.id).distance(100)) // 边拉力
    .force("center", d3.forceCenter(0, 0))  // 居中
    .stop(); // 手动控制迭代

  // 3. 预计算迭代
  for (let i = 0; i < iterations; i++) simulation.tick();

  // 4. 返回带坐标的节点
  return nodesWithPos.map(node => ({
    id: node.id,
    x: node.x,
    y: node.y
  }));
}

// 暴露函数给全局作用域
window.computeLayout = computeLayout;