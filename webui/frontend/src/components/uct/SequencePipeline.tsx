import React from 'react';
import { motion } from 'framer-motion';
import { GitCommit, ArrowRight, AlertOctagon, CheckCircle2 } from 'lucide-react';
import type { SequenceBlock } from '../../types';

interface SequencePipelineProps {
  sequenceBlocks?: SequenceBlock[];
}

export const SequencePipeline: React.FC<SequencePipelineProps> = ({ sequenceBlocks }) => {
  if (!sequenceBlocks || sequenceBlocks.length === 0) return null;

  return (
    <div className="mb-10 space-y-6">
      <div className="flex items-center space-x-2">
        <GitCommit className="w-5 h-5 text-cyan-400" />
        <h3 className="text-lg font-semibold text-white">Execution Sequences</h3>
      </div>

      {sequenceBlocks.map((block, bIdx) => (
        <motion.div
          key={block.title + bIdx}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: bIdx * 0.1 }}
          className="glass-panel p-6"
        >
          <h4 className="text-sm font-bold text-cyan-300 mb-4 font-mono uppercase tracking-wider">
            {block.title}
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 relative">
            {block.steps.map((step, sIdx) => (
              <React.Fragment key={step.label + sIdx}>
                <div className="glass-card rounded-xl p-4 flex flex-col justify-between border-l-4 border-l-cyan-500 relative">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300">
                        Step {sIdx + 1}
                      </span>
                      {step.validation && (
                        <span className="flex items-center text-[10px] text-emerald-400">
                          <CheckCircle2 className="w-3 h-3 mr-1" /> Validated
                        </span>
                      )}
                    </div>

                    <h5 className="text-xs font-bold text-white mb-2">{step.label}</h5>

                    <div className="space-y-1.5 text-[11px] text-slate-300">
                      {step.input && (
                        <div>
                          <strong className="text-slate-400">Input:</strong> {step.input}
                        </div>
                      )}
                      {step.transformation && (
                        <div>
                          <strong className="text-slate-400">Process:</strong> {step.transformation}
                        </div>
                      )}
                      {step.output && (
                        <div>
                          <strong className="text-slate-400">Output:</strong> {step.output}
                        </div>
                      )}
                    </div>
                  </div>

                  {step.failure_condition && (
                    <div className="mt-3 p-2 rounded bg-red-500/10 border border-red-500/20 text-[10px] text-red-300 flex items-start space-x-1">
                      <AlertOctagon className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                      <span>{step.failure_condition}</span>
                    </div>
                  )}
                </div>

                {sIdx < block.steps.length - 1 && (
                  <div className="hidden lg:flex items-center justify-center -mx-2 text-cyan-500/50">
                    <ArrowRight className="w-4 h-4" />
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </motion.div>
      ))}
    </div>
  );
};
