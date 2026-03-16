import { useState } from 'react';
import { BrowserRouter, Route, Routes, Link } from 'react-router-dom';
import {
  Box, Button, CssBaseline, Drawer, IconButton, List, ListItemButton,
  ListItemIcon, ListItemText, ThemeProvider, Toolbar, Typography,
  useMediaQuery, AppBar,
} from '@mui/material';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import { Dashboard } from './pages/Dashboard';
import { TaskMonitor } from './pages/TaskMonitor';
import { AgentBuilder } from './pages/AgentBuilder';
import { WorkflowDesigner } from './pages/WorkflowDesigner';
import { Login, Signup } from './pages/Auth';
import { Settings } from './pages/Settings';
import { SubmitTask } from './pages/SubmitTask';
import { Projects } from './pages/Projects';
import { Chat } from './pages/Chat';
import { Admin } from './pages/Admin';
import { lightTheme, darkTheme } from './theme';

const SIDEBAR_WIDTH = 220;

const NAV_ITEMS = [
  { label: 'Projects', path: '/projects', icon: '📁' },
  { label: 'Dashboard', path: '/', icon: '📊' },
  { label: 'Chat', path: '/chat', icon: '💬' },
  { label: 'Submit', path: '/submit', icon: '🚀' },
  { label: 'Agents', path: '/agents', icon: '🤖' },
  { label: 'Workflows', path: '/workflows', icon: '🔀' },
  { label: 'Settings', path: '/settings', icon: '⚙️' },
  { label: 'Admin', path: '/admin', icon: '🛡️' },
];

function AppShell({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth();
  const isMobile = useMediaQuery('(max-width:768px)');
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (!user) return <>{children}</>;

  const sidebar = (
    <Box
      sx={{
        width: SIDEBAR_WIDTH,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'background.paper',
        borderRight: 1,
        borderColor: 'divider',
      }}
      data-testid="sidebar"
    >
      <Toolbar>
        <Typography variant="h6" sx={{ fontFamily: '"Fira Code", monospace', fontSize: 16 }}>
          Agent Fleet
        </Typography>
      </Toolbar>
      <List sx={{ flex: 1, px: 1 }}>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.path}
            component={Link}
            to={item.path}
            onClick={() => setDrawerOpen(false)}
            sx={{ borderRadius: 1, mb: 0.5 }}
            data-testid={`nav-${item.label.toLowerCase()}`}
          >
            <ListItemIcon sx={{ minWidth: 36, fontSize: 18 }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <Typography variant="caption" color="text.secondary" noWrap>
          {user.email}
        </Typography>
        <Button
          size="small"
          fullWidth
          onClick={() => signOut()}
          sx={{ mt: 1 }}
          data-testid="nav-logout"
        >
          Sign Out
        </Button>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {isMobile ? (
        <>
          <AppBar position="fixed" data-testid="app-bar">
            <Toolbar>
              <IconButton
                color="inherit"
                onClick={() => setDrawerOpen(true)}
                data-testid="menu-btn"
              >
                ☰
              </IconButton>
              <Typography variant="h6" sx={{ ml: 1 }}>Agent Fleet</Typography>
            </Toolbar>
          </AppBar>
          <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>
            {sidebar}
          </Drawer>
          <Box component="main" sx={{ flex: 1, pt: 8 }}>
            {children}
          </Box>
        </>
      ) : (
        <>
          {sidebar}
          <Box component="main" sx={{ flex: 1, overflow: 'auto' }}>
            {children}
          </Box>
        </>
      )}
    </Box>
  );
}

export default function App() {
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)');
  const [isDark] = useState(prefersDark);
  const theme = isDark ? darkTheme : lightTheme;

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <BrowserRouter>
          <AppShell>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/tasks/:taskId" element={<ProtectedRoute><TaskMonitor /></ProtectedRoute>} />
              <Route path="/agents" element={<ProtectedRoute><AgentBuilder /></ProtectedRoute>} />
              <Route path="/workflows" element={<ProtectedRoute><WorkflowDesigner /></ProtectedRoute>} />
              <Route path="/submit" element={<ProtectedRoute><SubmitTask /></ProtectedRoute>} />
              <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
              <Route path="/projects" element={<ProtectedRoute><Projects /></ProtectedRoute>} />
              <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
              <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
            </Routes>
          </AppShell>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
