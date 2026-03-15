import { useEffect, useState } from 'react';
import { Box, Card, CardContent, Chip, Container, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import { fetchTasks, Task } from '../../services/api';

const statusColor: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  completed: 'success',
  running: 'warning',
  error: 'error',
  queued: 'info',
};

export default function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    const load = () => fetchTasks().then(setTasks).catch(() => {});
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" data-testid="dashboard-title" gutterBottom>
        Agent Fleet Dashboard
      </Typography>
      {tasks.length === 0 && (
        <Typography color="text.secondary" data-testid="no-tasks">
          No tasks yet. Submit one via CLI or API.
        </Typography>
      )}
      {tasks.map((task) => (
        <Card key={task.task_id} sx={{ mb: 2 }} data-testid={`task-card-${task.task_id}`}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Link to={`/tasks/${task.task_id}`} style={{ textDecoration: 'none' }}>
                <Typography variant="h6" data-testid={`task-id-${task.task_id}`}>
                  {task.task_id}
                </Typography>
              </Link>
              <Chip
                label={task.status}
                color={statusColor[task.status] || 'default'}
                size="small"
                data-testid={`task-status-${task.task_id}`}
              />
            </Box>
            <Typography variant="body2" color="text.secondary">
              {task.description}
            </Typography>
          </CardContent>
        </Card>
      ))}
    </Container>
  );
}
