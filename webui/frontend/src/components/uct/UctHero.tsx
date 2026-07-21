import React from 'react';
import { motion } from 'framer-motion';
import { Search, Sparkles, Layers, Compass, RotateCw } from 'lucide-react';

interface UctHeroProps {
  onGenerate: (topic: string, depth: number, mode: string, forceRegenerate?: boolean) => void;
  isLoading: boolean;
  currentTopic?: string;
}

const EXAMPLES = [
  'TCP congestion control',
  'Transformer attention mechanism',
  'Microservices architecture',
  'Distributed consensus protocols',
  'Neural network backpropagation',
];

export const UctHero: React.FC<UctHeroProps> = ({ onGenerate, isLoading, currentTopic }) => {
  const [topic, setTopic] = React.useState(currentTopic || '');
  const [depth, setDepth] = React.useState<number>(1);
  const [mode, setMode] = React.useState<string>('understand');

  React.useEffect(() => {
    if (currentTopic) setTopic(currentTopic);
  }, [currentTopic]);

  const handleSubmit = (e: React.FormEvent, forceRegenerate = false) => {
    e.preventDefault();
    if (!topic.trim()) return;
    onGenerate(topic.trim(), depth, mode, forceRegenerate);
  };

  return (
    <div className="w-full max-w-4xl mx-auto my-8 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="glass-panel p-8 shadow-2xl relative overflow-hidden"
      >
        {/* Glow accent line top */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 via-cyan-400 to-pink-500" />

        <div className="text-center mb-6">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-mono mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Universal Cognitive Textbook (UCT)</span>
          </div>
          <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Synthesize Any Topic into Structured Knowledge
          </h2>
          <p className="mt-2 text-sm text-slate-400 max-w-2xl mx-auto">
            Deep multi-dimensional analysis powered by local LLMs — dimensions, concepts, sequence steps, causal loops, and force graphs.
          </p>
        </div>

        {/* Input Form */}
        <form onSubmit={(e) => handleSubmit(e, false)} className="space-y-4">
          <div className="flex flex-col md:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-5 h-5 absolute left-4 top-3.5 text-slate-400" />
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder='e.g. "observability in cloud and AI applications"'
                required
                className="w-full pl-12 pr-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 text-sm transition-all"
              />
            </div>

            {/* Depth Selector */}
            <div className="relative flex items-center">
              <Layers className="w-4 h-4 absolute left-3 text-slate-400 pointer-events-none" />
              <select
                value={depth}
                onChange={(e) => setDepth(Number(e.target.value))}
                className="pl-9 pr-8 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white text-xs focus:outline-none focus:border-purple-500 cursor-pointer appearance-none"
              >
                <option value={0} className="bg-slate-900">Depth: Essence (0)</option>
                <option value={1} className="bg-slate-900">Depth: Core (1)</option>
                <option value={2} className="bg-slate-900">Depth: Full (2)</option>
                <option value={3} className="bg-slate-900">Depth: Expert (3)</option>
              </select>
            </div>

            {/* Mode Selector */}
            <div className="relative flex items-center">
              <Compass className="w-4 h-4 absolute left-3 text-slate-400 pointer-events-none" />
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="pl-9 pr-8 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white text-xs focus:outline-none focus:border-purple-500 cursor-pointer appearance-none"
              >
                <option value="understand" className="bg-slate-900">Mode: Understand</option>
                <option value="exam" className="bg-slate-900">Mode: Exam</option>
                <option value="practice" className="bg-slate-900">Mode: Practice</option>
                <option value="research" className="bg-slate-900">Mode: Research</option>
                <option value="overview" className="bg-slate-900">Mode: Overview</option>
              </select>
            </div>

            {/* Generate Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={isLoading}
              className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-sm shadow-lg shadow-purple-500/25 flex items-center justify-center space-x-2 transition-all disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Synthesizing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generate</span>
                </>
              )}
            </motion.button>

            {currentTopic && (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                onClick={(e) => handleSubmit(e, true)}
                disabled={isLoading}
                title="Bypass cache and regenerate topic"
                className="p-3.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white flex items-center justify-center transition-all disabled:opacity-50"
              >
                <RotateCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              </motion.button>
            )}
          </div>
        </form>

        {/* Quick Example Tags */}
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          <span className="text-xs text-slate-400 font-medium">Try:</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => {
                setTopic(ex);
                onGenerate(ex, depth, mode);
              }}
              className="px-3 py-1 rounded-full bg-white/5 hover:bg-purple-500/20 border border-white/10 hover:border-purple-500/40 text-slate-300 hover:text-purple-300 text-xs transition-all duration-200"
            >
              {ex}
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
};
