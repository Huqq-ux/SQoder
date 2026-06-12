import { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/api/client';
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

interface GraphNode {
  id: string;
  name: string;
  section: string;
  source_file?: string;
  mastery?: 'mastered' | 'learning' | 'unlearned';
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  sources: string[];
}

interface Props {
  identifier: string;
}

interface LayoutNode extends GraphNode {
  x: number;
  y: number;
}

const W = 800;
const H = 500;
const MASTERY_COLORS: Record<string, string> = {
  mastered: '#22c55e',
  learning: '#6366f1',
  unlearned: '#94a3b8',
};
const MASTERY_SIZES: Record<string, number> = {
  mastered: 8,
  learning: 7,
  unlearned: 5.5,
};

function runForceLayout(nodes: GraphNode[], edges: GraphEdge[]): LayoutNode[] {
  const layoutNodes: LayoutNode[] = nodes.map((n) => ({
    ...n,
    x: W / 2 + (Math.random() - 0.5) * 200,
    y: H / 2 + (Math.random() - 0.5) * 200,
  }));
  const nodeMap = new Map(layoutNodes.map((n) => [n.id, n]));
  const edgePairs = edges
    .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
    .map((e) => ({ source: nodeMap.get(e.source)!, target: nodeMap.get(e.target)! }));

  for (let iter = 0; iter < 60; iter++) {
    // Reset velocities
    const vx = new Float64Array(layoutNodes.length);
    const vy = new Float64Array(layoutNodes.length);

    // Repulsion
    for (let i = 0; i < layoutNodes.length; i++) {
      for (let j = i + 1; j < layoutNodes.length; j++) {
        const dx = layoutNodes[j].x - layoutNodes[i].x;
        const dy = layoutNodes[j].y - layoutNodes[i].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = 1800 / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        vx[i] -= fx; vy[i] -= fy;
        vx[j] += fx; vy[j] += fy;
      }
    }

    // Attraction
    for (const e of edgePairs) {
      const dx = e.target.x - e.source.x;
      const dy = e.target.y - e.source.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = dist * 0.008;
      vx[nodes.indexOf(e.source)] += (dx / dist) * force;
      vy[nodes.indexOf(e.source)] += (dy / dist) * force;
      vx[nodes.indexOf(e.target)] -= (dx / dist) * force;
      vy[nodes.indexOf(e.target)] -= (dy / dist) * force;
    }

    // Gravity + damping
    const damping = 0.45;
    for (let i = 0; i < layoutNodes.length; i++) {
      layoutNodes[i].x += (vx[i] + (W / 2 - layoutNodes[i].x) * 0.01) * damping;
      layoutNodes[i].y += (vy[i] + (H / 2 - layoutNodes[i].y) * 0.01) * damping;
      layoutNodes[i].x = Math.max(25, Math.min(W - 25, layoutNodes[i].x));
      layoutNodes[i].y = Math.max(20, Math.min(H - 20, layoutNodes[i].y));
    }
  }

  return layoutNodes;
}

export function KnowledgeGraph({ identifier }: Props) {
  const navigate = useNavigate();
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [hovered, setHovered] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [sourceFile, setSourceFile] = useState('');
  const svgRef = useRef<SVGSVGElement>(null);
  const dragging = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const qs = sourceFile ? `?source_file=${encodeURIComponent(sourceFile)}` : '';
        const res = await api.get<GraphData>(`/courses/${identifier}/knowledge-graph${qs}`);
        setData(res);
      } catch {
        setData(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [identifier, sourceFile]);

  // Stable layout: only recompute when data changes
  const layoutNodes = useMemo(() => {
    if (!data || data.nodes.length === 0) return [];
    return runForceLayout(data.nodes, data.edges);
  }, [data]);

  const nodeMap = useMemo(() => new Map(layoutNodes.map((n) => [n.id, n])), [layoutNodes]);
  const edgePairs = useMemo(
    () =>
      data?.edges
        .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
        .map((e) => ({ source: nodeMap.get(e.source)!, target: nodeMap.get(e.target)! })) ?? [],
    [data, nodeMap],
  );

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setScale((prev) => Math.max(0.3, Math.min(3, prev - e.deltaY * 0.001)));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target === svgRef.current || (e.target as Element).tagName === 'svg') {
      dragging.current = true;
      lastPos.current = { x: e.clientX, y: e.clientY };
    }
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging.current) return;
    const dx = e.clientX - lastPos.current.x;
    const dy = e.clientY - lastPos.current.y;
    lastPos.current = { x: e.clientX, y: e.clientY };
    setPan((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
  }, []);

  const handleMouseUp = useCallback(() => {
    dragging.current = false;
  }, []);

  const resetView = () => {
    setScale(1);
    setPan({ x: 0, y: 0 });
  };

  const handleNodeClick = (node: LayoutNode) => {
    navigate(`/course/${identifier}/qa`, { state: { question: `请详细讲解知识点：${node.name}` } });
  };

  if (loading) {
    return <div className="p-8 text-center text-sm" style={{ color: 'var(--text-dim)' }}>加载中...</div>;
  }

  if (!data || data.nodes.length === 0) {
    return <div className="p-8 text-center text-sm" style={{ color: 'var(--text-dim)' }}>暂无知识点数据，请先上传课件</div>;
  }

  const transform = `translate(${pan.x},${pan.y}) scale(${scale})`;

  return (
    <div className="p-4 overflow-hidden select-none">
      {/* File tabs */}
      {data.sources.length > 1 && (
        <div className="flex items-center gap-1 mb-3 flex-wrap">
          <button
            onClick={() => setSourceFile('')}
            className={`px-3 py-1 rounded-md text-xs transition-colors ${
              sourceFile === '' ? 'text-white' : ''
            }`}
            style={{
              background: sourceFile === '' ? 'var(--brand)' : 'var(--surface)',
              border: sourceFile === '' ? 'none' : '1px solid var(--border)',
              color: sourceFile === '' ? undefined : 'var(--text-dim)',
            }}
          >
            全部 ({data.sources.reduce((s, f) => s + (f ? 1 : 0), 0)} 个文件)
          </button>
          {data.sources.map((sf) => (
            <button
              key={sf}
              onClick={() => setSourceFile(sf)}
              className={`px-3 py-1 rounded-md text-xs transition-colors truncate max-w-[200px] ${
                sourceFile === sf ? 'text-white' : ''
              }`}
              title={sf}
              style={{
                background: sourceFile === sf ? 'var(--brand)' : 'var(--surface)',
                border: sourceFile === sf ? 'none' : '1px solid var(--border)',
                color: sourceFile === sf ? undefined : 'var(--text-dim)',
              }}
            >
              {sf}
            </button>
          ))}
        </div>
      )}

      {/* Toolbar */}
      <div className="flex items-center gap-1 mb-2">
        <button
          onClick={() => setScale((s) => Math.min(3, s + 0.2))}
          className="p-1.5 rounded-md transition-colors hover:bg-white/10"
          title="放大"
        >
          <ZoomIn className="h-4 w-4" style={{ color: 'var(--text-dim)' }} />
        </button>
        <button
          onClick={() => setScale((s) => Math.max(0.3, s - 0.2))}
          className="p-1.5 rounded-md transition-colors hover:bg-white/10"
          title="缩小"
        >
          <ZoomOut className="h-4 w-4" style={{ color: 'var(--text-dim)' }} />
        </button>
        <button
          onClick={resetView}
          className="p-1.5 rounded-md transition-colors hover:bg-white/10"
          title="重置"
        >
          <RotateCcw className="h-4 w-4" style={{ color: 'var(--text-dim)' }} />
        </button>
        <span className="text-[10px] ml-2" style={{ color: 'var(--text-dim)' }}>
          滚轮缩放 · 拖拽平移 · 点击节点提问
        </span>
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="w-full rounded-lg cursor-grab active:cursor-grabbing"
        style={{ background: 'var(--surface)', minHeight: 460 }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <g transform={transform}>
          {/* Edges */}
          {edgePairs.map((e, i) => (
            <line
              key={i}
              x1={e.source.x}
              y1={e.source.y}
              x2={e.target.x}
              y2={e.target.y}
              stroke="#94a3b8"
              strokeWidth={0.7}
              opacity={0.35}
            />
          ))}
          {/* Nodes */}
          {layoutNodes.map((n) => {
            const isHover = hovered === n.id;
            const mastery = n.mastery || 'unlearned';
            const color = MASTERY_COLORS[mastery] || MASTERY_COLORS.unlearned;
            const r = (MASTERY_SIZES[mastery] || 5.5) * (1 / scale);
            return (
              <g
                key={n.id}
                onMouseEnter={() => setHovered(n.id)}
                onMouseLeave={() => setHovered(null)}
                onClick={() => handleNodeClick(n)}
                className="cursor-pointer"
              >
                <circle
                  cx={n.x}
                  cy={n.y}
                  r={isHover ? r + 2 : r}
                  fill={color}
                  opacity={isHover ? 1 : 0.75}
                />
                <text
                  x={n.x}
                  y={n.y + 16}
                  textAnchor="middle"
                  className="pointer-events-none"
                  style={{
                    fontSize: isHover ? 11 : 9,
                    fill: 'var(--text)',
                    fontWeight: isHover ? 600 : 400,
                  }}
                >
                  {n.name.length > 10 ? n.name.slice(0, 10) + '…' : n.name}
                </text>
                {isHover && (
                  <text
                    x={n.x}
                    y={n.y - r - 8}
                    textAnchor="middle"
                    className="pointer-events-none"
                    style={{ fontSize: 10, fill: 'var(--text-dim)' }}
                  >
                    {n.section}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 justify-center mt-3">
        <span className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--text-dim)' }}>
          <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: '#22c55e' }} /> 已掌握
        </span>
        <span className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--text-dim)' }}>
          <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: '#6366f1' }} /> 学习中
        </span>
        <span className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--text-dim)' }}>
          <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: '#94a3b8' }} /> 未开始
        </span>
      </div>
    </div>
  );
}
