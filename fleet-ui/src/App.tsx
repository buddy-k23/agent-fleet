import { BrowserRouter, Route, Routes, Link } from 'react-router-dom';
import { AppBar, Box, Button, CssBaseline, ThemeProvider, Toolbar, Typography, createTheme } from '@mui/material';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import { Dashboard } from './pages/Dashboard';
import { TaskMonitor } from './pages/TaskMonitor';
import { AgentBuilder } from './pages/AgentBuilder';
import { WorkflowDesigner } from './pages/WorkflowDesigner';
import { Login, Signup } from './pages/Auth';

const darkTheme = createTheme({
  palette: { mode: 'dark' },
});

function NavBar() {
  const { user, signOut } = useAuth();

  return (
    <AppBar position="static" data-testid="app-bar">
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Agent Fleet
        </Typography>
        {user && (
          <Box display="flex" gap={1} alignItems="center">
            <Button color="inherit" component={Link} to="/" data-testid="nav-dashboard">
              Dashboard
            </Button>
            <Button color="inherit" component={Link} to="/agents" data-testid="nav-agents">
              Agents
            </Button>
            <Button color="inherit" component={Link} to="/workflows" data-testid="nav-workflows">
              Workflows
            </Button>
            <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
              {user.email}
            </Typography>
            <Button
              color="inherit"
              onClick={() => signOut()}
              size="small"
              data-testid="nav-logout"
            >
              Logout
            </Button>
          </Box>
        )}
      </Toolbar>
    </AppBar>
  );
}

export default function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <AuthProvider>
        <BrowserRouter>
          <NavBar />
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/tasks/:taskId" element={<ProtectedRoute><TaskMonitor /></ProtectedRoute>} />
            <Route path="/agents" element={<ProtectedRoute><AgentBuilder /></ProtectedRoute>} />
            <Route path="/workflows" element={<ProtectedRoute><WorkflowDesigner /></ProtectedRoute>} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
