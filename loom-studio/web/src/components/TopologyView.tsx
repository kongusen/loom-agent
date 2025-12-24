import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type { TopologyData, CloudEvent } from '../types';
import './TopologyView.css';

interface TopologyViewProps {
  data: TopologyData;
  events: CloudEvent[];
}

interface NodeDetail {
  id: string;
  type: string;
  inputs: CloudEvent[];
  outputs: CloudEvent[];
  status: 'idle' | 'running' | 'completed' | 'error';
}

const TopologyView: React.FC<TopologyViewProps> = ({ data, events }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeDetail | null>(null);
  const [currentExecution, setCurrentExecution] = useState<string | null>(null);

  // 从事件中提取节点详情
  const getNodeDetails = (nodeId: string): NodeDetail => {
    // 规范化节点 ID：统一处理各种格式
    const normalizeId = (id: string): string[] => {
      if (!id) return [];
      // 移除开头的 / 如果存在
      const clean = id.startsWith('/') ? id.substring(1) : id;
      // 如果已经是 node/ 开头，返回多种格式
      if (clean.startsWith('node/')) {
        return [id, clean, `/${clean}`, clean.replace('node/', '/node/')];
      }
      // 否则添加 node/ 前缀
      return [id, `node/${clean}`, `/node/${clean}`, clean];
    };
    
    const nodeIdVariants = normalizeId(nodeId);
    
    // 辅助函数：检查事件是否匹配节点
    const matchesNode = (event: CloudEvent, field: 'source' | 'subject'): boolean => {
      const value = field === 'source' ? event.source : event.subject;
      if (!value) return false;
      return nodeIdVariants.some(vid => {
        const normalizedValue = value.startsWith('/') ? value.substring(1) : value;
        const normalizedVid = vid.startsWith('/') ? vid.substring(1) : vid;
        return value === vid || 
               normalizedValue === normalizedVid ||
               value === vid.replace('node/', '/node/') ||
               value === vid.replace('/node/', 'node/');
      });
    };
    
    // 输入：指向这个节点的事件（subject 匹配且是 request 类型）
    const inputsRaw = events.filter(e => {
      const isMatch = matchesNode(e, 'subject') && e.type.includes('request');
      return isMatch;
    });
    
    // 输出：从这个节点发出的事件（source 匹配）
    const outputsRaw = events.filter(e => {
      if (!matchesNode(e, 'source')) return false;
      // response 类型
      if (e.type.includes('response')) return true;
      // 或者包含 result/response/final_output 数据
      if (e.data && (e.data.result || e.data.response || e.data.final_output)) return true;
      // 或者不是 request 类型（可能是其他类型的响应）
      if (!e.type.includes('request')) return true;
      return false;
    });
    
    // 去重：基于事件的唯一标识符（id 或 time+source+subject+type 组合）
    const deduplicateEvents = (eventList: CloudEvent[]): CloudEvent[] => {
      const seen = new Set<string>();
      const unique: CloudEvent[] = [];
      
      for (const event of eventList) {
        // 使用 id 字段（如果存在），否则使用组合键
        const key = event.id || `${event.time}-${event.source}-${event.subject}-${event.type}`;
        if (!seen.has(key)) {
          seen.add(key);
          unique.push(event);
        }
      }
      
      return unique;
    };
    
    const inputs = deduplicateEvents(inputsRaw);
    const outputs = deduplicateEvents(outputsRaw);
    
    // 找到所有相关事件（用于状态判断）
    const allNodeEvents = events.filter(e => 
      matchesNode(e, 'source') || matchesNode(e, 'subject')
    );
    
    // 判断状态
    let status: NodeDetail['status'] = 'idle';
    const recentEvents = allNodeEvents.slice(-5);
    if (recentEvents.some((e: CloudEvent) => e.type.includes('error'))) {
      status = 'error';
    } else if (recentEvents.some((e: CloudEvent) => e.type.includes('request') && matchesNode(e, 'subject'))) {
      status = 'running';
    } else if (outputs.length > 0) {
      status = 'completed';
    }

    return {
      id: nodeId,
      type: data.nodes.find((n: { id: string; type: string }) => {
        const nId = n.id;
        return nId === nodeId || 
               nId === nodeId.replace('node/', '/node/') ||
               nId === nodeId.replace('/node/', 'node/') ||
               nId.replace('/', '') === nodeId.replace('/', '');
      })?.type || 'Node',
      inputs: inputs.sort((a, b) => {
        const timeA = a.extensions?.studio_timestamp || new Date(a.time).getTime();
        const timeB = b.extensions?.studio_timestamp || new Date(b.time).getTime();
        return timeB - timeA; // 最新的在前
      }),
      outputs: outputs.sort((a, b) => {
        const timeA = a.extensions?.studio_timestamp || new Date(a.time).getTime();
        const timeB = b.extensions?.studio_timestamp || new Date(b.time).getTime();
        return timeB - timeA; // 最新的在前
      }),
      status
    };
  };

  // 更新当前执行节点
  useEffect(() => {
    if (events.length === 0) return;
    
    // 找到最新的 request 事件
    const latestRequest = events
      .filter(e => e.type.includes('request'))
      .sort((a, b) => {
        const timeA = a.extensions?.studio_timestamp || new Date(a.time).getTime();
        const timeB = b.extensions?.studio_timestamp || new Date(b.time).getTime();
        return timeB - timeA;
      })[0];
    
    if (latestRequest) {
      setCurrentExecution(latestRequest.subject || latestRequest.source);
    }
  }, [events]);

  useEffect(() => {
    if (!containerRef.current) return;
    
    // 确保容器有正确的尺寸
    const container = containerRef.current;
    container.style.width = '100%';
    container.style.height = '100%';
    container.style.position = 'relative';

    // 如果已经存在实例，先销毁
    if (cyRef.current) {
      try {
        cyRef.current.destroy();
      } catch (e) {
        // 忽略销毁错误
      }
      cyRef.current = null;
    }

    cyRef.current = cytoscape({
      container: container,
      elements: [
        ...data.nodes.map(n => ({
          data: { id: n.id, label: n.id.split('/').pop() || n.id, type: n.type, status: 'idle' }
        })),
        ...data.edges.map(e => ({
          data: { id: `${e.from}-${e.to}`, source: e.from, target: e.to, count: e.count }
        }))
      ],
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#fff',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '14px',
            'font-weight': 'bold',
            'background-color': '#4a5568',
            'width': 80,
            'height': 80,
            'border-width': 3,
            'border-color': '#2d3748',
            'shape': 'round-rectangle'
          }
        },
        {
          selector: 'node[type="AgentNode"]',
          style: {
            'background-color': '#48bb78',
            'border-color': '#2f855a',
            'width': 100,
            'height': 100
          }
        },
        {
          selector: 'node[type="ToolNode"]',
          style: {
            'background-color': '#4299e1',
            'border-color': '#2b6cb0',
            'shape': 'rectangle',
            'width': 90,
            'height': 60
          }
        },
        {
          selector: 'node[type="CrewNode"]',
          style: {
            'background-color': '#ed8936',
            'border-color': '#c05621',
            'width': 120,
            'height': 80
          }
        },
        {
          selector: 'node[status="running"]',
          style: {
            'border-color': '#f6e05e',
            'border-width': 5,
            'background-opacity': 0.9
          }
        },
        {
          selector: 'node[status="completed"]',
          style: {
            'border-color': '#68d391',
            'border-width': 4
          }
        },
        {
          selector: 'node[status="error"]',
          style: {
            'border-color': '#fc8181',
            'background-color': '#e53e3e'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 3,
            'line-color': '#718096',
            'target-arrow-color': '#718096',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(count)',
            'text-rotation': 'autorotate',
            'text-margin-y': -15,
            'color': '#e2e8f0',
            'font-size': '12px',
            'font-weight': 'bold',
            'text-background-color': '#2d3748',
            'text-background-opacity': 0.8,
            'text-background-padding': '4px',
            'text-border-width': 0
          }
        },
        {
          selector: 'edge[active="true"]',
          style: {
            'line-color': '#f6e05e',
            'target-arrow-color': '#f6e05e',
            'width': 5
          }
        }
      ],
      layout: {
        name: 'breadthfirst',
        animate: true,
        animationDuration: 500,
        padding: 50
      }
    });

    // 节点点击事件 - 使用 ref 来访问最新的 events 和 data
    const handleNodeTap = (evt: any) => {
      try {
        if (!cyRef.current) return;
        const nodeId = evt.target.id();
        if (!nodeId) {
          console.warn('Node tap event has no nodeId');
          return;
        }
        
        console.log('Node clicked:', nodeId);
        console.log('Current events count:', events.length);
        console.log('Current nodes:', data.nodes.map((n: { id: string }) => n.id));
        
        // 直接使用 getNodeDetails，它使用最新的 props (events, data)
        const details = getNodeDetails(nodeId);
        
        console.log('Node details computed:', {
          id: details.id,
          inputs: details.inputs.length,
          outputs: details.outputs.length,
          status: details.status,
          inputs_sample: details.inputs.slice(0, 2).map((e: CloudEvent) => ({
            type: e.type,
            subject: e.subject,
            source: e.source
          })),
          outputs_sample: details.outputs.slice(0, 2).map((e: CloudEvent) => ({
            type: e.type,
            source: e.source,
            subject: e.subject
          }))
        });
        
        setSelectedNode(details);
      } catch (e) {
        console.error('Error handling node tap:', e);
        console.error('Event:', evt);
        console.error('Stack:', (e as Error).stack);
      }
    };

    if (cyRef.current) {
      cyRef.current.on('tap', 'node', handleNodeTap);
    }

    // 点击空白处取消选择
    const handleBackgroundTap = (evt: any) => {
      try {
        if (!cyRef.current) return;
        // 检查是否点击在背景上（不是节点或边）
        const cy = cyRef.current;
        // evt.target 可能是 cy 实例本身，或者 cy.container() 返回的 DOM 元素
        const target = evt.target;
        if (target === cy || (target && target === cy.container())) {
          setSelectedNode(null);
        }
      } catch (e) {
        console.error('Error handling background tap:', e);
      }
    };

    if (cyRef.current) {
      cyRef.current.on('tap', handleBackgroundTap);
    }

    return () => {
      if (cyRef.current) {
        try {
          cyRef.current.off('tap', 'node');
          cyRef.current.off('tap');
          cyRef.current.destroy();
        } catch (e) {
          // 忽略销毁错误
        }
        cyRef.current = null;
      }
    };
  }, [data]); // 只在 data 变化时重建，events 变化时只更新节点状态

  useEffect(() => {
    if (!cyRef.current) return;

    const cy = cyRef.current;
    
    // 检查 cytoscape 实例是否仍然有效
    try {
      if (!cy.container()) {
        return; // 容器已不存在，跳过更新
      }
    } catch (e) {
      return; // 实例已销毁，跳过更新
    }
    
    const nodes = data.nodes.map(n => {
      const details = getNodeDetails(n.id);
      const isCurrent = currentExecution === n.id;
      const shortLabel = n.id.split('/').pop() || n.id;
      
      return {
        data: { 
          id: n.id, 
          type: n.type,
          label: shortLabel,
          status: details.status,
          isCurrent
        }
      };
    });
    
    const edges = data.edges.map(e => ({
      data: { 
        source: e.from, 
        target: e.to, 
        count: e.count,
        active: currentExecution === e.to
      }
    }));

    try {
      // 使用 requestAnimationFrame 确保在下一个渲染周期更新
      requestAnimationFrame(() => {
        if (!cyRef.current) return;
        
        try {
          const currentCy = cyRef.current;
          if (!currentCy.container()) return;
          
          currentCy.batch(() => {
            currentCy.elements().remove();
            if (nodes.length > 0 || edges.length > 0) {
              currentCy.add([...nodes, ...edges]);
            }
            
            if (nodes.length > 0) {
              const layout = currentCy.layout({
                name: 'cose',
                animate: true,
                animationDuration: 500,
                padding: 50,
                nodeDimensionsIncludeLabels: true
              });
              layout.run();
            }
          });

          // 高亮当前执行节点
          if (currentExecution) {
            try {
              currentCy.nodes(`[id="${currentExecution}"]`).addClass('highlight');
            } catch (e) {
              // 忽略高亮错误
            }
          }
        } catch (e) {
          console.error('Error updating cytoscape graph:', e);
        }
      });
    } catch (e) {
      console.error('Error scheduling cytoscape update:', e);
    }

  }, [data, events, currentExecution]);

  const formatEventData = (event: CloudEvent): string => {
    if (!event.data) return 'No data';
    
    // 优先显示 task（输入）
    if (event.data.task) {
      const task = typeof event.data.task === 'string' ? event.data.task : JSON.stringify(event.data.task);
      return task.length > 300 ? task.substring(0, 300) + '...' : task;
    }
    
    // 优先显示 response（输出）
    if (event.data.response) {
      const response = typeof event.data.response === 'string' ? event.data.response : JSON.stringify(event.data.response);
      return response.length > 300 ? response.substring(0, 300) + '...' : response;
    }
    
    // 显示 final_output
    if (event.data.final_output) {
      const output = typeof event.data.final_output === 'string' ? event.data.final_output : JSON.stringify(event.data.final_output);
      return output.length > 300 ? output.substring(0, 300) + '...' : output;
    }
    
    // 显示 result
    if (event.data.result) {
      const result = typeof event.data.result === 'string' ? event.data.result : JSON.stringify(event.data.result);
      return result.length > 300 ? result.substring(0, 300) + '...' : result;
    }
    
    // 如果是字符串，直接返回
    if (typeof event.data === 'string') {
      return event.data.length > 300 ? event.data.substring(0, 300) + '...' : event.data;
    }
    
    // 否则格式化为 JSON
    const jsonStr = JSON.stringify(event.data, null, 2);
    return jsonStr.length > 300 ? jsonStr.substring(0, 300) + '...' : jsonStr;
  };

  return (
    <div className="topology-container">
      {/* 主拓扑图区域 */}
      <div 
        ref={containerRef} 
        className={`topology-graph ${selectedNode ? 'has-details' : ''}`}
        style={{ 
          borderRight: selectedNode ? '2px solid #4a5568' : 'none'
        }} 
      />
      
      {/* 节点详情面板 */}
      {selectedNode && (
        <div style={{
          width: '400px',
          height: '100%',
          backgroundColor: '#2d3748',
          color: '#e2e8f0',
          padding: '20px',
          overflowY: 'auto',
          borderLeft: '2px solid #4a5568',
          flexShrink: 0
        }}>
          <div style={{ marginBottom: '20px' }}>
            <button
              onClick={() => setSelectedNode(null)}
              style={{
                float: 'right',
                background: 'none',
                border: 'none',
                color: '#e2e8f0',
                fontSize: '24px',
                cursor: 'pointer',
                padding: '0 10px'
              }}
            >
              ×
            </button>
            <h2 style={{ margin: '0 0 10px 0', color: '#fff', fontSize: '20px' }}>
              {selectedNode.id.split('/').pop()}
            </h2>
            <div style={{ 
              display: 'inline-block',
              padding: '4px 12px',
              borderRadius: '12px',
              fontSize: '12px',
              fontWeight: 'bold',
              backgroundColor: 
                selectedNode.status === 'running' ? '#f6e05e' :
                selectedNode.status === 'completed' ? '#68d391' :
                selectedNode.status === 'error' ? '#fc8181' : '#718096',
              color: selectedNode.status === 'running' ? '#1a202c' : '#fff'
            }}>
              {selectedNode.status.toUpperCase()}
            </div>
            <div style={{ marginTop: '8px', fontSize: '14px', color: '#a0aec0' }}>
              类型: {selectedNode.type}
            </div>
          </div>

          {/* 输入事件 */}
          <div style={{ marginBottom: '30px' }}>
            <h3 style={{ 
              color: '#fff', 
              fontSize: '16px', 
              marginBottom: '12px',
              borderBottom: '2px solid #4a5568',
              paddingBottom: '8px'
            }}>
              输入 ({selectedNode.inputs.length})
            </h3>
            {selectedNode.inputs.length === 0 ? (
              <div style={{ color: '#718096', fontStyle: 'italic' }}>暂无输入</div>
            ) : (
              selectedNode.inputs.slice(0, 10).map((event) => (
                <div 
                  key={event.id || `${event.time}-${event.source}-${event.subject}-${event.type}`}
                  style={{
                    backgroundColor: '#1a202c',
                    padding: '12px',
                    marginBottom: '10px',
                    borderRadius: '6px',
                    border: '1px solid #4a5568'
                  }}
                >
                  <div style={{ fontSize: '12px', color: '#a0aec0', marginBottom: '6px' }}>
                    {event.type} • {new Date(event.time).toLocaleTimeString()}
                  </div>
                  <div style={{ 
                    fontSize: '13px', 
                    color: '#e2e8f0',
                    maxHeight: '150px',
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}>
                    {formatEventData(event)}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* 输出事件 */}
          <div>
            <h3 style={{ 
              color: '#fff', 
              fontSize: '16px', 
              marginBottom: '12px',
              borderBottom: '2px solid #4a5568',
              paddingBottom: '8px'
            }}>
              输出 ({selectedNode.outputs.length})
            </h3>
            {selectedNode.outputs.length === 0 ? (
              <div style={{ color: '#718096', fontStyle: 'italic', padding: '10px' }}>
                暂无输出事件
                <div style={{ fontSize: '12px', marginTop: '5px', color: '#a0aec0' }}>
                  提示：输出事件是 type="node.response" 且 source 来自此节点的事件
                </div>
              </div>
            ) : (
              selectedNode.outputs.slice(0, 10).map((event, idx) => (
                <div 
                  key={idx}
                  style={{
                    backgroundColor: '#1a202c',
                    padding: '12px',
                    marginBottom: '10px',
                    borderRadius: '6px',
                    border: '1px solid #4a5568'
                  }}
                >
                  <div style={{ fontSize: '12px', color: '#a0aec0', marginBottom: '6px' }}>
                    {event.type} • {new Date(event.time).toLocaleTimeString()}
                  </div>
                  <div style={{ 
                    fontSize: '13px', 
                    color: '#e2e8f0',
                    maxHeight: '150px',
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}>
                    {formatEventData(event)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TopologyView;
