import { useEffect, useState, useRef } from 'react';
import { api } from '@/api/client';

interface GraphNode {
  id: string;
  name: string;
  section: string;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface Props {
  identifier: string;
}

interface LayoutNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

export function KnowledgeGraph({ identifier }: Props) {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [hovered, setHovered] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get<{ nodes: GraphNode[]; edges: GraphEdge[] }>(
          `/courses/${identifier}/knowledge-graph`
        );
        setData(res);
      } catch {
        setData(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [identifier]);

  if (loading) {
    return <div className="p-8 text-gray-500">加载中...</div>;
  }

  if (!data || data.nodes.length === 0) {
    return <div className="p-8 text-gray-500">暂无知识点数据，请先上传课件</div>;
  }

  // Simple force-directed layout
  const w = 800;
  const h = 500;
  const layoutNodes: LayoutNode[] = data.nodes.map((n) => ({
    ...n,
    x: w / 2 + (Math.random() - 0.5) * 200,
    y: h / 2 + (Math.random() - 0.5) * 200,
    vx: 0,
    vy: 0,
  }));

  const nodeMap = new Map(layoutNodes.map((n) => [n.id, n]));
  const edges = data.edges
    .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
    .map((e) => ({
      source: nodeMap.get(e.source)!,
      target: nodeMap.get(e.target)!,
    }));

  // Run force simulation (simple spring forces, ~30 iterations)
  for (let iter = 0; iter < 50; iter++) {
    for (const n of layoutNodes) {
      n.vx = 0;
      n.vy = 0;
    }
    // Repulsion between all nodes
    for (let i = 0; i < layoutNodes.length; i++) {
      for (let j = i + 1; j < layoutNodes.length; j++) {
        const dx = layoutNodes[j].x - layoutNodes[i].x;
        const dy = layoutNodes[j].y - layoutNodes[i].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = 2000 / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        layoutNodes[i].vx -= fx;
        layoutNodes[i].vy -= fy;
        layoutNodes[j].vx += fx;
        layoutNodes[j].vy += fy;
      }
    }
    // Attraction along edges
    for (const e of edges) {
      const dx = e.target.x - e.source.x;
      const dy = e.target.y - e.source.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = dist * 0.01;
      e.source.vx += (dx / dist) * force;
      e.source.vy += (dy / dist) * force;
      e.target.vx -= (dx / dist) * force;
      e.target.vy -= (dy / dist) * force;
    }
    // Center gravity
    for (const n of layoutNodes) {
      n.vx += (w / 2 - n.x) * 0.01;
      n.vy += (h / 2 - n.y) * 0.01;
    }
    // Apply velocity with damping
    for (const n of layoutNodes) {
      n.x += n.vx * 0.5;
      n.y += n.vy * 0.5;
      n.x = Math.max(30, Math.min(w - 30, n.x));
      n.y = Math.max(20, Math.min(h - 20, n.y));
    }
  }

  // Color by mastery level
  const masteryColors: Record<string, string> = {
    mastered: '#22c55e',
    learning: '#6366f1',
    new: '#94a3b8',
  };
  const getMastery = (n: any): string => n.mastery || 'new';

  return (
    <div className="p-4 overflow-auto">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${w} ${h}`}
        className="w-full max-w-3xl mx-auto rounded-lg"
        style={{ background: 'var(--surface)', minHeight: 500 }}
      >
        {/* Edges */}
        {edges.map((e, i) => (
          <line
            key={i}
            x1={e.source.x}
            y1={e.source.y}
            x2={e.target.x}
            y2={e.target.y}
            stroke="#94a3b8"
            strokeWidth={0.8}
            opacity={0.4}
          />
        ))}
        {/* Nodes */}
        {layoutNodes.map((n) => {
          const isHover = hovered === n.id;
          const mastery = getMastery(n);
          const color = masteryColors[mastery] || '#94a3b8';
          const nodeR = mastery === 'mastered' ? 8 : mastery === 'learning' ? 7 : 5.5;
          return (
            <g
              key={n.id}
              onMouseEnter={() => setHovered(n.id)}
              onMouseLeave={() => setHovered(null)}
              className="cursor-pointer"
            >
              <circle
                cx={n.x}
                cy={n.y}
                r={isHover ? nodeR + 2 : nodeR}
                fill={color}
                opacity={isHover ? 1 : 0.8}
                filter={isHover ? 'drop-shadow(0 0 4px currentColor)' : undefined}
              />
              <text
                x={n.x}
                y={n.y + 16}
                textAnchor="middle"
                className={`text-[10px] fill-gray-700 dark:fill-gray-300 ${
                  isHover ? 'font-semibold' : ''
                }`}
              >
                {n.name.length > 8 ? n.name.slice(0, 8) + '…' : n.name}
              </text>
              {isHover && (
                <text
                  x={n.x + 12}
                  y={n.y - 12}
                  className="text-[11px] fill-gray-500 dark:fill-gray-400"
                >
                  {n.section}
                </text>
              )}
            </g>
          );
        })}
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
        <span className="text-[10px] ml-auto" style={{ color: 'var(--text-dim)' }}>💡 点击节点跳转问答</span>
      </div>
    </div>
  );
}
