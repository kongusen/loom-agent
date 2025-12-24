
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
          const eventData = event.data || {};

          // Add Source Node
          if (source && !nodes.find(n => n.id === source)) {
              let type = 'Node';
              if (source.includes('agent')) type = 'AgentNode';
              if (source.includes('tool')) type = 'ToolNode';
              if (source.includes('crew')) type = 'CrewNode';
              nodes.push({ id: source, type, metadata: {} });
          }

          // Add Target Node
          if (target && !nodes.find(n => n.id === target)) {
              let type = 'Node';
              if (target.includes('agent')) type = 'AgentNode';
              if (target.includes('tool')) type = 'ToolNode';
              if (target.includes('crew')) type = 'CrewNode';
              nodes.push({ id: target, type, metadata: {} });
          }

          // 从事件数据中提取内部节点信息（如果 Crew 内部调用了 Agent）
          // 检查 trace 信息
          if (eventData.trace && Array.isArray(eventData.trace)) {
              eventData.trace.forEach((step: any) => {
                  const agentId = step.agent;
                  if (agentId && !nodes.find(n => n.id === agentId)) {
                      let type = 'AgentNode';
                      if (agentId.includes('crew')) type = 'CrewNode';
                      if (agentId.includes('tool')) type = 'ToolNode';
                      nodes.push({ id: agentId, type, metadata: {} });
                      
                      // 创建从 Crew 到 Agent 的边
                      if (source && source.includes('crew')) {
                          const existingEdge = edges.find(e => e.from === source && e.to === agentId);
                          if (!existingEdge) {
                              edges.push({ from: source, to: agentId, count: 1 });
                          }
                      }
                  }
              });
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

    // Subscribe to events via WebSocket
    const unsubscribeEvents = wsService.subscribe((event) => {
      setEvents(prev => [...prev, event]);
      
      // Update Topology locally (optimistic update)
      updateTopology(event);
    });

    // Subscribe to topology updates via WebSocket
    const unsubscribeTopology = wsService.subscribeTopology((topologyData) => {
      setTopology(topologyData);
    });

    // 初始加载：获取完整拓扑和历史事件
    const fetchInitialData = async () => {
      try {
        // 获取拓扑
        const topologyResponse = await fetch('http://localhost:8765/api/topology');
        const topologyData = await topologyResponse.json();
        setTopology(topologyData);
        
        // 获取历史事件（最多1000个）
        const eventsResponse = await fetch('http://localhost:8765/api/events?limit=1000');
        const eventsData = await eventsResponse.json();
        if (eventsData.events && Array.isArray(eventsData.events)) {
          setEvents(eventsData.events);
          console.log(`Loaded ${eventsData.events.length} historical events`);
        }
      } catch (err) {
        console.error('Failed to fetch initial data:', err);
      }
    };

    // 只在初始加载时获取一次，之后通过 WebSocket 实时更新
    fetchInitialData();

    return () => {
      unsubscribeEvents();
      unsubscribeTopology();
    }
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<div style={{padding: 20}}><h2>Dashboard</h2><p>Events captured: {events.length}</p></div>} />
          <Route path="topology" element={<TopologyView data={topology} events={events} />} />
          <Route path="timeline" element={<TimelineView events={events} />} />
          <Route path="memory" element={<MemoryBrowser events={events} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
