
import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import TopologyView from './components/TopologyView';
import TimelineView from './components/TimelineView';
import MemoryBrowser from './components/MemoryBrowser';
import { wsService } from './services/websocket';
import type { CloudEvent, TopologyData } from './types';

function App() {
  const [events, setEvents] = useState<CloudEvent[]>([]);
  const [topology, setTopology] = useState<TopologyData>({ nodes: [], edges: [] });

  const updateTopology = (event: CloudEvent) => {
      setTopology(prev => {
          const nodes = [...prev.nodes];
          const edges = [...prev.edges];
          
          const source = event.source;
          const target = event.subject;

          // Add Source Node
          if (source && !nodes.find(n => n.id === source)) {
              let type = 'Node';
              if (source.includes('agent')) type = 'AgentNode';
              if (source.includes('tool')) type = 'ToolNode';
              nodes.push({ id: source, type, metadata: {} });
          }

          // Add Target Node
          if (target && !nodes.find(n => n.id === target)) {
              nodes.push({ id: target, type: 'Node', metadata: {} });
          }

          // Add Edge
          if (source && target) {
              const existingEdge = edges.find(e => e.from === source && e.to === target);
              if (existingEdge) {
                  existingEdge.count++;
              } else {
                  edges.push({ from: source, to: target, count: 1 });
              }
          }
          
          return { nodes, edges };
      });
  };

  useEffect(() => {
    // Connect to WebSocket
    wsService.connect();

    // Subscribe to events
    const unsubscribe = wsService.subscribe((event) => {
      setEvents(prev => [...prev, event]);
      
      // Update Topology
      // In a real app we might debounce this or fetch from API
      // Here we just accumulate purely local for demo
      updateTopology(event);
    });

    return () => {
      unsubscribe();
    }
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<div style={{padding: 20}}><h2>Dashboard</h2><p>Events captured: {events.length}</p></div>} />
          <Route path="topology" element={<TopologyView data={topology} />} />
          <Route path="timeline" element={<TimelineView events={events} />} />
          <Route path="memory" element={<MemoryBrowser events={events} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
