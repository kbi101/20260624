import React from 'react';
import { motion } from 'framer-motion';
import { RefreshCw, ArrowRightLeft, Clock } from 'lucide-react';
import type { CausalLoop } from '../../types';

interface CausalLoopViewProps {
  causalLoops?: CausalLoop[];
}

export const CausalLoopView: React.FC<CausalLoopViewProps> = ({ causalLoops }) => {
  if (!causalLoops || causalLoops.length === 0) return null;

  return (
    <div className="mb-10 space-y-6">
      <div className="flex items-center space-x-2">
        <RefreshCw className="w-5 h-5 text-pink-400" />
        <h3 className="text-lg font-semibold text-white">Causal Loops & Feedback Systems</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {causalLoops.map((loop, idx) => (
          <motion.div
            key={loop.title + idx}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: idx * 0.1 }}
            className="glass-panel p-6"
          >
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-white/10">
              <h4 className="text-sm font-bold text-pink-300 font-mono">{loop.title}</h4>
              {loop.loop_type && (
                <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider bg-pink-500/20 text-pink-300 border border-pink-500/30">
                  {loop.loop_type}
                </span>
              )}
            </div>

            <div className="space-y-3">
              {loop.links.map((link, lIdx) => (
                <div
                  key={lIdx}
                  className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 text-xs"
                >
                  <div className="flex items-center space-x-2 font-medium text-slate-200">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px]">
                      {link.from}
                    </span>
                    <ArrowRightLeft className="w-3.5 h-3.5 text-pink-400" />
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px]">
                      {link.to}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 font-mono text-[11px]">
                    <span
                      className={`px-2 py-0.5 rounded font-bold ${
                        link.effect.includes('+') || link.effect.toLowerCase().includes('reinforce')
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}
                    >
                      {link.effect}
                    </span>
                    {link.delay && (
                      <span className="flex items-center text-slate-400">
                        <Clock className="w-3 h-3 mr-1" />
                        {link.delay}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
