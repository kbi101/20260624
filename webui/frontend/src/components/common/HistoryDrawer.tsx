import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Trash2, ExternalLink, Calendar, Search } from 'lucide-react';
import type { HistoryItem } from '../../types';

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  history: HistoryItem[];
  onSelectTopic: (topic: string) => void;
  onDeleteTopic: (topic: string) => void;
  isLoading?: boolean;
}

export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({
  isOpen,
  onClose,
  history,
  onSelectTopic,
  onDeleteTopic,
  isLoading,
}) => {
  const [filter, setFilter] = React.useState('');

  const filtered = history.filter((item) =>
    item.topic.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />

          {/* Slide-over Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 350, damping: 30 }}
            className="fixed top-0 right-0 z-50 h-full w-full max-w-md bg-slate-900/95 border-l border-white/10 backdrop-blur-2xl p-6 shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <div className="flex items-center space-x-2">
                <div className="p-2 rounded-lg bg-purple-500/20 text-purple-400">
                  <Calendar className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-white">Dashboard History</h2>
                  <p className="text-xs text-slate-400">Saved knowledge dashboards</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Filter Search input */}
            <div className="mt-4 relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                placeholder="Filter saved topics..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-xs bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 transition-all"
              />
            </div>

            {/* History List */}
            <div className="flex-1 overflow-y-auto mt-4 space-y-2 pr-1">
              {isLoading ? (
                <div className="flex items-center justify-center h-48 text-slate-400 text-xs">
                  <div className="w-5 h-5 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mr-2" />
                  Loading history...
                </div>
              ) : filtered.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-slate-500 text-xs">
                  <p>No saved topics found</p>
                </div>
              ) : (
                filtered.map((item, idx) => (
                  <motion.div
                    key={item.topic + idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    className="group flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 hover:border-purple-500/30 transition-all duration-200"
                  >
                    <div
                      onClick={() => {
                        onSelectTopic(item.topic);
                        onClose();
                      }}
                      className="flex-1 cursor-pointer pr-3"
                    >
                      <h3 className="text-xs font-medium text-slate-200 group-hover:text-purple-300 transition-colors line-clamp-1">
                        {item.topic}
                      </h3>
                      {item.timestamp && (
                        <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                          {new Date(item.timestamp).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center space-x-1 opacity-60 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => {
                          onSelectTopic(item.topic);
                          onClose();
                        }}
                        title="Load topic"
                        className="p-1.5 rounded-lg hover:bg-purple-500/20 text-slate-400 hover:text-purple-300 transition-colors"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteTopic(item.topic);
                        }}
                        title="Delete entry"
                        className="p-1.5 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
