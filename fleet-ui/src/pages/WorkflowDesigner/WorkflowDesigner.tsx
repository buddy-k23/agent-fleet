import { useCallback, useState } from 'react';
import { Box, Button, Container, Paper, Typography } from '@mui/material';
import {
  ReactFlow,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  Connection,
  Node,
  Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const initialNodes: Node[] = [
  { id: 'plan', position: { x: 250, y: 0 }, data: { label: 'Plan (Architect)' }, type: 'default' },
  { id: 'backend', position: { x: 100, y: 150 }, data: { label: 'Backend Dev' }, type: 'default' },
  { id: 'frontend', position: { x: 400, y: 150 }, data: { label: 'Frontend Dev' }, type: 'default' },
  { id: 'review', position: { x: 250, y: 300 }, data: { label: 'Reviewer' }, type: 'default' },
  { id: 'e2e', position: { x: 250, y: 450 }, data: { label: 'Tester' }, type: 'default' },
  { id: 'deliver', position: { x: 250, y: 600 }, data: { label: 'Integrator' }, type: 'default' },
];

const initialEdges: Edge[] = [
  { id: 'e-plan-backend', source: 'plan', target: 'backend' },
  { id: 'e-plan-frontend', source: 'plan', target: 'frontend' },
  { id: 'e-backend-review', source: 'backend', target: 'review' },
  { id: 'e-frontend-review', source: 'frontend', target: 'review' },
  { id: 'e-review-e2e', source: 'review', target: 'e2e' },
  { id: 'e-e2e-deliver', source: 'e2e', target: 'deliver' },
];

export default function WorkflowDesigner() {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  const exportYaml = () => {
    const stages = nodes.map((node) => {
      const deps = edges
        .filter((e) => e.target === node.id)
        .map((e) => e.source);
      return {
        name: node.id,
        agent: node.id,
        depends_on: deps.length > 0 ? deps : undefined,
      };
    });
    const yaml = JSON.stringify({ name: 'Custom Workflow', stages }, null, 2);
    navigator.clipboard.writeText(yaml);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4" data-testid="workflow-title">
          Workflow Designer
        </Typography>
        <Button variant="contained" onClick={exportYaml} data-testid="export-btn">
          Export YAML
        </Button>
      </Box>
      <Paper sx={{ height: 700 }} data-testid="workflow-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
        >
          <Controls />
          <Background />
        </ReactFlow>
      </Paper>
    </Container>
  );
}
