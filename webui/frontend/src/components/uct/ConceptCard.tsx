import React from 'react';
import { motion } from 'framer-motion';
import { BookOpen, AlertTriangle, ShieldAlert, HelpCircle, Layers } from 'lucide-react';
import type { Concept, Compression } from '../../types';

interface ConceptCardProps {
  concepts: Concept[];
  compressions?: Compression[];
  mode?: string;
}

export const ConceptCard: React.FC<ConceptCardProps> = ({ concepts, compressions, mode }) => {
  const [activeLevels, setActiveLevels] = React.useState<Record<string, number>>({});

  if (!concepts || concepts.length === 0) return null;

  const getDefaultLevel = () => {
    if (mode === 'exam') return 3;
    if (mode === 'overview') return 0;
    if (mode === 'practice') return 1;
    return 1;
  };

  return (
    <div className="mb-10">
      <div className="flex items-center space-x-2 mb-4">
        <BookOpen className="w-5 h-5 text-purple-400" />
        <h3 className="text-lg font-semibold text-white">Core Concepts</h3>
        <span className="text-xs text-slate-500 font-mono">({concepts.length})</span>
        {mode === 'exam' && (
          <span className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 text-xs border border-red-500/30">
            🎯 Exam Mode: L3 Expert / Edge Cases Auto-Expanded
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {concepts.map((concept, idx) => {
          const comp = compressions?.find((c) => c.concept_name === concept.name);
          const level = activeLevels[concept.name] ?? getDefaultLevel();

          let displayDefinition = concept.definition;
          if (comp) {
            if (level === 0) displayDefinition = comp.level_0_essence;
            else if (level === 1) displayDefinition = comp.level_1_functional;
            else if (level === 2) displayDefinition = comp.level_2_detailed;
            else if (level === 3) displayDefinition = comp.level_3_expert;
          }

          return (
            <motion.div
              key={concept.name + idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: idx * 0.05 }}
              className="glass-card rounded-2xl p-6 flex flex-col justify-between h-full group relative overflow-hidden"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <h4 className="text-base font-bold text-white group-hover:text-purple-300 transition-colors">
                    {concept.name}
                  </h4>
                  {comp && (
                    <div className="flex items-center space-x-1 p-0.5 rounded-lg bg-white/5 border border-white/10 text-[10px] font-mono">
                      <Layers className="w-3 h-3 text-purple-400 ml-1" />
                      {[0, 1, 2, 3].map((lvl) => (
                        <button
                          key={lvl}
                          onClick={() =>
                            setActiveLevels((prev) => ({ ...prev, [concept.name]: lvl }))
                          }
                          className={`px-1.5 py-0.5 rounded ${
                            level === lvl
                              ? 'bg-purple-500 text-white font-bold'
                              : 'text-slate-400 hover:text-white'
                          }`}
                        >
                          L{lvl}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <p className="text-xs text-slate-300 leading-relaxed font-light">
                  {displayDefinition}
                </p>

                {concept.why_it_exists && (
                  <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs">
                    <span className="flex items-center text-[10px] font-semibold uppercase tracking-wider text-purple-300 mb-1">
                      <HelpCircle className="w-3 h-3 mr-1" /> Why it exists
                    </span>
                    <p className="text-purple-200/90 text-xs">{concept.why_it_exists}</p>
                  </div>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-white/5 space-y-2 text-xs">
                {concept.constraints && concept.constraints.length > 0 && (
                  <div>
                    <span className="flex items-center text-[10px] font-semibold text-slate-400 mb-1">
                      <AlertTriangle className="w-3 h-3 text-amber-400 mr-1" /> Constraints
                    </span>
                    <ul className="list-disc list-inside text-slate-400 space-y-0.5 text-[11px]">
                      {concept.constraints.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {concept.failure_modes && concept.failure_modes.length > 0 && (
                  <div>
                    <span className="flex items-center text-[10px] font-semibold text-slate-400 mb-1">
                      <ShieldAlert className="w-3 h-3 text-red-400 mr-1" /> Failure Modes
                    </span>
                    <ul className="list-disc list-inside text-slate-400 space-y-0.5 text-[11px]">
                      {concept.failure_modes.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
