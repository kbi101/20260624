import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as d3 from 'd3-force';
import { Network, ZoomIn, ZoomOut, RefreshCw, X, ChevronRight } from 'lucide-react';
import type { GraphAdjacency, Edge, HistNode, HistEdge } from '../../types';

interface ForceGraphViewProps {
  graph?: GraphAdjacency;
  edges?: Edge[];
  rawNodes?: HistNode[];
  rawEdges?: HistEdge[];
  onSelectNodeId?: (nodeId: string) => void;
  selectedNodeId?: string | null;
}

interface NodeItem extends d3.SimulationNodeDatum {
  id: string;
  name: string;
}

interface LinkItem extends d3.SimulationLinkDatum<NodeItem> {
  type: string;
}

export const ForceGraphView: React.FC<ForceGraphViewProps> = ({
  graph,
  edges,
  rawNodes,
  rawEdges,
  onSelectNodeId,
  selectedNodeId,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [internalSelectedNode, setInternalSelectedNode] = useState<string | null>(null);
  const [zoom, setZoom] = useState<number>(1);
  const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  const activeSelectedNode = selectedNodeId !== undefined ? selectedNodeId : internalSelectedNode;

  // Build node data & link list from either UCT graph or HIST rawNodes/rawEdges
  const nodesMap = new Map<string, string>(); // id -> display name
  const links: LinkItem[] = [];

  if (rawNodes && rawNodes.length > 0) {
    rawNodes.forEach((n) => nodesMap.set(n.node_id, n.name || n.node_id));
    if (rawEdges) {
      rawEdges.forEach((e) => {
        if (nodesMap.has(e.src) && nodesMap.has(e.tgt)) {
          links.push({ source: e.src, target: e.tgt, type: e.rel || 'CONNECTED' });
        }
      });
    }
  } else if (graph?.nodes) {
    graph.nodes.forEach((name) => nodesMap.set(name, name));
    if (graph.adjacency) {
      Object.entries(graph.adjacency).forEach(([src, connList]) => {
        connList.forEach((conn) => {
          if (nodesMap.has(conn.name)) {
            links.push({ source: src, target: conn.name, type: conn.edge_type });
          }
        });
      });
    } else if (edges) {
      edges.forEach((e) => {
        if (nodesMap.has(e.from) && nodesMap.has(e.to)) {
          links.push({ source: e.from, target: e.to, type: e.type });
        }
      });
    }
  }

  const nodeList = Array.from(nodesMap.entries()).map(([id, name]) => ({ id, name }));

  if (nodeList.length === 0) return null;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    const nodes: NodeItem[] = nodeList.map((n) => ({ id: n.id, name: n.name }));

    const sim = d3
      .forceSimulation<NodeItem>(nodes)
      .force('charge', d3.forceManyBody().strength(-280))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('link', d3.forceLink<NodeItem, LinkItem>(links).id((d) => d.id).distance(100))
      .force('collide', d3.forceCollide(35));

    let animationFrameId: number;

    const render = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.save();
      ctx.translate(offset.x, offset.y);
      ctx.scale(zoom, zoom);

      // Render links
      links.forEach((link) => {
        const src = link.source as NodeItem;
        const tgt = link.target as NodeItem;
        if (src.x === undefined || src.y === undefined || tgt.x === undefined || tgt.y === undefined) return;

        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);

        const relUpper = (link.type || '').toUpperCase();
        if (relUpper.includes('PREREQ') || relUpper.includes('WAR') || relUpper.includes('FOUGHT')) {
          ctx.strokeStyle = 'rgba(239, 68, 68, 0.5)';
        } else if (relUpper.includes('ENABLE') || relUpper.includes('LED') || relUpper.includes('SERVED')) {
          ctx.strokeStyle = 'rgba(16, 185, 129, 0.5)';
        } else {
          ctx.strokeStyle = 'rgba(168, 85, 247, 0.4)';
        }

        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // Render nodes
      nodes.forEach((node) => {
        if (node.x === undefined || node.y === undefined) return;
        const isSelected = activeSelectedNode === node.id || activeSelectedNode === node.name;

        ctx.beginPath();
        ctx.arc(node.x, node.y, isSelected ? 20 : 14, 0, 2 * Math.PI);
        ctx.fillStyle = isSelected ? 'rgba(168, 85, 247, 0.4)' : 'rgba(0, 206, 201, 0.2)';
        ctx.fill();

        ctx.beginPath();
        ctx.arc(node.x, node.y, isSelected ? 10 : 7, 0, 2 * Math.PI);
        ctx.fillStyle = isSelected ? '#a855f7' : '#00cec9';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.font = isSelected ? 'bold 11px Inter, sans-serif' : '10px Inter, sans-serif';
        ctx.fillStyle = isSelected ? '#ffffff' : '#cbd5e1';
        ctx.textAlign = 'center';
        ctx.fillText(node.name.slice(0, 20), node.x, node.y + 20);
      });

      ctx.restore();
      animationFrameId = requestAnimationFrame(render);
    };

    sim.on('tick', render);

    return () => {
      sim.stop();
      cancelAnimationFrame(animationFrameId);
    };
  }, [nodeList, links, activeSelectedNode, zoom, offset]);

  const handleSelect = (id: string) => {
    if (onSelectNodeId) {
      onSelectNodeId(id === activeSelectedNode ? '' : id);
    } else {
      setInternalSelectedNode(id === activeSelectedNode ? null : id);
    }
  };

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Network className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Interactive Knowledge Graph</h3>
          <span className="text-xs text-slate-500 font-mono">({nodeList.length} nodes)</span>
        </div>

        <div className="hidden sm:flex items-center space-x-3 text-[11px] font-mono text-slate-400">
          <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-red-500 mr-1.5" /> Prerequisite / Conflict</span>
          <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-1.5" /> Enables / Leadership</span>
          <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-purple-500 mr-1.5" /> Connection</span>
        </div>
      </div>

      <div className="glass-panel p-4 relative overflow-hidden flex flex-col lg:flex-row gap-4">
        <div className="absolute top-6 left-6 z-10 flex flex-col space-y-2 bg-slate-900/80 backdrop-blur-md p-1.5 rounded-xl border border-white/10">
          <button
            onClick={() => setZoom((z) => Math.min(z + 0.2, 2.5))}
            className="p-2 rounded-lg hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z - 0.2, 0.5))}
            className="p-2 rounded-lg hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setZoom(1);
              setOffset({ x: 0, y: 0 });
              if (onSelectNodeId) onSelectNodeId('');
              else setInternalSelectedNode(null);
            }}
            className="p-2 rounded-lg hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
            title="Reset View"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 h-[440px] rounded-xl bg-slate-950/60 overflow-hidden relative">
          <canvas
            ref={canvasRef}
            width={800}
            height={440}
            className="w-full h-full cursor-grab active:cursor-grabbing"
          />
        </div>

        <div className="w-full lg:w-80 space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-400 font-mono uppercase tracking-wider">
              Select Concept Node
            </h4>
            <div className="max-h-56 overflow-y-auto space-y-1 pr-1">
              {nodeList.map((node) => (
                <button
                  key={node.id}
                  onClick={() => handleSelect(node.id)}
                  className={`w-full text-left px-3 py-2 rounded-xl text-xs flex items-center justify-between transition-all ${
                    activeSelectedNode === node.id || activeSelectedNode === node.name
                      ? 'bg-purple-600/80 text-white font-semibold shadow-md shadow-purple-500/20'
                      : 'bg-white/5 hover:bg-white/10 text-slate-300'
                  }`}
                >
                  <span className="truncate">{node.name}</span>
                  <ChevronRight className="w-3.5 h-3.5 opacity-60" />
                </button>
              ))}
            </div>
          </div>

          <AnimatePresence>
            {activeSelectedNode && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30 text-xs space-y-2 relative"
              >
                <button
                  onClick={() => {
                    if (onSelectNodeId) onSelectNodeId('');
                    else setInternalSelectedNode(null);
                  }}
                  className="absolute top-2 right-2 p-1 text-slate-400 hover:text-white"
                >
                  <X className="w-3.5 h-3.5" />
                </button>

                <h5 className="font-bold text-white text-sm pr-6">
                  {nodesMap.get(activeSelectedNode) || activeSelectedNode}
                </h5>

                <p className="text-[11px] text-purple-300 font-mono">
                  ID: {activeSelectedNode}
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};
