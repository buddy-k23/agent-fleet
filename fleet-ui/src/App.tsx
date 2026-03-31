import { useState } from 'react';
import { BrowserRouter, Route, Routes, Link, useLocation } from 'react-router-dom';
import {
  Box, Button, CssBaseline, Drawer, IconButton, List, ListItemButton,
  ListItemIcon, ListItemText, ThemeProvider, Toolbar, Typography,
  useMediaQuery, AppBar, Avatar, Divider, alpha,
} from '@mui/material';
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined';
import DashboardOutlinedIcon from '@mui/icons-material/DashboardOutlined';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import RocketLaunchOutlinedIcon from '@mui/icons-material/RocketLaunchOutlined';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';
import AccountTreeOutlinedIcon from '@mui/icons-material/AccountTreeOutlined';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import AdminPanelSettingsOutlinedIcon from '@mui/icons-material/AdminPanelSettingsOutlined';
import MenuIcon from '@mui/icons-material/Menu';
import LogoutIcon from '@mui/icons-material/Logout';
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
import { ProjectDetail } from './pages/ProjectDetail';
import { Chat } from './pages/Chat';
import { Admin } from './pages/Admin';
import { lightTheme, darkTheme } from './theme';

const SIDEBAR_WIDTH = 260;

const AUTH_ROUTES = ['/login', '/signup'];

const NAV_ITEMS = [
  { label: 'Projects', path: '/projects', icon: FolderOutlinedIcon },
  { label: 'Dashboard', path: '/', icon: DashboardOutlinedIcon },
  { label: 'Chat', path: '/chat', icon: ChatBubbleOutlineIcon },
  { label: 'Submit', path: '/submit', icon: RocketLaunchOutlinedIcon },
  { label: 'Agents', path: '/agents', icon: SmartToyOutlinedIcon },
  { label: 'Workflows', path: '/workflows', icon: AccountTreeOutlinedIcon },
  { label: 'Settings', path: '/settings', icon: SettingsOutlinedIcon },
  { label: 'Admin', path: '/admin', icon: AdminPanelSettingsOutlinedIcon },
];

function AppShell({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth();
  const location = useLocation();
  const isMobile = useMediaQuery('(max-width:768px)');
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Hide sidebar on auth pages regardless of login state
  if (!user || AUTH_ROUTES.includes(location.pathname)) return <>{children}</>;

  const isActive = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);

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
        color: 'text.primary',
      }}
      data-testid="sidebar"
    >
      {/* Brand */}
      <Box sx={{ px: 2.5, py: 2.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Box
          sx={{
            width: 34,
            height: 34,
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #6366F1, #818CF8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            fontSize: 15,
            color: '#fff',
            fontFamily: '"Fira Code", monospace',
          }}
        >
          AF
        </Box>
        <Typography
          variant="h6"
          sx={{
            fontFamily: '"Fira Code", monospace',
            fontSize: 15,
            fontWeight: 700,
            letterSpacing: '-0.02em',
            color: 'text.primary',
          }}
        >
          Agent Fleet
        </Typography>
      </Box>

      <Divider sx={{ borderColor: 'divider', mx: 2 }} />

      {/* Navigation */}
      <List sx={{ flex: 1, px: 1.5, pt: 1.5 }}>
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.path);
          const Icon = item.icon;
          return (
            <ListItemButton
              key={item.path}
              component={Link}
              to={item.path}
              onClick={() => setDrawerOpen(false)}
              sx={{
                borderRadius: '8px',
                mb: 0.25,
                py: 1,
                px: 1.5,
                color: active ? 'primary.main' : 'text.secondary',
                bgcolor: active ? alpha('#6366F1', 0.1) : 'transparent',
                '&:hover': {
                  bgcolor: active ? alpha('#6366F1', 0.15) : 'action.hover',
                  color: active ? 'primary.main' : 'text.primary',
                },
                transition: 'all 150ms ease',
              }}
              data-testid={`nav-${item.label.toLowerCase()}`}
            >
              <ListItemIcon
                sx={{
                  minWidth: 36,
                  color: active ? 'primary.light' : 'text.secondary',
                }}
              >
                <Icon fontSize="small" />
              </ListItemIcon>
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{
                  fontSize: 14,
                  fontWeight: active ? 600 : 400,
                }}
              />
              {active && (
                <Box
                  sx={{
                    width: 4,
                    height: 20,
                    borderRadius: 2,
                    bgcolor: '#6366F1',
                    position: 'absolute',
                    right: 0,
                  }}
                />
              )}
            </ListItemButton>
          );
        })}
      </List>

      {/* User section */}
      <Divider sx={{ borderColor: 'divider', mx: 2 }} />
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Avatar
          sx={{
            width: 32,
            height: 32,
            bgcolor: alpha('#6366F1', 0.15),
            color: 'primary.light',
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          {user.email?.charAt(0).toUpperCase()}
        </Avatar>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            variant="body2"
            noWrap
            sx={{ fontSize: 13, color: 'text.secondary' }}
          >
            {user.email}
          </Typography>
        </Box>
        <IconButton
          size="small"
          onClick={() => signOut()}
          sx={{ color: 'text.secondary', '&:hover': { color: 'error.main' } }}
          data-testid="nav-logout"
        >
          <LogoutIcon fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {isMobile ? (
        <>
          <AppBar position="fixed" sx={{ bgcolor: 'background.paper' }} data-testid="app-bar">
            <Toolbar>
              <IconButton
                color="inherit"
                onClick={() => setDrawerOpen(true)}
                data-testid="menu-btn"
              >
                <MenuIcon />
              </IconButton>
              <Typography variant="h6" sx={{ ml: 1, fontFamily: '"Fira Code", monospace', fontSize: 15 }}>
                Agent Fleet
              </Typography>
            </Toolbar>
          </AppBar>
          <Drawer
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            PaperProps={{ sx: { bgcolor: 'transparent', border: 'none' } }}
          >
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
              <Route path="/projects/:projectId" element={<ProtectedRoute><ProjectDetail /></ProtectedRoute>} />
              <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
              <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
            </Routes>
          </AppShell>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
