(function () {
  const LogicFlow = Core.default;

  let lf = null;
  let currentData = null;
  let viewMode = 'plan';

  // -- Topological sort (Kahn's algorithm, mirrors the Python orchestrator) --
  function topologicalLevels(nodes) {
    const fallbackIds = new Set();
    nodes.forEach(n => { if (n.on_error) fallbackIds.add(n.on_error); });

    // Find all nodes transitively dependent on fallback nodes (the error recovery path)
    const fallbackPath = new Set(fallbackIds);
    let changed = true;
    while (changed) {
      changed = false;
      nodes.forEach(n => {
        if (!fallbackPath.has(n.id) && (n.depends_on || []).some(dep => fallbackPath.has(dep))) {
          fallbackPath.add(n.id);
          changed = true;
        }
      });
    }

    const active = nodes.filter(n => !fallbackPath.has(n.id));
    const nodeMap = new Map(active.map(n => [n.id, n]));
    const inDegree = new Map(active.map(n => [n.id, 0]));
    const children = new Map(active.map(n => [n.id, []]));

    active.forEach(n => {
      (n.depends_on || []).forEach(dep => {
        if (nodeMap.has(dep)) {
          inDegree.set(n.id, (inDegree.get(n.id) || 0) + 1);
          children.get(dep).push(n.id);
        }
      });
    });

    const levels = [];
    let queue = [...inDegree.entries()].filter(([, d]) => d === 0).map(([id]) => id);

    while (queue.length > 0) {
      levels.push(queue.map(id => nodeMap.get(id)));
      const next = [];
      queue.forEach(id => {
        (children.get(id) || []).forEach(child => {
          inDegree.set(child, inDegree.get(child) - 1);
          if (inDegree.get(child) === 0) next.push(child);
        });
      });
      queue = next;
    }

    // Topological sort for the fallback path (fallback nodes + their dependents)
    const fallbackGroup = nodes.filter(n => fallbackPath.has(n.id));
    if (fallbackGroup.length > 0) {
      const fbNodeMap = new Map(fallbackGroup.map(n => [n.id, n]));
      const fbInDegree = new Map(fallbackGroup.map(n => [n.id, 0]));
      const fbChildren = new Map(fallbackGroup.map(n => [n.id, []]));

      fallbackGroup.forEach(n => {
        (n.depends_on || []).forEach(dep => {
          if (fbNodeMap.has(dep)) {
            fbInDegree.set(n.id, (fbInDegree.get(n.id) || 0) + 1);
            fbChildren.get(dep).push(n.id);
          }
        });
      });

      let fbQueue = [...fbInDegree.entries()].filter(([, d]) => d === 0).map(([id]) => id);
      while (fbQueue.length > 0) {
        levels.push(fbQueue.map(id => fbNodeMap.get(id)));
        const next = [];
        fbQueue.forEach(id => {
          (fbChildren.get(id) || []).forEach(child => {
            fbInDegree.set(child, fbInDegree.get(child) - 1);
            if (fbInDegree.get(child) === 0) next.push(child);
          });
        });
        fbQueue = next;
      }
    }

    return levels;
  }

  // -- Build LogicFlow graph data from DAG --
  function buildGraphData(dag, results) {
    const nodes = dag.nodes || [];
    const levels = topologicalLevels(nodes);
    const fallbackIds = new Set();
    nodes.forEach(n => { if (n.on_error) fallbackIds.add(n.on_error); });

    // Compute full fallback path (fallback nodes + their dependents)
    const fallbackPath = new Set(fallbackIds);
    let changed = true;
    while (changed) {
      changed = false;
      nodes.forEach(n => {
        if (!fallbackPath.has(n.id) && (n.depends_on || []).some(dep => fallbackPath.has(dep))) {
          fallbackPath.add(n.id);
          changed = true;
        }
      });
    }

    const NODE_W = 180;
    const NODE_H = 50;
    const GAP_X = 250;
    const GAP_Y = 100;

    const lfNodes = [];
    const lfEdges = [];

    const nodePositions = new Map();
    const totalHeight = Math.max(...levels.map(l => l.length)) * GAP_Y;

    levels.forEach((level, levelIdx) => {
      const isFallbackLevel = level.some(n => fallbackPath.has(n.id));
      const levelHeight = level.length * GAP_Y;
      const offsetY = (totalHeight - levelHeight) / 2;

      level.forEach((node, nodeIdx) => {
        const x = 150 + levelIdx * GAP_X;

        // Try to align with parent nodes when possible
        const parentYs = (node.depends_on || [])
          .filter(dep => nodePositions.has(dep))
          .map(dep => nodePositions.get(dep));

        let y;
        if (parentYs.length > 0 && level.length === 1) {
          // Single node in level: place at average of parents
          y = parentYs.reduce((a, b) => a + b, 0) / parentYs.length;
        } else {
          y = 80 + offsetY + nodeIdx * GAP_Y;
        }

        if (isFallbackLevel) {
          y += GAP_Y;
        }

        nodePositions.set(node.id, y);

        let fill = '#2563eb';
        let stroke = '#3b82f6';
        const fontColor = '#ffffff';

        if (fallbackIds.has(node.id)) {
          fill = '#b91c1c';
          stroke = '#ef4444';
        } else if (node.tool === 'check_condition') {
          fill = '#7c3aed';
          stroke = '#a78bfa';
        } else if (node.on_error) {
          fill = '#d97706';
          stroke = '#f59e0b';
        }

        if (results && results[node.id]) {
          const r = results[node.id];
          if (r._skipped) {
            fill = '#4b5563';
            stroke = '#6b7280';
          } else if (r._error) {
            fill = '#dc2626';
            stroke = '#ef4444';
          } else {
            fill = '#16a34a';
            stroke = '#22c55e';
          }
        }

        const label = `${node.id}\n(${node.tool})`;

        lfNodes.push({
          id: node.id,
          type: 'rect',
          x,
          y,
          text: { x, y: y - 5, value: label },
          properties: {
            width: NODE_W,
            height: NODE_H,
            style: { fill, stroke, strokeWidth: 2, radius: 8, fillOpacity: 0.65 },
            textStyle: { color: fontColor, fontSize: 11 },
            nodeData: { tool: node.tool, params: node.params || {} },
          },
        });
      });
    });

    nodes.forEach(node => {
      (node.depends_on || []).forEach(dep => {
        lfEdges.push({
          type: 'polyline',
          sourceNodeId: dep,
          targetNodeId: node.id,
          properties: { style: { stroke: '#9ca3af', strokeWidth: 2 } },
        });
      });

      if (node.on_error) {
        lfEdges.push({
          type: 'polyline',
          sourceNodeId: node.id,
          targetNodeId: node.on_error,
          text: 'on_error',
          properties: {
            style: { stroke: '#f87171', strokeWidth: 1.5, strokeDasharray: '6 3' },
          },
        });
      }
    });

    return { nodes: lfNodes, edges: lfEdges };
  }

  // -- Render --
  function renderDag(data) {
    currentData = data;
    const { run_id, dag, results } = data;

    document.getElementById('dag-info').classList.remove('hidden');
    document.getElementById('info-run').textContent = run_id;
    document.getElementById('info-desc').textContent = dag.description || '-';
    document.getElementById('info-nodes').textContent = (dag.nodes || []).length;

    const effectiveResults = viewMode === 'result' ? results : null;
    const graphData = buildGraphData(dag, effectiveResults);

    if (lf) {
      lf.render(graphData);
    } else {
      lf = new LogicFlow({
        container: document.getElementById('canvas'),
        grid: { type: 'dot', size: 20, config: { color: '#d1d5db', thickness: 1 } },
        keyboard: { enabled: true },
        edgeType: 'polyline',
        nodeTextEdit: false,
        edgeTextEdit: false,
        isSilentMode: false,
        stopZoomGraph: false,
        stopScrollGraph: false,
        adjustEdgeStartAndEnd: true,
        style: {
          rect: { width: 180, height: 50, radius: 8 },
          nodeText: { fontSize: 11, color: '#ffffff', overflowMode: 'ellipsis' },
          polyline: { stroke: '#9ca3af', strokeWidth: 2 },
          edgeText: { fontSize: 12, color: '#dc2626', background: { fill: '#ffffff', stroke: 'transparent' } },
        },
      });

      lf.on('node:click', ({ data }) => {
        showNodeDetail(data.id, data.properties);
      });
      lf.on('blank:click', hideNodeDetail);

      lf.render(graphData);
    }

    lf.fitView(300);
  }

  // -- API calls --
  function showError(msg) {
    const banner = document.getElementById('error-banner');
    banner.textContent = msg;
    banner.classList.remove('hidden');
    setTimeout(() => banner.classList.add('hidden'), 5000);
  }

  async function loadRuns() {
    try {
      const res = await fetch('/api/runs');
      const data = await res.json();
      const select = document.getElementById('run-select');
      select.innerHTML = '';

      if (!data.runs || data.runs.length === 0) {
        select.innerHTML = '<option value="">No runs found</option>';
        return;
      }

      data.runs.forEach((run, i) => {
        const opt = document.createElement('option');
        opt.value = run;
        opt.textContent = run + (i === 0 ? ' (latest)' : '');
        select.appendChild(opt);
      });

      loadRun(data.runs[0]);
    } catch (e) {
      showError('Failed to load runs: ' + e.message);
    }
  }

  async function loadRun(runId) {
    try {
      const res = await fetch(`/api/runs/${runId}`);
      if (!res.ok) {
        const err = await res.json();
        showError(err.error || 'Failed to load run');
        return;
      }
      const data = await res.json();
      renderDag(data);
    } catch (e) {
      showError('Failed to load DAG: ' + e.message);
    }
  }

  // -- Node detail panel --
  const detailPanel = document.getElementById('node-detail');
  const detailTitle = document.getElementById('detail-title');
  const detailTool = document.getElementById('detail-tool');
  const detailParams = document.getElementById('detail-params');

  function showNodeDetail(nodeId, properties) {
    if (viewMode !== 'plan') return;

    const { nodeData } = properties;
    if (!nodeData) return;

    detailTitle.textContent = nodeId;
    detailTool.textContent = nodeData.tool;

    const params = nodeData.params;
    const keys = Object.keys(params);

    if (keys.length === 0) {
      detailParams.innerHTML = '<p class="text-xs text-gray-400 italic">No params</p>';
    } else {
      detailParams.innerHTML = keys.map(key => {
        const val = typeof params[key] === 'object'
          ? JSON.stringify(params[key], null, 2)
          : String(params[key]);
        return `
          <div class="flex gap-2 py-1.5 border-b border-gray-50 last:border-0">
            <span class="text-xs font-medium text-gray-500 shrink-0">${key}:</span>
            <span class="text-xs font-mono text-gray-800 break-all">${val}</span>
          </div>`;
      }).join('');
    }

    detailPanel.classList.remove('hidden');
  }

  function hideNodeDetail() {
    detailPanel.classList.add('hidden');
  }

  document.getElementById('detail-close').addEventListener('click', hideNodeDetail);

  // -- Event listeners --
  document.getElementById('run-select').addEventListener('change', (e) => {
    if (e.target.value) loadRun(e.target.value);
  });

  document.getElementById('btn-refresh').addEventListener('click', loadRuns);

  document.getElementById('view-toggle').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-view]');
    if (!btn || btn.dataset.view === viewMode) return;

    viewMode = btn.dataset.view;
    document.querySelectorAll('#view-toggle [data-view]').forEach(b => {
      b.classList.remove('bg-blue-600', 'text-white');
      b.classList.add('text-gray-500', 'hover:text-gray-800');
    });
    btn.classList.remove('text-gray-500', 'hover:text-gray-800');
    btn.classList.add('bg-blue-600', 'text-white');

    hideNodeDetail();
    if (currentData) renderDag(currentData);
  });

  // -- Init --
  loadRuns();
})();
