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
        bgcolor: '#0C0A1D',
        background: 'linear-gradient(180deg, #0C0A1D 0%, #12102B 100%)',
        color: '#E8E5F0',
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
            color: '#E8E5F0',
          }}
        >
          Agent Fleet
        </Typography>
      </Box>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)', mx: 2 }} />

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
                color: active ? '#fff' : 'rgba(232,229,240,0.55)',
                bgcolor: active ? alpha('#6366F1', 0.15) : 'transparent',
                '&:hover': {
                  bgcolor: active ? alpha('#6366F1', 0.2) : 'rgba(255,255,255,0.05)',
                  color: '#fff',
                },
                transition: 'all 150ms ease',
              }}
              data-testid={`nav-${item.label.toLowerCase()}`}
            >
              <ListItemIcon
                sx={{
                  minWidth: 36,
                  color: active ? '#818CF8' : 'rgba(232,229,240,0.4)',
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
      <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)', mx: 2 }} />
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Avatar
          sx={{
            width: 32,
            height: 32,
            bgcolor: alpha('#6366F1', 0.25),
            color: '#818CF8',
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
            sx={{ fontSize: 13, color: 'rgba(232,229,240,0.7)' }}
          >
            {user.email}
          </Typography>
        </Box>
        <IconButton
          size="small"
          onClick={() => signOut()}
          sx={{ color: 'rgba(232,229,240,0.4)', '&:hover': { color: '#EF4444' } }}
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
          <AppBar position="fixed" sx={{ bgcolor: '#0C0A1D' }} data-testid="app-bar">
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
              <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
              <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
            </Routes>
          </AppShell>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
