import React, { useMemo, useState } from 'react';
import { ReactFlow, Controls, Background, MarkerType } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { X, Search } from 'lucide-react';

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes, edges, direction = 'LR') => {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction, ranksep: 100, nodesep: 50 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 150, height: 50 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? 'left' : 'top';
    node.sourcePosition = isHorizontal ? 'right' : 'bottom';

    // We are shifting the dagre node position (anchor=center center) to the top left
    // so it matches the React Flow node anchor point (top left).
    node.position = {
      x: nodeWithPosition.x - 75,
      y: nodeWithPosition.y - 25,
    };
    return node;
  });

  return { nodes, edges };
};

// Heuristic to guess node type based on name for coloring
const getNodeColor = (name) => {
  const lower = name.toLowerCase();
  if (lower.match(/star|planet|galaxy|moon|sun|asteroid|comet|nebula/)) return '#a855f7'; // purple for celestial
  if (lower.match(/mission|telescope|probe|rover|satellite|voyager|apollo|jwst|hubble/)) return '#3b82f6'; // blue for missions
  if (lower.match(/eclipse|supernova|gravity|radiation|flare|hole|shift|wave/)) return '#f97316'; // orange for phenomena
  if (lower.match(/nasa|esa|isro|roscosmos|spacex|agency/)) return '#ef4444'; // red for agencies
  return '#6366f1'; // default indigo
};

const KnowledgeGraph = ({ nodes = [], edges = [] }) => {
  const [selectedNode, setSelectedNode] = useState(null);

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!nodes.length) return { initialNodes: [], initialEdges: [] };

    const flowNodes = nodes.map((node) => {
      const color = getNodeColor(node);
      
      return {
        id: node,
        data: { label: node },
        style: {
          background: '#0d1117',
          color: '#ffffff',
          border: `2px solid ${color}`,
          borderRadius: '8px',
          padding: '10px 15px',
          fontSize: '12px',
          fontWeight: 'bold',
          width: 'auto',
          minWidth: '120px',
          textAlign: 'center'
        }
      };
    });

    const flowEdges = edges.map((edge, i) => ({
      id: `e-${i}`,
      source: edge.source,
      target: edge.target,
      label: edge.type,
      labelStyle: { fill: '#94a3b8', fontSize: 10, fontWeight: 600 },
      labelBgStyle: { fill: '#0d1117', opacity: 0.8 },
      style: { stroke: '#1e2433', strokeWidth: 1.5 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 15,
        height: 15,
        color: '#1e2433',
      },
    }));

    const layouted = getLayoutedElements(flowNodes, flowEdges, 'LR');
    return { initialNodes: layouted.nodes, initialEdges: layouted.edges };
  }, [nodes, edges]);

  // Filter edges for the selected node
  const relatedEdges = useMemo(() => {
    if (!selectedNode) return [];
    return edges.filter(e => e.source === selectedNode || e.target === selectedNode);
  }, [selectedNode, edges]);

  const handleNodeClick = (event, node) => {
    setSelectedNode(node.id);
  };

  const handleSearchTopic = () => {
    if (selectedNode) {
      window.dispatchEvent(new CustomEvent('setSearchQuery', { detail: selectedNode }));
    }
  };

  return (
    <div className="bg-space-800 border border-space-border rounded-lg p-6 flex flex-col h-[520px]">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-space-muted mb-6">KNOWLEDGE GRAPH</h2>
      
      <div className="flex-1 w-full rounded-md border border-space-border/50 overflow-hidden bg-space-900/50 relative">
        {nodes.length > 0 ? (
          <>
            <ReactFlow 
              nodes={initialNodes} 
              edges={initialEdges}
              fitView
              proOptions={{ hideAttribution: true }}
              onNodeClick={handleNodeClick}
            >
              <Background color="#1e2433" gap={16} />
              <Controls />
            </ReactFlow>

            {/* Overlay Panel */}
            {selectedNode && (
              <div className="absolute top-4 right-4 w-72 bg-space-800 border border-space-border rounded-lg shadow-xl flex flex-col z-10 max-h-[80%] overflow-hidden">
                <div className="flex items-center justify-between p-3 border-b border-space-border bg-space-900/30">
                  <h3 className="text-sm font-bold text-white truncate pr-2" title={selectedNode}>{selectedNode}</h3>
                  <button onClick={() => setSelectedNode(null)} className="text-space-muted hover:text-white transition-colors flex-shrink-0">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="p-3 overflow-y-auto custom-scrollbar flex-1 bg-space-800">
                  <h4 className="text-[10px] uppercase font-semibold text-space-muted mb-2 tracking-wider">Connected Entities</h4>
                  {relatedEdges.length > 0 ? (
                    <ul className="space-y-2">
                      {relatedEdges.map((edge, idx) => {
                        const isSource = edge.source === selectedNode;
                        const connectedNode = isSource ? edge.target : edge.source;
                        const arrow = isSource ? '→' : '←';
                        
                        return (
                          <li key={idx} className="text-xs flex items-center gap-2 bg-space-900/40 p-2 rounded border border-space-border/50 text-space-text">
                            <span className="text-space-muted font-mono">{arrow}</span>
                            <span className="text-space-accent italic truncate max-w-[80px]" title={edge.type}>{edge.type}</span>
                            <span className="text-space-muted font-mono">{arrow}</span>
                            <span className="font-semibold truncate" title={connectedNode}>{connectedNode}</span>
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <div className="text-xs text-space-muted italic">No connected entities.</div>
                  )}
                </div>

                <div className="p-3 border-t border-space-border bg-space-900/30">
                  <button 
                    onClick={handleSearchTopic}
                    className="w-full flex items-center justify-center gap-2 bg-space-accent/10 hover:bg-space-accent/20 text-space-accent border border-space-accent/30 rounded py-1.5 transition-colors text-xs font-semibold"
                  >
                    <Search className="w-3.5 h-3.5" />
                    Search this topic
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-space-muted">
            No graph data for this query
          </div>
        )}
      </div>
    </div>
  );
};

export default KnowledgeGraph;
