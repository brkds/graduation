function generateTooltipContent(nodeData) {
  const { type, label, data } = nodeData;

  // 图标定义
  const ICONS = {
    function: 'ƒ',
    variable: '𝓋',
    data_pointer: '→',
    function_pointer: '↦',
    return: '↩',
    params: '(…)',
    location: '<img src="static/icons/akar-icons--location.svg"  width="18" height="18">',
    static: '🅢',
    line: '⎸'
  };

  let content = `
    <div class="tooltip-header">
      <span class="node-type ${type}">${ICONS[type] || '•'} ${type}</span>
      <strong>${label}</strong>
    </div>
    <div class="tooltip-section">
  `;

  switch (type) {
    case 'function':
      content += `
        <div><span class="icon">${ICONS.return}</span> <strong>Returns:</strong> <code>${data.return_type}</code></div>
        <div><span class="icon">${ICONS.params}</span> <strong>Params:</strong> <code>${data.parameters}</code></div>
        <div><span class="icon">${ICONS.location}</span> <strong>Lines:</strong> ${data.location.start_line}-${data.location.end_line}</div>
      `;
      break;

    case 'variable':
      content += `
        <div><span class="icon">𝓋</span> <strong>Type:</strong> <code>${data.var_type}</code></div>
        <div><span class="icon">${ICONS.static}</span> <strong>Static:</strong> ${data.is_static ? 'Yes' : 'No'}</div>
        <div><span class="icon">${ICONS.line}</span> <strong>Defined at:</strong> line ${data.line_number}</div>
      `;
      break;

    case 'data_pointer':
      content += `
        <div><span class="icon">${ICONS.data_pointer}</span> <strong>Target:</strong> var[${data.points_to_var_id}]</div>
        <div><span class="icon">${ICONS.line}</span> <strong>At:</strong> line ${data.line_number}</div>
      `;
      break;

    case 'function_pointer':
      content += `
        <div><span class="icon">${ICONS.function_pointer}</span> <strong>Calls:</strong> func[${data.points_to_func_id}]</div>
        <div><span class="icon">${ICONS.line}</span> <strong>At:</strong> line ${data.line_number}</div>
      `;
      break;
  }

  return content + `</div>`;
}


function createEdgeTooltip(params, edges) {
  const edge = edges.get(params.edge);
  if (!edge) return () => {};

  // 统一使用节点相同的DOM结构
  const tooltip = document.createElement('div');
  tooltip.className = 'network-tooltip';

  // 确定类型显示文本
  let typeText = edge.type;
  if (edge.access_type) typeText = `${edge.type}.${edge.access_type}`;

  tooltip.innerHTML = `
    <div class="tooltip-header">
      <span class="node-type ${edge.access_type || edge.type}">
        ${edge.access_type ? '⇄' : '→'} ${typeText}
      </span>
      <strong>${edge.label || 'relationship'}</strong>
    </div>
    <div class="tooltip-section">
      <div><img src="static/icons/akar-icons--location.svg"  width="18" height="18"><strong>Location:</strong> line ${edge.line_number}</div>
      ${edge.from ? `<div>🡐 <strong>From:</strong> node ${edge.from}</div>` : ''}
      ${edge.to ? `<div>🡒 <strong>To:</strong> node ${edge.to}</div>` : ''}
    </div>
  `;

  // 使用相同的定位逻辑
  const { clientX, clientY } = params.event;
  tooltip.style.left = `${clientX + 15}px`;
  tooltip.style.top = `${clientY + 15}px`;
  document.body.appendChild(tooltip);

  return () => tooltip.remove();
}


/**
 * 获取函数体源码
 * @param {string} filename - 文件名
 * @returns {Promise<{code: string, error: string|null}>} - 返回包含代码和错误信息的对象
 */
async function getFunctionBody(filename) {
  try {
    // 1. 发起请求
    const res = await fetch(`http://localhost:5002/func_body?id=${encodeURIComponent(filename)}`);

    // 2. 检查HTTP状态
    if (!res.ok) {
      return {
        code: '',
        error: `HTTP错误: ${res.status} ${res.statusText}`
      };
    }

    // 3. 解析响应数据
    const data = await res.json();
console.log('响应数据:', data);
    // 4. 验证响应结构
    if (!data.functions[0].source_code) {
      return {
        code: '',
        error: '无效的响应格式'
      };
    }

    return data.functions[0].source_code;

  } catch (err) {
    // 5. 捕获网络或解析错误
    console.error(`获取函数体失败 [${filename}]:`, err);
    return {
      code: '',
      error: err.message || '未知错误'
    };
  }
}


