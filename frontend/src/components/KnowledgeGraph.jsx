import React, { useMemo } from 'react';
import { ReactFlow, Controls, Background, MarkerType } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';

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

  return (
    <div className="bg-space-800 border border-space-border rounded-lg p-6 flex flex-col h-[520px]">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-space-muted mb-6">KNOWLEDGE GRAPH</h2>
      
      <div className="flex-1 w-full rounded-md border border-space-border/50 overflow-hidden bg-space-900/50">
        {nodes.length > 0 ? (
          <ReactFlow 
            nodes={initialNodes} 
            edges={initialEdges}
            fitView
            attributionPosition="bottom-right"
          >
            <Background color="#1e2433" gap={16} />
            <Controls className="!bg-space-800 !border-space-border !fill-white" />
          </ReactFlow>
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
