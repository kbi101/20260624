export interface Concept {
  name: string;
  definition: string;
  why_it_exists: string;
  constraints: string[];
  failure_modes: string[];
}

export interface ScaledConcept {
  name: string;
  definition: string;
  scale: string;
}

export interface SequenceStep {
  label: string;
  input: string;
  transformation: string;
  validation: string;
  output: string;
  failure_condition?: string;
  prerequisites?: string[];
}

export interface SequenceBlock {
  title: string;
  steps: SequenceStep[];
}

export interface LoopLink {
  from: string;
  to: string;
  effect: string;
  delay?: string;
}

export interface CausalLoop {
  title: string;
  loops: string[];
  links: LoopLink[];
  loop_type?: string;
}

export interface Matrix {
  title: string;
  attributes: string[];
  options: string[];
  cells: Record<string, string>;
}

export interface Edge {
  from: string;
  to: string;
  type: string;
}

export interface Compression {
  concept_name: string;
  level_0_essence: string;
  level_1_functional: string;
  level_2_detailed: string;
  level_3_expert: string;
}

export interface GraphAdjacency {
  nodes: string[];
  adjacency: Record<string, { name: string; edge_type: string }[]>;
}

export interface TopicModel {
  topic: string;
  mode?: string;
  dimensions: {
    dominant?: string;
    primary_concepts?: string[];
    [key: string]: any;
  };
  concepts: Concept[];
  scaled_concepts?: ScaledConcept[];
  sequence_blocks?: SequenceBlock[];
  causal_loops?: CausalLoop[];
  matrices?: Matrix[];
  edges?: Edge[];
  compressions?: Compression[];
  graph?: GraphAdjacency;
  references?: { title: string; url: string }[];
}

export interface HistoryItem {
  topic: string;
  timestamp: string;
}

export interface HistNode {
  node_id: string;
  name: string;
  label?: string;
  type?: string;
  year?: number;
  properties?: Record<string, any>;
  [key: string]: any;
}

export interface HistEdge {
  src: string;
  rel: string;
  tgt: string;
  [key: string]: any;
}

export interface HistGraphData {
  nodes: HistNode[];
  edges: HistEdge[];
}

export interface HistNodeDetails {
  node_id: string;
  name: string;
  label: string;
  properties: Record<string, any>;
  connections: { rel: string; node_id: string; name: string }[];
  error?: string;
}

export interface HistAnswer {
  answer: string;
  nodes_used: number;
  edges_used: number;
  evidence: any[];
  error?: string;
}

export interface HistStats {
  nodes?: number;
  edges?: number;
  persons?: number;
  node_count?: number;
  edge_count?: number;
}
