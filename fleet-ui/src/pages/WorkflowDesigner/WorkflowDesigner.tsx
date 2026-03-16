import { useCallback, useEffect, useState } from 'react';
import {
  Box, Button, Container, Dialog, DialogActions, DialogContent,
  DialogTitle, FormControl, InputLabel, MenuItem, Paper, Select,
  Snackbar, TextField, Typography,
} from '@mui/material';
import {
  ReactFlow, addEdge, useNodesState, useEdgesState, Controls, Background,
} from '@xyflow/react';
import type { Connection, Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/AuthContext';

const STAGE_COLORS: Record<string, string> = {
  architect: '#6366F1', 'backend-dev': '#10B981', 'frontend-dev': '#3B82F6',
  reviewer: '#8B5CF6', tester: '#F59E0B', integrator: '#6B7280',
};

const defaultNodes: Node[] = [
  { id: 'plan', position: { x: 250, y: 0 }, data: { label: 'Plan\n(Architect)', agent: 'architect', gate: 'approval' } },
  { id: 'backend', position: { x: 80, y: 150 }, data: { label: 'Backend\n(Backend Dev)', agent: 'backend-dev', gate: 'automated' } },
  { id: 'frontend', position: { x: 420, y: 150 }, data: { label: 'Frontend\n(Frontend Dev)', agent: 'frontend-dev', gate: 'automated' } },
  { id: 'review', position: { x: 250, y: 300 }, data: { label: 'Review\n(Reviewer)', agent: 'reviewer', gate: 'score' } },
  { id: 'e2e', position: { x: 250, y: 450 }, data: { label: 'E2E\n(Tester)', agent: 'tester', gate: 'automated' } },
  { id: 'deliver', position: { x: 250, y: 600 }, data: { label: 'Deliver\n(Integrator)', agent: 'integrator', gate: 'approval' } },
];

const defaultEdges: Edge[] = [
  { id: 'e1', source: 'plan', target: 'backend' },
  { id: 'e2', source: 'plan', target: 'frontend' },
  { id: 'e3', source: 'backend', target: 'review' },
  { id: 'e4', source: 'frontend', target: 'review' },
  { id: 'e5', source: 'review', target: 'e2e' },
  { id: 'e6', source: 'e2e', target: 'deliver' },
];

export default function WorkflowDesigner() {
  const { user } = useAuth();
  const [nodes, setNodes, onNodesChange] = useNodesState(defaultNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(defaultEdges);
  const [workflowName, setWorkflowName] = useState('Full Development Pipeline');
  const [_workflows, setWorkflows] = useState<{ id: string; name: string }[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [toast, setToast] = useState('');

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  useEffect(() => {
    supabase.from('workflows').select('id, name').then(({ data }) => {
      if (data) setWorkflows(data);
    });
  }, []);

  const exportYaml = () => {
    const stages = nodes.map((node) => {
      const deps = edges.filter((e) => e.target === node.id).map((e) => e.source);
      return {
        name: node.id,
        agent: node.data.agent || node.id,
        ...(deps.length > 0 ? { depends_on: deps } : {}),
        gate: { type: node.data.gate || 'automated' },
      };
    });
    const yaml = `name: "${workflowName}"\nstages:\n${stages.map((s) =>
      `  - name: ${s.name}\n    agent: ${s.agent}${s.depends_on ? `\n    depends_on:\n${s.depends_on.map((d: string) => `      - ${d}`).join('\n')}` : ''}\n    gate:\n      type: ${s.gate.type}`
    ).join('\n')}`;
    navigator.clipboard.writeText(yaml);
    setToast('YAML copied to clipboard!');
  };

  const saveToSupabase = async () => {
    if (!user) return;
    const stages = nodes.map((node) => {
      const deps = edges.filter((e) => e.target === node.id).map((e) => e.source);
      return {
        name: node.id,
        agent: node.data.agent || node.id,
        depends_on: deps,
        gate: { type: node.data.gate || 'automated' },
      };
    });
    await supabase.from('workflows').insert({
      user_id: user.id,
      name: workflowName,
      stages,
    });
    setToast('Workflow saved!');
    supabase.from('workflows').select('id, name').then(({ data }) => {
      if (data) setWorkflows(data);
    });
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Box display="flex" gap={2} alignItems="center">
          <Typography variant="h4" data-testid="workflow-title">Workflows</Typography>
          <TextField
            size="small"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            sx={{ width: 300 }}
            data-testid="workflow-name"
          />
        </Box>
        <Box display="flex" gap={1}>
          <Button variant="outlined" onClick={exportYaml} data-testid="export-btn">
            Export YAML
          </Button>
          <Button variant="contained" onClick={saveToSupabase} data-testid="save-btn">
            Save
          </Button>
        </Box>
      </Box>

      <Paper sx={{ height: 650 }} data-testid="workflow-canvas">
        <ReactFlow
          nodes={nodes.map((n) => ({
            ...n,
            style: {
              border: `2px solid ${STAGE_COLORS[n.data.agent as string] || '#6B7280'}`,
              borderRadius: 8,
              padding: 8,
              background: 'transparent',
              fontFamily: '"Fira Code", monospace',
              fontSize: 12,
              whiteSpace: 'pre-line' as const,
              textAlign: 'center' as const,
              minWidth: 120,
            },
          }))}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={(_, node) => setSelectedNode(node)}
          onPaneClick={() => setSelectedNode(null)}
          fitView
        >
          <Controls />
          <Background />
        </ReactFlow>
      </Paper>

      {/* Properties Panel */}
      {selectedNode && (
        <Dialog open onClose={() => setSelectedNode(null)} maxWidth="xs" fullWidth>
          <DialogTitle>Stage: {selectedNode.id}</DialogTitle>
          <DialogContent>
            <TextField
              label="Agent"
              fullWidth
              margin="dense"
              value={selectedNode.data.agent || ''}
              onChange={(e) => {
                setNodes((nds) => nds.map((n) =>
                  n.id === selectedNode.id ? { ...n, data: { ...n.data, agent: e.target.value } } : n
                ));
              }}
              data-testid="prop-agent"
            />
            <FormControl fullWidth margin="dense">
              <InputLabel>Gate Type</InputLabel>
              <Select
                value={selectedNode.data.gate || 'automated'}
                label="Gate Type"
                onChange={(e) => {
                  setNodes((nds) => nds.map((n) =>
                    n.id === selectedNode.id ? { ...n, data: { ...n.data, gate: e.target.value } } : n
                  ));
                }}
                data-testid="prop-gate"
              >
                <MenuItem value="automated">Automated</MenuItem>
                <MenuItem value="score">Score</MenuItem>
                <MenuItem value="approval">Approval</MenuItem>
                <MenuItem value="custom">Custom</MenuItem>
              </Select>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setSelectedNode(null)}>Close</Button>
          </DialogActions>
        </Dialog>
      )}

      <Snackbar
        open={!!toast}
        autoHideDuration={3000}
        onClose={() => setToast('')}
        message={toast}
      />
    </Container>
  );
}
