import React, { useEffect, useRef } from 'react';
import type { HistNode, HistEdge } from '../../types';

interface HistTimelineCanvasProps {
  nodes: HistNode[];
  edges: HistEdge[];
  onSelectNode: (nodeId: string) => void;
  selectedNodeId?: string | null;
}

export const HistTimelineCanvas: React.FC<HistTimelineCanvasProps> = ({
  nodes,
  edges,
  onSelectNode,
  selectedNodeId,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    if (nodes.length === 0) {
      ctx.fillStyle = '#64748b';
      ctx.font = '13px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No timeline data loaded. Ingest topics or search graph above.', width / 2, height / 2);
      return;
    }

    const sorted = [...nodes].sort((a, b) => (a.year || 0) - (b.year || 0));

    ctx.beginPath();
    ctx.moveTo(60, height / 2);
    ctx.lineTo(width - 60, height / 2);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 2;
    ctx.stroke();

    const spacing = (width - 120) / Math.max(sorted.length - 1, 1);

    sorted.forEach((node, idx) => {
      const x = 60 + idx * spacing;
      const y = height / 2 + (idx % 2 === 0 ? -45 : 45);
      const isSelected = selectedNodeId === node.node_id;

      ctx.beginPath();
      ctx.moveTo(x, height / 2);
      ctx.lineTo(x, y);
      ctx.strokeStyle = isSelected ? '#00cec9' : 'rgba(255, 255, 255, 0.1)';
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(x, y, isSelected ? 12 : 8, 0, 2 * Math.PI);
      ctx.fillStyle = isSelected ? '#00cec9' : '#6c5ce7';
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.font = isSelected ? 'bold 11px Inter' : '10px Inter';
      ctx.fillStyle = isSelected ? '#ffffff' : '#cbd5e1';
      ctx.textAlign = 'center';
      ctx.fillText(node.name.slice(0, 18), x, y + (idx % 2 === 0 ? -14 : 20));
    });
  }, [nodes, edges, selectedNodeId]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const width = canvas.width;
    const spacing = (width - 120) / Math.max(nodes.length - 1, 1);

    const closestIdx = Math.round((clickX - 60) / spacing);
    if (closestIdx >= 0 && closestIdx < nodes.length) {
      onSelectNode(nodes[closestIdx].node_id);
    }
  };

  return (
    <div className="glass-panel p-4 mb-6 relative overflow-hidden">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-bold text-slate-400 font-mono uppercase tracking-wider">
          HIST Event & Entity Timeline Canvas
        </h4>
        <span className="text-xs text-cyan-400 font-mono">{nodes.length} nodes loaded</span>
      </div>

      <div className="h-64 rounded-xl bg-slate-950/60 overflow-hidden relative">
        <canvas
          ref={canvasRef}
          width={900}
          height={256}
          onClick={handleCanvasClick}
          className="w-full h-full cursor-pointer"
        />
      </div>
    </div>
  );
};
