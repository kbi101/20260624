import React from 'react';
import { motion } from 'framer-motion';
import { Activity, Star } from 'lucide-react';

interface DimensionBarsProps {
  dimensions: {
    dominant?: string;
    primary_concepts?: string[];
    [key: string]: any;
  };
}

export const DimensionBars: React.FC<DimensionBarsProps> = ({ dimensions }) => {
  if (!dimensions || Object.keys(dimensions).length === 0) return null;

  // Filter numeric dimensions
  const dimEntries = Object.entries(dimensions).filter(
    ([key, val]) => typeof val === 'number' && key !== 'dominant'
  );

  if (dimEntries.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="glass-panel p-6 mb-8"
    >
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/10">
        <div className="flex items-center space-x-2">
          <Activity className="w-5 h-5 text-purple-400" />
          <h3 className="text-base font-semibold text-white">Cognitive Dimensions</h3>
        </div>

        {dimensions.dominant && (
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-gradient-to-r from-purple-500/20 to-cyan-500/20 border border-purple-500/30 text-purple-300 text-xs font-medium">
            <Star className="w-3.5 h-3.5 fill-purple-400 text-purple-400" />
            <span>Dominant: <strong className="text-white capitalize">{dimensions.dominant}</strong></span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {dimEntries.map(([name, value], idx) => {
          const numVal = Math.min(Math.max(Number(value) * 100, 5), 100);
          return (
            <div key={name} className="space-y-1.5">
              <div className="flex justify-between text-xs font-medium">
                <span className="text-slate-300 capitalize">{name.replace('_', ' ')}</span>
                <span className="text-purple-400 font-mono">{Math.round(numVal)}%</span>
              </div>
              <div className="h-2.5 w-full bg-white/5 rounded-full overflow-hidden p-0.5 border border-white/5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${numVal}%` }}
                  transition={{ duration: 0.8, delay: 0.2 + idx * 0.05, ease: 'easeOut' }}
                  className="h-full rounded-full bg-gradient-to-r from-purple-500 to-cyan-400 shadow-sm shadow-purple-500/50"
                />
              </div>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
};
