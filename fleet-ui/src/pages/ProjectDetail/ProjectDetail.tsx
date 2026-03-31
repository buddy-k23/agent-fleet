import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box, Button, Chip, CircularProgress, Container, Divider,
  Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import RocketLaunchOutlinedIcon from '@mui/icons-material/RocketLaunchOutlined';
import { supabase } from '../../lib/supabase';

interface Project {
  id: string;
  name: string;
  repo_path: string;
  languages: string[];
  frameworks: string[];
  test_frameworks: string[];
  databases: string[];
  has_ci: boolean;
  has_docker: boolean;
  estimated_loc: number;
  created_at: string;
}

interface Task {
  id: string;
  description: string;
  status: string;
  created_at: string;
}

const STATUS_COLOR: Record<string, 'default' | 'warning' | 'info' | 'success' | 'error'> = {
  queued: 'default',
  running: 'info',
  completed: 'success',
  failed: 'error',
  cancelled: 'default',
};

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    Promise.all([
      supabase.from('projects').select('*').eq('id', projectId).single(),
      supabase.from('tasks').select('id, description, status, created_at').eq('project_id', projectId).order('created_at', { ascending: false }),
    ]).then(([{ data: proj }, { data: taskData }]) => {
      if (proj) setProject(proj);
      if (taskData) setTasks(taskData);
      setLoading(false);
    });
  }, [projectId]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!project) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography color="error" data-testid="project-not-found">Project not found.</Typography>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/projects')} sx={{ mt: 2 }}>
          Back to Projects
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box display="flex" alignItems="center" gap={1} mb={3}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/projects')}
          size="small"
          data-testid="back-to-projects"
        >
          Projects
        </Button>
        <Typography color="text.disabled">/</Typography>
        <Typography variant="h5" sx={{ fontFamily: '"Fira Code"' }} data-testid="project-detail-name">
          {project.name}
        </Typography>
      </Box>

      {/* Metadata */}
      <Box mb={3}>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {project.repo_path}
        </Typography>
        <Stack direction="row" flexWrap="wrap" gap={0.5} mb={1}>
          {project.languages?.map((l) => <Chip key={l} label={l} size="small" color="primary" />)}
          {project.frameworks?.map((f) => <Chip key={f} label={f} size="small" variant="outlined" />)}
          {project.test_frameworks?.map((t) => <Chip key={t} label={t} size="small" variant="outlined" />)}
          {project.databases?.map((d) => <Chip key={d} label={d} size="small" variant="outlined" />)}
          {project.has_ci && <Chip label="CI" size="small" color="success" variant="outlined" />}
          {project.has_docker && <Chip label="Docker" size="small" color="info" variant="outlined" />}
        </Stack>
        {project.estimated_loc > 0 && (
          <Typography variant="caption" color="text.secondary">
            ~{project.estimated_loc.toLocaleString()} LOC
          </Typography>
        )}
      </Box>

      <Divider sx={{ mb: 3 }} />

      {/* Tasks */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Tasks ({tasks.length})</Typography>
        <Button
          variant="contained"
          size="small"
          startIcon={<RocketLaunchOutlinedIcon />}
          onClick={() => navigate(`/submit?project_id=${projectId}`)}
          data-testid="submit-task-for-project"
        >
          Submit Task
        </Button>
      </Box>

      {tasks.length === 0 ? (
        <Typography color="text.secondary" data-testid="no-tasks">
          No tasks yet. Submit one to get started.
        </Typography>
      ) : (
        <Table size="small" data-testid="project-tasks-table">
          <TableHead>
            <TableRow>
              <TableCell>Description</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tasks.map((t) => (
              <TableRow
                key={t.id}
                hover
                sx={{ cursor: 'pointer' }}
                onClick={() => navigate(`/tasks/${t.id}`)}
                data-testid={`task-row-${t.id}`}
              >
                <TableCell sx={{ maxWidth: 400 }}>
                  <Typography variant="body2" noWrap>{t.description}</Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={t.status}
                    size="small"
                    color={STATUS_COLOR[t.status] ?? 'default'}
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="caption" color="text.secondary">
                    {new Date(t.created_at).toLocaleString()}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Container>
  );
}
