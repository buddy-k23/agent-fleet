import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box, Card, CardContent, Chip, Container, Grid, LinearProgress,
  Paper, Typography,
} from '@mui/material';
import { supabase } from '../../lib/supabase';

const STAGES = ['plan', 'backend', 'frontend', 'review', 'e2e', 'deliver'];

const STAGE_COLORS: Record<string, string> = {
  pending: '#6B7280', running: '#6366F1', completed: '#10B981', error: '#EF4444',
};

interface TaskData {
  id: string;
  description: string;
  status: string;
  current_stage: string | null;
  completed_stages: string[];
  total_tokens: number;
  workflow_name: string;
  error_message: string | null;
  created_at: string;
}

interface Execution {
  id: string;
  stage: string;
  agent: string;
  model: string;
  status: string;
  tokens_used: number;
  summary: string | null;
  files_changed: string[];
}

interface GateResult {
  id: string;
  execution_id: string;
  gate_type: string;
  passed: boolean;
  score: number | null;
  details: Record<string, unknown>;
}

function getStageStatus(stage: string, task: TaskData): string {
  if (task.completed_stages?.includes(stage)) return 'completed';
  if (task.current_stage === stage) return 'running';
  return 'pending';
}

export default function TaskMonitor() {
  const { taskId } = useParams<{ taskId: string }>();
  const [task, setTask] = useState<TaskData | null>(null);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [gates, setGates] = useState<GateResult[]>([]);

  const load = async () => {
    if (!taskId) return;
    const { data: t } = await supabase.from('tasks').select('*').eq('id', taskId).single();
    if (t) setTask(t);
    const { data: e } = await supabase.from('executions').select('*').eq('task_id', taskId).order('started_at');
    if (e) setExecutions(e);
    const { data: g } = await supabase.from('gate_results').select('*');
    if (g) setGates(g);
  };

  useEffect(() => {
    load();
    const ch = supabase.channel(`task-${taskId}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'tasks', filter: `id=eq.${taskId}` }, () => load())
      .on('postgres_changes', { event: '*', schema: 'public', table: 'executions' }, () => load())
      .subscribe();
    return () => { supabase.removeChannel(ch); };
  }, [taskId]);

  if (!task) return <Container sx={{ py: 4 }}><Typography>Loading...</Typography></Container>;

  const completedCount = task.completed_stages?.length || 0;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" data-testid="monitor-title" gutterBottom>
        Task Monitor
      </Typography>

      {/* Task Info */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="body1" data-testid="task-description">{task.description}</Typography>
        <Box display="flex" gap={2} mt={1} alignItems="center">
          <Chip label={task.status} color={task.status === 'completed' ? 'success' : task.status === 'error' ? 'error' : 'warning'} size="small" />
          <Typography variant="body2" color="text.secondary" sx={{ fontFamily: '"Fira Code"' }}>
            {task.total_tokens.toLocaleString()} tokens
          </Typography>
          <Typography variant="body2" color="text.secondary">{task.workflow_name}</Typography>
        </Box>
        {task.error_message && (
          <Typography variant="body2" color="error" sx={{ mt: 1 }}>{task.error_message}</Typography>
        )}
        <LinearProgress
          variant="determinate"
          value={(completedCount / STAGES.length) * 100}
          sx={{ mt: 2, height: 8, borderRadius: 4 }}
          data-testid="progress-bar"
        />
      </Paper>

      {/* Pipeline Visualizer */}
      <Box display="flex" gap={1} mb={3} flexWrap="wrap" data-testid="pipeline-visualizer">
        {STAGES.map((stage, i) => {
          const status = getStageStatus(stage, task);
          return (
            <Box key={stage} display="flex" alignItems="center">
              <Box
                sx={{
                  px: 2, py: 1, borderRadius: 1,
                  border: 2, borderColor: STAGE_COLORS[status],
                  bgcolor: status === 'running' ? `${STAGE_COLORS.running}22` : 'transparent',
                  animation: status === 'running' ? 'pulse 2s infinite' : 'none',
                  '@keyframes pulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.6 } },
                }}
                data-testid={`stage-${stage}`}
              >
                <Typography variant="caption" sx={{ fontFamily: '"Fira Code"', color: STAGE_COLORS[status] }}>
                  {stage}
                </Typography>
                {status === 'completed' && <Typography variant="caption" sx={{ ml: 1 }}>✓</Typography>}
                {status === 'error' && <Typography variant="caption" sx={{ ml: 1 }}>✗</Typography>}
              </Box>
              {i < STAGES.length - 1 && (
                <Box sx={{ width: 24, height: 2, bgcolor: STAGE_COLORS[status], mx: 0.5 }} />
              )}
            </Box>
          );
        })}
      </Box>

      {/* Agent Cards + Gate Results */}
      <Grid container spacing={2}>
        {executions.map((exec) => {
          const gate = gates.find((g) => g.execution_id === exec.id);
          return (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={exec.id}>
              <Card data-testid={`agent-card-${exec.stage}`}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontFamily: '"Fira Code"' }}>{exec.stage}</Typography>
                  <Typography variant="body2" color="text.secondary">{exec.agent}</Typography>
                  <Chip label={exec.model.split('/')[1] || exec.model} size="small" sx={{ mt: 1 }} />
                  <Box mt={1}>
                    <Chip label={exec.status} size="small" color={exec.status === 'completed' ? 'success' : exec.status === 'running' ? 'warning' : 'error'} />
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, fontFamily: '"Fira Code"' }}>
                    {exec.tokens_used.toLocaleString()} tokens
                  </Typography>
                  {gate && (
                    <Box mt={1} sx={{ borderTop: 1, borderColor: 'divider', pt: 1 }}>
                      <Typography variant="caption">
                        Gate: {gate.gate_type} — {gate.passed ? '✓ Pass' : '✗ Fail'}
                        {gate.score !== null && ` (${gate.score}/100)`}
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Container>
  );
}
