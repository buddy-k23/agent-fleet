import { useEffect, useState } from 'react';
import {
  Box, Card, CardContent, Container, Grid, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography,
} from '@mui/material';
import { supabase } from '../../lib/supabase';

interface Stats {
  totalUsers: number;
  totalTasks: number;
  totalTokens: number;
  totalAgents: number;
}

interface UserRow {
  id: string;
  email: string;
  created_at: string;
}

function StatCard({ title, value }: { title: string; value: string | number }) {
  return (
    <Card data-testid={`admin-stat-${title.toLowerCase().replace(/\s/g, '-')}`}>
      <CardContent>
        <Typography variant="body2" color="text.secondary">{title}</Typography>
        <Typography variant="h4" sx={{ fontFamily: '"Fira Code"', color: 'primary.main', my: 1 }}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function Admin() {
  const [stats, setStats] = useState<Stats>({ totalUsers: 0, totalTasks: 0, totalTokens: 0, totalAgents: 0 });
  const [tasks, setTasks] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    const load = async () => {
      // Use service role would be better, but for now use user's view
      const { data: taskData } = await supabase.from('tasks').select('*');
      const { data: agentData } = await supabase.from('agents').select('id');
      const { data: profileData } = await supabase.from('profiles').select('id');

      const totalTokens = (taskData || []).reduce(
        (sum: number, t: Record<string, unknown>) => sum + ((t.total_tokens as number) || 0), 0
      );

      setStats({
        totalUsers: profileData?.length || 0,
        totalTasks: taskData?.length || 0,
        totalTokens,
        totalAgents: agentData?.length || 0,
      });
      setTasks(taskData || []);
    };
    load();
  }, []);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" data-testid="admin-title" gutterBottom>
        Admin Dashboard
      </Typography>

      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatCard title="Users" value={stats.totalUsers} />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatCard title="Tasks" value={stats.totalTasks} />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatCard title="Tokens" value={stats.totalTokens.toLocaleString()} />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatCard title="Agents" value={stats.totalAgents} />
        </Grid>
      </Grid>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Recent Tasks</Typography>
          <TableContainer data-testid="admin-tasks-table">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Tokens</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tasks.slice(0, 20).map((t) => (
                  <TableRow key={t.id as string}>
                    <TableCell sx={{ fontFamily: '"Fira Code"', fontSize: 12 }}>
                      {(t.id as string).slice(0, 8)}
                    </TableCell>
                    <TableCell>{(t.description as string)?.slice(0, 60)}</TableCell>
                    <TableCell>{t.status as string}</TableCell>
                    <TableCell sx={{ fontFamily: '"Fira Code"' }}>{t.total_tokens as number}</TableCell>
                    <TableCell>{new Date(t.created_at as string).toLocaleDateString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Container>
  );
}
