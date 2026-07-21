import type { TopicModel, HistoryItem, HistGraphData, HistNodeDetails, HistAnswer, HistStats } from '../types';

export async function fetchTopicData(topic: string, depth: number = 1, mode: string = 'understand'): Promise<TopicModel> {
  const res = await fetch(`/api/json?topic=${encodeURIComponent(topic)}&depth=${depth}&mode=${mode}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch topic data: ${res.statusText}`);
  }
  return res.json();
}

export async function regenerateTopicData(topic: string, depth: number = 1, mode: string = 'understand'): Promise<TopicModel> {
  const res = await fetch('/api/regenerate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, depth, mode }),
  });
  if (!res.ok) {
    return fetchTopicData(topic, depth, mode);
  }
  return fetchTopicData(topic, depth, mode);
}

export async function fetchHistory(): Promise<HistoryItem[]> {
  const res = await fetch('/api/history');
  if (!res.ok) return [];
  return res.json();
}

export async function deleteHistoryTopic(topic: string): Promise<boolean> {
  const res = await fetch(`/api/history/${encodeURIComponent(topic)}`, { method: 'DELETE' });
  return res.ok;
}

export async function fetchHistGraphData(query?: string, hops: number = 1, limit: number = 80): Promise<HistGraphData> {
  const params = new URLSearchParams({ hops: String(hops), limit: String(limit) });
  if (query) params.append('query', query);
  const res = await fetch(`/api/hist/graph-data?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch HIST graph data');
  return res.json();
}

export async function fetchHistNodeDetails(nodeId: string): Promise<HistNodeDetails> {
  const res = await fetch(`/api/hist/node-details/${encodeURIComponent(nodeId)}`);
  if (!res.ok) throw new Error('Node details failed');
  return res.json();
}

export async function askHistQuestion(question: string): Promise<HistAnswer> {
  const res = await fetch('/api/hist/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error('Q&A request failed');
  return res.json();
}

export async function ingestHistTopic(topic: string): Promise<{ status: string; url?: string; result?: any }> {
  const res = await fetch('/api/hist/ingest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  });
  return res.json();
}

export async function fetchHistStats(): Promise<HistStats> {
  const res = await fetch('/api/hist/stats');
  if (!res.ok) return {};
  return res.json();
}
