import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from './components/common/Header';
import { OrbBackground } from './components/common/OrbBackground';
import { HistoryDrawer } from './components/common/HistoryDrawer';
import { UctHero } from './components/uct/UctHero';
import { DimensionBars } from './components/uct/DimensionBars';
import { ConceptCard } from './components/uct/ConceptCard';
import { SequencePipeline } from './components/uct/SequencePipeline';
import { CausalLoopView } from './components/uct/CausalLoopView';
import { MatrixGrid } from './components/uct/MatrixGrid';
import { ForceGraphView } from './components/uct/ForceGraphView';

import { HistControls } from './components/hist/HistControls';
import { HistTimelineCanvas } from './components/hist/HistTimelineCanvas';
import { HistEntityChips } from './components/hist/HistEntityChips';
import { HistAnswerDrawer } from './components/hist/HistAnswerDrawer';

import {
  fetchTopicData,
  regenerateTopicData,
  fetchHistory,
  deleteHistoryTopic,
  fetchHistGraphData,
  askHistQuestion,
  ingestHistTopic,
  fetchHistStats,
} from './services/api';
import type { TopicModel, HistoryItem, HistGraphData, HistAnswer, HistStats } from './types';
import { ExternalLink, BookOpen, AlertCircle } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState<'uct' | 'hist'>('uct');

  // UCT State
  const [topicData, setTopicData] = useState<TopicModel | null>(null);
  const [activeMode, setActiveMode] = useState<string>('understand');
  const [isUctLoading, setIsUctLoading] = useState<boolean>(false);
  const [uctError, setUctError] = useState<string | null>(null);

  // History Drawer State
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [historyList, setHistoryList] = useState<HistoryItem[]>([]);

  // HIST State
  const [histData, setHistData] = useState<HistGraphData>({ nodes: [], edges: [] });
  const [histAnswer, setHistAnswer] = useState<HistAnswer | null>(null);
  const [histStats, setHistStats] = useState<HistStats>({});
  const [selectedHistNode, setSelectedHistNode] = useState<string | null>(null);
  const [histViewMode, setHistViewMode] = useState<'timeline' | 'graph'>('graph');
  const [isHistAsking, setIsHistAsking] = useState<boolean>(false);
  const [isHistIngesting, setIsHistIngesting] = useState<boolean>(false);

  useEffect(() => {
    loadHistory();
    loadHistGraph();
    loadHistStats();
  }, []);

  useEffect(() => {
    if (topicData?.mode) {
      setActiveMode(topicData.mode);
    }
  }, [topicData]);

  const loadHistory = async () => {
    try {
      const items = await fetchHistory();
      setHistoryList(items);
    } catch (e) {
      console.error('Failed to load history', e);
    }
  };

  const loadHistGraph = async (query?: string) => {
    try {
      const data = await fetchHistGraphData(query);
      setHistData(data);
    } catch (e) {
      console.error('Failed to load HIST graph', e);
    }
  };

  const loadHistStats = async () => {
    try {
      const stats = await fetchHistStats();
      setHistStats(stats);
    } catch (e) {
      console.error('Failed to load HIST stats', e);
    }
  };

  const handleGenerateTopic = async (topic: string, depth: number, mode: string, forceRegenerate = false) => {
    setIsUctLoading(true);
    setUctError(null);
    setActiveMode(mode);
    try {
      const data = forceRegenerate
        ? await regenerateTopicData(topic, depth, mode)
        : await fetchTopicData(topic, depth, mode);
      setTopicData(data);
      loadHistory();
    } catch (err: any) {
      setUctError(err.message || 'Failed to generate topic dashboard.');
    } finally {
      setIsUctLoading(false);
    }
  };

  const handleDeleteHistory = async (topic: string) => {
    await deleteHistoryTopic(topic);
    loadHistory();
  };

  const handleAskHist = async (question: string) => {
    setIsHistAsking(true);
    try {
      const ans = await askHistQuestion(question);
      setHistAnswer(ans);
    } catch (e: any) {
      console.error(e);
    } finally {
      setIsHistAsking(false);
    }
  };

  const handleIngestHist = async (topic: string) => {
    setIsHistIngesting(true);
    try {
      await ingestHistTopic(topic);
      loadHistGraph();
      loadHistStats();
    } catch (e) {
      console.error(e);
    } finally {
      setIsHistIngesting(false);
    }
  };

  return (
    <div className="min-h-screen text-slate-100 flex flex-col font-sans relative">
      <OrbBackground />

      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenHistory={() => setIsHistoryOpen(true)}
        histStats={histStats}
      />

      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        history={historyList}
        onSelectTopic={(t) => handleGenerateTopic(t, 1, 'understand')}
        onDeleteTopic={handleDeleteHistory}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        <AnimatePresence mode="wait">
          {activeTab === 'uct' ? (
            <motion.div
              key="uct-tab"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              <UctHero
                onGenerate={handleGenerateTopic}
                isLoading={isUctLoading}
                currentTopic={topicData?.topic}
                activeMode={activeMode}
                onModeChange={setActiveMode}
                recentTopics={historyList.map((h) => h.topic).slice(0, 5)}
              />

              {uctError && (
                <div className="max-w-4xl mx-auto mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm flex items-center space-x-2">
                  <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
                  <span>{uctError}</span>
                </div>
              )}

              {topicData && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5 }}
                  className="space-y-8"
                >
                  <div className="glass-panel p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <h2 className="text-2xl font-extrabold text-white capitalize">
                          {topicData.topic}
                        </h2>
                        {/* Interactive Mode Pills */}
                        <div className="flex items-center space-x-1.5 p-1 rounded-xl bg-white/5 border border-white/10">
                          {[
                            { id: 'understand', label: '📖 Understand' },
                            { id: 'exam', label: '🎯 Exam' },
                            { id: 'practice', label: '⚡ Practice' },
                            { id: 'research', label: '🔬 Research' },
                            { id: 'overview', label: '📋 Overview' },
                          ].map((m) => (
                            <button
                              key={m.id}
                              onClick={() => setActiveMode(m.id)}
                              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                                activeMode === m.id
                                  ? 'bg-purple-600 text-white font-bold shadow-md shadow-purple-500/30'
                                  : 'text-slate-400 hover:text-white hover:bg-white/5'
                              }`}
                            >
                              {m.label}
                            </button>
                          ))}
                        </div>
                      </div>
                      {(() => {
                        if (!topicData.compressions?.length) return null;
                        const tLower = topicData.topic.toLowerCase();
                        const match = topicData.compressions.find(
                          (c) => c.concept_name.toLowerCase().includes(tLower) || tLower.includes(c.concept_name.toLowerCase())
                        );
                        const essence = match?.level_0_essence || topicData.compressions[0].level_0_essence;
                        return (
                          <p className="mt-1.5 text-sm text-purple-300 font-light">
                            "{essence}"
                          </p>
                        );
                      })()}
                    </div>
                    <a
                      href={`/api/json?topic=${encodeURIComponent(topicData.topic)}`}
                      target="_blank"
                      rel="noreferrer"
                      className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-mono text-slate-300 hover:text-white transition-all flex items-center space-x-2 shrink-0"
                    >
                      <span>Export Raw JSON</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>

                  <DimensionBars dimensions={topicData.dimensions} />

                  {/* Mode-Driven Layout Reordering */}
                  {(() => {
                    const currentMode = activeMode || topicData.mode || 'understand';

                    const conceptsComponent = (
                      <ConceptCard
                        key="concepts"
                        concepts={topicData.concepts}
                        compressions={topicData.compressions}
                        mode={currentMode}
                      />
                    );
                    const graphComponent = (
                      <ForceGraphView key="graph" graph={topicData.graph} edges={topicData.edges} />
                    );
                    const sequenceComponent = (
                      <SequencePipeline key="sequence" sequenceBlocks={topicData.sequence_blocks} />
                    );
                    const loopsComponent = (
                      <CausalLoopView key="loops" causalLoops={topicData.causal_loops} />
                    );
                    const matrixComponent = (
                      <MatrixGrid key="matrix" matrices={topicData.matrices} />
                    );

                    if (currentMode === 'practice') {
                      return [sequenceComponent, conceptsComponent, graphComponent, loopsComponent, matrixComponent];
                    }
                    if (currentMode === 'research') {
                      return [loopsComponent, matrixComponent, graphComponent, conceptsComponent, sequenceComponent];
                    }
                    if (currentMode === 'exam') {
                      return [conceptsComponent, matrixComponent, sequenceComponent, loopsComponent, graphComponent];
                    }
                    if (currentMode === 'overview') {
                      return [conceptsComponent, graphComponent, sequenceComponent, loopsComponent, matrixComponent];
                    }
                    // Default 'understand'
                    return [conceptsComponent, graphComponent, sequenceComponent, loopsComponent, matrixComponent];
                  })()}

                  {topicData.references && topicData.references.length > 0 && (
                    <div className="glass-panel p-6">
                      <div className="flex items-center space-x-2 mb-3">
                        <BookOpen className="w-4 h-4 text-purple-400" />
                        <h4 className="text-sm font-bold text-white">Sources & Web References</h4>
                      </div>
                      <ul className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        {topicData.references.map((ref, idx) => (
                          <li key={idx}>
                            <a
                              href={ref.url}
                              target="_blank"
                              rel="noreferrer"
                              className="p-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 flex items-center justify-between group transition-all"
                            >
                              <span className="text-slate-300 group-hover:text-purple-300 font-medium truncate">
                                {ref.title || ref.url}
                              </span>
                              <ExternalLink className="w-3.5 h-3.5 text-slate-500 group-hover:text-purple-400 shrink-0 ml-2" />
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </motion.div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="hist-tab"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              <HistControls
                onSearchGraph={(q) => loadHistGraph(q)}
                onAskQuestion={handleAskHist}
                onIngestTopic={handleIngestHist}
                onProcessQueue={() => handleIngestHist('')}
                isAsking={isHistAsking}
                isIngesting={isHistIngesting}
                viewMode={histViewMode}
                onToggleViewMode={setHistViewMode}
              />

              <HistAnswerDrawer answer={histAnswer} />

              {histViewMode === 'graph' ? (
                <ForceGraphView
                  rawNodes={histData.nodes}
                  rawEdges={histData.edges}
                  onSelectNodeId={(id) => setSelectedHistNode(id)}
                  selectedNodeId={selectedHistNode}
                />
              ) : (
                <HistTimelineCanvas
                  nodes={histData.nodes}
                  edges={histData.edges}
                  onSelectNode={(id) => setSelectedHistNode(id)}
                  selectedNodeId={selectedHistNode}
                />
              )}

              <HistEntityChips
                nodes={histData.nodes}
                onSelectNode={(id) => setSelectedHistNode(id)}
                selectedNodeId={selectedHistNode}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="w-full py-4 text-center text-xs text-slate-500 border-t border-white/5 backdrop-blur-md">
        Morphos Cognitive Intelligence · React Motion UI · Powered by Local LLMs
      </footer>
    </div>
  );
}