function formatTooltipContent(response) {
  const { type, data } = response;

  if (!type || !data) return '';

  const ICONS = {
    function: '<img src="static/icons/mdi--function.svg"  width="18" height="18">',
    variable: '𝓋',
    data_pointer: '→',
    function_pointer: '↦',
    return: '↩',
    params: '(…)',
    location: '<img src="static/icons/akar-icons--location.svg"  width="18" height="18">',
    static: '<img src="static/icons/mdi--alpha-s-circle.svg"  width="15" height="15">',
    line: '⎸'
  };

  let content = `
    <div class="tooltip-header">
      <span class="node-type ${type}">${ICONS[type] || '•'} ${type}</span>
      <strong>${data.name || data.pointer_name || ''}</strong>
    </div>
    <div class="tooltip-section">
  `;

  switch (type) {
    case 'function':
      content += `
        <div><span class="icon">${ICONS.return}</span> <strong>返回类型:</strong> <code>${data.return_type}</code></div>
        <div><span class="icon">${ICONS.params}</span> <strong>参数:</strong> <code>${data.parameters}</code></div>
        <div><span class="icon">${ICONS.location}</span> <strong>位置:</strong> ${data.file_path} (${data.start_line}行)</div>
        <div><span class="icon">${ICONS.static}</span> <strong>是否为静态:</strong> ${data.is_static ? '是' : '否'}</div>
       <div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.5;">
  <strong style="font-size: 15px; color: #333;">访问变量：</strong>
  <ul style="padding-left: 16px; margin: 8px 0;">
    ${data.access_relations.map(rel => `
      <li style="margin-bottom: 6px;">
        <span style="color: #007bff; font-weight: bold;">${rel.access_type}</span>
        <code style="background: #f1f1f1; padding: 2px 4px; border-radius: 4px; color: #d63384;">
          ${rel.variable_type} ${rel.variable_name}
        </code>
        <span style="color: #555;">@ ${rel.access_file}:${rel.access_line}</span>
      </li>
    `).join('')}
  </ul>
</div>
      `;
      break;

    case 'variable':
      content += `
        <div><span class="icon">${ICONS.variable}</span> <strong>类型:</strong> <code>${data.type}</code></div>
        <div><span class="icon">${ICONS.location}</span> <strong>位置:</strong> ${data.file_path}:${data.line_number}</div>
        <div><span class="icon">${ICONS.static}</span> <strong>是否为静态:</strong> ${data.is_static ? '是' : '否'}</div>
        <div><strong>定义:</strong><pre>${data.definition_code}</pre></div>
        <div><strong>被访问:</strong>
          <ul>
            ${data.access_relations.map(rel => `
              <li>
                ${rel.access_type} by <code>${rel.function_name}()</code> at ${rel.access_file}:${rel.access_line}
              </li>`).join('')}
          </ul>
        </div>
      `;
      break;

    case 'function_pointer':
      content += `
        <div><span class="icon">${ICONS.line}</span> <strong>位置:</strong> ${data.file_path}:${data.line_number}</div>
        <div><span class="icon">${ICONS.function_pointer}</span> <strong>指向函数:</strong>
          <code>${data.points_to_function.name}</code>
          (${data.points_to_function.file_path}:${data.points_to_function.start_line})
        </div>
      `;
      break;

    case 'data_pointer':
      content += `
        <div><span class="icon">${ICONS.line}</span> <strong>位置:</strong> ${data.file_path}:${data.line_number}</div>
        <div><span class="icon">${ICONS.data_pointer}</span> <strong>指向变量:</strong>
          <code>${data.points_to_variable.name}</code>
          (${data.points_to_variable.file_path}:${data.points_to_variable.line_number})
        </div>
        <pre>${data.points_to_variable.definition_code}</pre>
      `;
      break;

    default:
      return `<div>未知类型：${type}</div>`;
  }

  content += `</div>`;
  return content;
}




