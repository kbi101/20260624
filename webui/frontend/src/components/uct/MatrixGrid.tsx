import React from 'react';
import { motion } from 'framer-motion';
import { LayoutGrid } from 'lucide-react';
import type { Matrix } from '../../types';

interface MatrixGridProps {
  matrices?: Matrix[];
}

export const MatrixGrid: React.FC<MatrixGridProps> = ({ matrices }) => {
  if (!matrices || matrices.length === 0) return null;

  return (
    <div className="mb-10 space-y-6">
      <div className="flex items-center space-x-2">
        <LayoutGrid className="w-5 h-5 text-indigo-400" />
        <h3 className="text-lg font-semibold text-white">Comparative Matrices</h3>
      </div>

      {matrices.map((mx, idx) => (
        <motion.div
          key={mx.title + idx}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: idx * 0.1 }}
          className="glass-panel p-6 overflow-x-auto"
        >
          <h4 className="text-sm font-bold text-indigo-300 font-mono mb-4">{mx.title}</h4>

          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/10 text-slate-400 font-mono uppercase text-[10px]">
                <th className="p-3 bg-white/5 rounded-tl-xl">Option / Attribute</th>
                {mx.attributes.map((attr) => (
                  <th key={attr} className="p-3 bg-white/5">
                    {attr}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {mx.options.map((opt) => (
                <tr key={opt} className="hover:bg-white/5 transition-colors">
                  <td className="p-3 font-semibold text-white bg-white/5">{opt}</td>
                  {mx.attributes.map((attr) => {
                    const key = `${opt}|${attr}`;
                    const altKey = `${attr}|${opt}`;
                    const val = mx.cells[key] || mx.cells[altKey] || '-';
                    return (
                      <td key={attr} className="p-3 text-slate-300">
                        {val}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      ))}
    </div>
  );
};
