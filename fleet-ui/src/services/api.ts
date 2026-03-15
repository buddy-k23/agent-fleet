const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export interface Task {
  task_id: string;
  repo: string;
  description: string;
  status: string;
  workflow: string;
}

export interface TaskDetail extends Task {
  current_stage: string | null;
  completed_stages: string[];
  total_tokens: number;
}

export async function fetchTasks(): Promise<Task[]> {
  const res = await fetch(`${API_BASE}/api/v1/tasks`);
  const data = await res.json();
  return data.tasks;
}

export async function fetchTask(taskId: string): Promise<TaskDetail> {
  const res = await fetch(`${API_BASE}/api/v1/tasks/${taskId}`);
  return res.json();
}

export async function submitTask(repo: string, description: string, workflow = 'default'): Promise<Task> {
  const res = await fetch(`${API_BASE}/api/v1/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo, description, workflow }),
  });
  return res.json();
}

export async function fetchAgents(): Promise<Record<string, unknown>[]> {
  const res = await fetch(`${API_BASE}/api/v1/agents`);
  return res.json();
}

export function createTaskWebSocket(taskId: string): WebSocket {
  const wsBase = API_BASE.replace('http', 'ws');
  return new WebSocket(`${wsBase}/ws/tasks/${taskId}`);
}
