import React from 'react';
import { motion } from 'framer-motion';
import { HelpCircle, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import type { HistAnswer } from '../../types';

interface HistAnswerDrawerProps {
  answer?: HistAnswer | null;
}

export const HistAnswerDrawer: React.FC<HistAnswerDrawerProps> = ({ answer }) => {
  const [showEvidence, setShowEvidence] = React.useState(false);

  if (!answer) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel p-6 mb-8 border-l-4 border-l-purple-500"
    >
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-white/10">
        <div className="flex items-center space-x-2">
          <HelpCircle className="w-5 h-5 text-purple-400" />
          <h4 className="text-base font-bold text-white">HIST Synthesized Answer</h4>
        </div>
        <div className="flex items-center space-x-2 text-xs font-mono text-purple-300 bg-purple-500/10 px-3 py-1 rounded-full border border-purple-500/20">
          <span>{answer.nodes_used} nodes</span>
          <span>·</span>
          <span>{answer.edges_used} edges used</span>
        </div>
      </div>

      <p className="text-sm text-slate-200 leading-relaxed mb-4 whitespace-pre-wrap">
        {answer.answer}
      </p>

      {answer.evidence && answer.evidence.length > 0 && (
        <div className="pt-3 border-t border-white/5">
          <button
            onClick={() => setShowEvidence((prev) => !prev)}
            className="flex items-center space-x-1.5 text-xs text-purple-400 hover:text-purple-300 font-semibold transition-colors"
          >
            <FileText className="w-4 h-4" />
            <span>{showEvidence ? 'Hide' : 'Show'} Graph Evidence ({answer.evidence.length})</span>
            {showEvidence ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {showEvidence && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-3 p-3 rounded-xl bg-slate-950/80 border border-white/10 max-h-60 overflow-y-auto space-y-2 text-xs font-mono text-slate-400"
            >
              {answer.evidence.map((ev, i) => (
                <div key={i} className="p-2 rounded bg-white/5 border border-white/5">
                  <pre className="whitespace-pre-wrap break-all text-[11px]">
                    {JSON.stringify(ev, null, 2)}
                  </pre>
                </div>
              ))}
            </motion.div>
          )}
        </div>
      )}
    </motion.div>
  );
};
