import { useEffect, useState } from 'react';
import {
  Box, Card, CardContent, Chip, Container, Grid, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, ToggleButton,
  ToggleButtonGroup, Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../../lib/supabase';

interface Task {
  id: string;
  description: string;
  status: string;
  workflow_name: string;
  total_tokens: number;
  completed_stages: string[];
  created_at: string;
}

const STATUS_COLOR: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  completed: 'success', running: 'warning', error: 'error', queued: 'info',
};

function KPICard({ title, value, color }: {
  title: string; value: string | number; color?: string;
}) {
  return (
    <Card data-testid={`kpi-${title.toLowerCase().replace(/\s/g, '-')}`}>
      <CardContent>
        <Typography variant="body2" color="text.secondary">{title}</Typography>
        <Typography
          variant="h4"
          sx={{ fontFamily: '"Fira Code", monospace', color: color || 'primary.main', my: 1 }}
        >
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

function fmt(n: number): string {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return String(n);
}

function ago(d: string): string {
  const m = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState('all');
  const navigate = useNavigate();

  const load = async () => {
    const { data } = await supabase
      .from('tasks').select('*').order('created_at', { ascending: false });
    if (data) setTasks(data);
  };

  useEffect(() => {
    load();
    const ch = supabase.channel('tasks-rt')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'tasks' }, () => load())
      .subscribe();
    return () => { supabase.removeChannel(ch); };
  }, []);

  const filtered = filter === 'all' ? tasks : tasks.filter((t) => t.status === filter);
  const running = tasks.filter((t) => t.status === 'running').length;
  const done = tasks.filter((t) => t.status === 'completed').length;
  const tokens = tasks.reduce((s, t) => s + (t.total_tokens || 0), 0);
  const rate = tasks.length ? Math.round((done / tasks.length) * 100) : 0;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" data-testid="dashboard-title" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid size={{ xs: 6, md: 3 }}><KPICard title="Active" value={running} color="#10B981" /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KPICard title="Completed" value={done} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KPICard title="Tokens" value={fmt(tokens)} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KPICard title="Success" value={`${rate}%`} /></Grid>
      </Grid>

      <Box sx={{ mb: 2 }}>
        <ToggleButtonGroup value={filter} exclusive onChange={(_, v) => v && setFilter(v)} size="small" data-testid="status-filter">
          <ToggleButton value="all">All</ToggleButton>
          <ToggleButton value="running">Running</ToggleButton>
          <ToggleButton value="completed">Completed</ToggleButton>
          <ToggleButton value="error">Error</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <TableContainer data-testid="task-table">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Task</TableCell>
              <TableCell>Workflow</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Stages</TableCell>
              <TableCell>Tokens</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.length === 0 && (
              <TableRow><TableCell colSpan={6} align="center" data-testid="no-tasks">
                <Typography color="text.secondary">No tasks yet</Typography>
              </TableCell></TableRow>
            )}
            {filtered.map((t) => (
              <TableRow key={t.id} hover sx={{ cursor: 'pointer' }}
                onClick={() => navigate(`/tasks/${t.id}`)} data-testid={`task-row-${t.id}`}>
                <TableCell>
                  <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>{t.description}</Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontFamily: '"Fira Code"' }}>
                    {t.id.slice(0, 8)}
                  </Typography>
                </TableCell>
                <TableCell><Chip label={t.workflow_name || 'default'} size="small" variant="outlined" /></TableCell>
                <TableCell><Chip label={t.status} size="small" color={STATUS_COLOR[t.status] || 'default'} /></TableCell>
                <TableCell>{t.completed_stages?.length || 0}/6</TableCell>
                <TableCell sx={{ fontFamily: '"Fira Code"' }}>{fmt(t.total_tokens || 0)}</TableCell>
                <TableCell><Typography variant="caption">{ago(t.created_at)}</Typography></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Container>
  );
}
