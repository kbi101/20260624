import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, GitFork, Clock, Sparkles } from 'lucide-react';

interface HeaderProps {
  activeTab: 'uct' | 'hist';
  setActiveTab: (tab: 'uct' | 'hist') => void;
  onOpenHistory: () => void;
  histStats?: { nodes?: number; edges?: number; node_count?: number; edge_count?: number };
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  onOpenHistory,
  histStats,
}) => {
  const nodeCount = histStats?.nodes ?? histStats?.node_count ?? 0;
  const edgeCount = histStats?.edges ?? histStats?.edge_count ?? 0;

  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-xl bg-slate-950/65 border-b border-white/10 px-6 py-3 transition-all duration-300">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Brand Logo */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('uct')}>
          <motion.div
            whileHover={{ rotate: 180, scale: 1.1 }}
            transition={{ duration: 0.5, ease: "backOut" }}
            className="p-2 rounded-xl bg-gradient-to-tr from-purple-600 to-cyan-400 text-white shadow-lg shadow-purple-500/20"
          >
            <Cpu className="w-5 h-5" />
          </motion.div>
          <div>
            <h1 className="font-bold text-lg tracking-tight gradient-text">Morphos</h1>
            <p className="text-[10px] text-slate-400 font-mono tracking-widest uppercase">Cognitive Intelligence</p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center p-1 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
          <button
            onClick={() => setActiveTab('uct')}
            className={`relative px-5 py-2 rounded-xl text-xs font-semibold transition-all duration-300 flex items-center space-x-2 ${
              activeTab === 'uct' ? 'text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {activeTab === 'uct' && (
              <motion.div
                layoutId="activeTabIndicator"
                className="absolute inset-0 rounded-xl bg-gradient-to-r from-purple-600/80 to-indigo-600/80 shadow-md shadow-purple-500/20"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
            <Sparkles className="w-4 h-4 z-10" />
            <span className="z-10">Cognitive Textbook</span>
          </button>

          <button
            onClick={() => setActiveTab('hist')}
            className={`relative px-5 py-2 rounded-xl text-xs font-semibold transition-all duration-300 flex items-center space-x-2 ${
              activeTab === 'hist' ? 'text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {activeTab === 'hist' && (
              <motion.div
                layoutId="activeTabIndicator"
                className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-600/80 to-teal-600/80 shadow-md shadow-cyan-500/20"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
            <GitFork className="w-4 h-4 z-10" />
            <span className="z-10">HIST Graph</span>
            {nodeCount > 0 && (
              <span className="z-10 px-1.5 py-0.5 rounded-full text-[10px] bg-cyan-400/20 text-cyan-300 font-mono">
                {nodeCount}n
              </span>
            )}
          </button>
        </div>

        {/* Actions Right */}
        <div className="flex items-center space-x-3">
          {activeTab === 'hist' && (nodeCount > 0 || edgeCount > 0) && (
            <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span>{nodeCount} nodes · {edgeCount} edges</span>
            </div>
          )}

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onOpenHistory}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white text-xs font-medium transition-all"
          >
            <Clock className="w-4 h-4 text-purple-400" />
            <span>History</span>
          </motion.button>
        </div>

      </div>
    </header>
  );
};
