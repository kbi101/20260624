import React from 'react';
import { Search, Plus, Play, HelpCircle, Clock, Network } from 'lucide-react';

interface HistControlsProps {
  onSearchGraph: (query: string) => void;
  onAskQuestion: (question: string) => void;
  onIngestTopic: (topic: string) => void;
  onProcessQueue: () => void;
  isIngesting?: boolean;
  isAsking?: boolean;
  viewMode: 'timeline' | 'graph';
  onToggleViewMode: (mode: 'timeline' | 'graph') => void;
}

export const HistControls: React.FC<HistControlsProps> = ({
  onSearchGraph,
  onAskQuestion,
  onIngestTopic,
  onProcessQueue,
  isIngesting,
  isAsking,
  viewMode,
  onToggleViewMode,
}) => {
  const [searchQuery, setSearchQuery] = React.useState('');
  const [askQuery, setAskQuery] = React.useState('');
  const [seedTopic, setSeedTopic] = React.useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearchGraph(searchQuery);
  };

  const handleAsk = (e: React.FormEvent) => {
    e.preventDefault();
    if (!askQuery.trim()) return;
    onAskQuestion(askQuery.trim());
  };

  const handleIngest = (e: React.FormEvent) => {
    e.preventDefault();
    if (!seedTopic.trim()) return;
    onIngestTopic(seedTopic.trim());
    setSeedTopic('');
  };

  return (
    <div className="glass-panel p-4 mb-6 space-y-4">
      {/* Top Bar with Mode Switcher */}
      <div className="flex items-center justify-between pb-3 border-b border-white/10">
        <div className="flex items-center space-x-2">
          <Network className="w-5 h-5 text-cyan-400" />
          <h3 className="text-base font-bold text-white">HIST Knowledge Explorer</h3>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center p-1 rounded-xl bg-white/5 border border-white/10">
          <button
            onClick={() => onToggleViewMode('timeline')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              viewMode === 'timeline'
                ? 'bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>⏱ Timeline</span>
          </button>

          <button
            onClick={() => onToggleViewMode('graph')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              viewMode === 'graph'
                ? 'bg-purple-600 text-white font-bold shadow-md shadow-purple-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            <span>◎ Network Graph</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Graph Subgraph Search */}
        <form onSubmit={handleSearch} className="flex space-x-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search graph (e.g. Napoleon, 1492)..."
              className="w-full pl-9 pr-3 py-2 text-xs bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs transition-colors flex items-center space-x-1"
          >
            <span>Search</span>
          </button>
        </form>

        {/* Q&A Ask Input */}
        <form onSubmit={handleAsk} className="flex space-x-2">
          <div className="relative flex-1">
            <HelpCircle className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              value={askQuery}
              onChange={(e) => setAskQuery(e.target.value)}
              placeholder="Ask a historical question..."
              className="w-full pl-9 pr-3 py-2 text-xs bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
            />
          </div>
          <button
            type="submit"
            disabled={isAsking}
            className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs transition-colors flex items-center space-x-1 disabled:opacity-50"
          >
            {isAsking ? <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <span>Ask</span>}
          </button>
        </form>

        {/* Wikipedia Seed Ingest */}
        <form onSubmit={handleIngest} className="flex space-x-2">
          <input
            type="text"
            value={seedTopic}
            onChange={(e) => setSeedTopic(e.target.value)}
            placeholder="Wikipedia seed topic..."
            className="flex-1 px-3 py-2 text-xs bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
          <button
            type="submit"
            disabled={isIngesting}
            className="px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors flex items-center space-x-1 disabled:opacity-50"
            title="Seed Wikipedia topic"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={onProcessQueue}
            className="px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 text-xs transition-colors flex items-center space-x-1"
            title="Process queued URLs"
          >
            <Play className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Queue</span>
          </button>
        </form>
      </div>
    </div>
  );
};
