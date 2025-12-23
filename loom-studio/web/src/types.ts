export interface CloudEvent {
  specversion: string;
  type: string;
  source: string;
  id: string;
  time: string;
  subject?: string;
  data: any;
  extensions?: Record<string, any>;
}

export interface NodeInfo {
  id: string;
  type: string;
  metadata: any;
}

export interface EdgeInfo {
  from: string;
  to: string;
  count: number;
}

export interface TopologyData {
  nodes: NodeInfo[];
  edges: EdgeInfo[];
}

export interface MemoryEntry {
  type: string;
  data: any;
  source: string;
}
