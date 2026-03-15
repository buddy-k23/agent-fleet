import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Container, LinearProgress, Paper, Step, StepLabel, Stepper, Typography } from '@mui/material';
import { createTaskWebSocket, fetchTask } from '../../services/api';
import type { TaskDetail } from '../../services/api';

const STAGES = ['plan', 'backend', 'frontend', 'review', 'e2e', 'deliver'];

export default function TaskMonitor() {
  const { taskId } = useParams<{ taskId: string }>();
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [wsMessages, setWsMessages] = useState<string[]>([]);

  useEffect(() => {
    if (!taskId) return;
    fetchTask(taskId).then(setTask).catch(() => {});

    const ws = createTaskWebSocket(taskId);
    ws.onmessage = (event) => {
      setWsMessages((prev) => [...prev, event.data]);
      fetchTask(taskId).then(setTask).catch(() => {});
    };
    return () => ws.close();
  }, [taskId]);

  const activeStep = task ? STAGES.indexOf(task.current_stage || '') : -1;
  const completedCount = task?.completed_stages?.length || 0;

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" data-testid="monitor-title" gutterBottom>
        Task: {taskId}
      </Typography>

      {task && (
        <>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="body1" data-testid="task-description">
              {task.description}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Status: {task.status} | Tokens: {task.total_tokens}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={(completedCount / STAGES.length) * 100}
              sx={{ mt: 2 }}
              data-testid="progress-bar"
            />
          </Paper>

          <Stepper activeStep={activeStep} alternativeLabel data-testid="stage-stepper">
            {STAGES.map((stage) => (
              <Step
                key={stage}
                completed={task.completed_stages?.includes(stage)}
                data-testid={`step-${stage}`}
              >
                <StepLabel>{stage}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </>
      )}

      {wsMessages.length > 0 && (
        <Paper sx={{ p: 2, mt: 3, maxHeight: 300, overflow: 'auto' }} data-testid="ws-log">
          <Typography variant="subtitle2">Live Updates</Typography>
          {wsMessages.map((msg, i) => (
            <Typography key={i} variant="body2" sx={{ fontFamily: 'monospace', fontSize: 12 }}>
              {msg}
            </Typography>
          ))}
        </Paper>
      )}
    </Container>
  );
}
