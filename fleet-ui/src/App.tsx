import { BrowserRouter, Route, Routes, Link } from 'react-router-dom';
import { AppBar, Box, Button, CssBaseline, ThemeProvider, Toolbar, Typography, createTheme } from '@mui/material';
import { Dashboard } from './pages/Dashboard';
import { TaskMonitor } from './pages/TaskMonitor';
import { AgentBuilder } from './pages/AgentBuilder';
import { WorkflowDesigner } from './pages/WorkflowDesigner';

const darkTheme = createTheme({
  palette: { mode: 'dark' },
});

export default function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <BrowserRouter>
        <AppBar position="static" data-testid="app-bar">
          <Toolbar>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              Agent Fleet
            </Typography>
            <Box display="flex" gap={1}>
              <Button color="inherit" component={Link} to="/" data-testid="nav-dashboard">
                Dashboard
              </Button>
              <Button color="inherit" component={Link} to="/agents" data-testid="nav-agents">
                Agents
              </Button>
              <Button color="inherit" component={Link} to="/workflows" data-testid="nav-workflows">
                Workflows
              </Button>
            </Box>
          </Toolbar>
        </AppBar>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tasks/:taskId" element={<TaskMonitor />} />
          <Route path="/agents" element={<AgentBuilder />} />
          <Route path="/workflows" element={<WorkflowDesigner />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
