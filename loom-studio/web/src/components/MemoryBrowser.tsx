
import React, { useState } from 'react';
import type { CloudEvent } from '../types';

interface MemoryBrowserProps {
  events: CloudEvent[];
}

const MemoryBrowser: React.FC<MemoryBrowserProps> = ({ events }) => {
  const [selectedNode, setSelectedNode] = useState<string>('');
  
  // Extract unique nodes that have memory events
  const nodes = Array.from(
      new Set(
          events
          .filter(e => e.type.startsWith('memory.'))
          .map(e => e.source)
      )
  ).sort();

  const filteredEvents = events.filter(
      e => e.source === selectedNode && e.type.startsWith('memory.')
  );

  return (
    <div style={{ padding: '20px', color: '#fff', height: '100%', overflow: 'auto' }}>
      <h2>Memory Browser</h2>
      <div style={{ marginBottom: '20px' }}>
         <label style={{ marginRight: '10px' }}>Select Node:</label>
         <select 
            value={selectedNode} 
            onChange={e => setSelectedNode(e.target.value)}
            style={{ padding: '5px', background: '#333', color: '#fff', border: '1px solid #555' }}
         >
             <option value="">-- Select --</option>
             {nodes.map(n => <option key={n} value={n}>{n}</option>)}
         </select>
      </div>

      <div className="memory-stream">
          {filteredEvents.length === 0 ? (
              <p style={{ color: '#aaa' }}>No memory events found for this node.</p>
          ) : (
              filteredEvents.map(e => (
                  <div key={e.id} style={{ 
                      background: '#333', 
                      marginBottom: '10px', 
                      padding: '10px', 
                      borderRadius: '4px',
                      borderLeft: '4px solid #9c27b0'
                  }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                          <span style={{ fontWeight: 'bold', color: '#e1bee7' }}>{e.type}</span>
                          <span style={{ fontSize: '0.8em', color: '#aaa' }}>{e.time}</span>
                      </div>
                      <pre style={{ 
                          fontSize: '0.9em', 
                          color: '#ccc', 
                          overflowX: 'auto',
                          margin: 0
                      }}>
                          {JSON.stringify(e.data, null, 2)}
                      </pre>
                  </div>
              ))
          )}
      </div>
    </div>
  );
};

export default MemoryBrowser;
