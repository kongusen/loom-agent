
import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import type { TopologyData } from '../types';

interface TopologyViewProps {
  data: TopologyData;
}

const TopologyView: React.FC<TopologyViewProps> = ({ data }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: [], // Initial empty
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(id)',
            'color': '#fff',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '12px',
            'background-color': '#666',
            'width': 40,
            'height': 40
          }
        },
        {
            selector: 'node[type="AgentNode"]',
            style: {
                'background-color': '#4CAF50',
                'width': 60,
                'height': 60
            }
        },
        {
            selector: 'node[type="ToolNode"]',
            style: {
                'background-color': '#2196F3',
                'shape': 'rectangle'
            }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#555',
            'target-arrow-color': '#555',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(weight)',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
            'color': '#aaa',
            'font-size': '10px'
          }
        }
      ],
      layout: {
        name: 'grid'
      }
    });

    return () => {
      cyRef.current?.destroy();
    };
  }, []);

  useEffect(() => {
        if (!cyRef.current) return;

        const cy = cyRef.current;
        
        const nodes = data.nodes.map(n => ({
            data: { id: n.id, type: n.type }
        }));
        
        const edges = data.edges.map(e => ({
            data: { source: e.from, target: e.to, weight: e.count }
        }));

        cy.batch(() => {
            cy.elements().remove();
            cy.add([...nodes, ...edges]);
            
            const layout = cy.layout({
                name: 'cose',
                animate: true,
                animationDuration: 500,
                padding: 50
            });
            layout.run();
        });

  }, [data]);

  return <div ref={containerRef} style={{ width: '100%', height: '100%', backgroundColor: '#1e1e1e' }} />;
};

export default TopologyView;
