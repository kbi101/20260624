import React from 'react';
import type { HistNode } from '../../types';

interface HistEntityChipsProps {
  nodes: HistNode[];
  selectedNodeId?: string | null;
  onSelectNode: (nodeId: string) => void;
}

export const HistEntityChips: React.FC<HistEntityChipsProps> = ({
  nodes,
  selectedNodeId,
  onSelectNode,
}) => {
  if (!nodes || nodes.length === 0) return null;

  return (
    <div className="glass-panel p-4 mb-6">
      <h4 className="text-xs font-bold text-slate-400 font-mono uppercase tracking-wider mb-3">
        Historical Entity & Person Filter Chips ({nodes.length})
      </h4>
      <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto pr-1">
        {nodes.map((node) => {
          const isSelected = selectedNodeId === node.node_id;
          return (
            <button
              key={node.node_id}
              onClick={() => onSelectNode(node.node_id)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                isSelected
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/30'
                  : 'bg-pink-500/10 hover:bg-pink-500/20 text-pink-300 border border-pink-500/20'
              }`}
            >
              {node.name}
            </button>
          );
        })}
      </div>
    </div>
  );
};
