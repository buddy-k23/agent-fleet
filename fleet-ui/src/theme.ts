import { createTheme } from '@mui/material';

// Agent Fleet Design System — generated via UI/UX Pro Max
// Style: Flat Design | Colors: Indigo + Emerald | Fonts: Fira Code + Fira Sans

const palette = {
  primary: '#6366F1',
  primaryLight: '#818CF8',
  secondary: '#818CF8',
  success: '#10B981',
  error: '#EF4444',
  warning: '#F59E0B',
  info: '#3B82F6',
};

export const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: palette.primary, light: palette.primaryLight },
    secondary: { main: palette.secondary },
    success: { main: palette.success },
    error: { main: palette.error },
    warning: { main: palette.warning },
    info: { main: palette.info },
    background: { default: '#F5F3FF', paper: '#FFFFFF' },
    text: { primary: '#1E1B4B', secondary: '#6B7280' },
  },
  typography: {
    fontFamily: '"Fira Sans", -apple-system, sans-serif',
    h1: { fontFamily: '"Fira Code", monospace', fontWeight: 700 },
    h2: { fontFamily: '"Fira Code", monospace', fontWeight: 700 },
    h3: { fontFamily: '"Fira Code", monospace', fontWeight: 600 },
    h4: { fontFamily: '"Fira Code", monospace', fontWeight: 600 },
    h5: { fontFamily: '"Fira Code", monospace', fontWeight: 600 },
    h6: { fontFamily: '"Fira Code", monospace', fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  shape: { borderRadius: 8 },
  components: {
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          border: '1px solid #E5E4F0',
          transition: 'border-color 150ms ease',
          '&:hover': { borderColor: palette.primary },
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          borderRadius: 8,
          transition: 'all 150ms ease',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontFamily: '"Fira Code", monospace', fontSize: '0.75rem' },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { border: '1px solid #E5E4F0' },
      },
    },
    MuiAppBar: {
      defaultProps: { elevation: 0 },
    },
  },
});

export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: palette.primary, light: palette.primaryLight },
    secondary: { main: palette.secondary },
    success: { main: palette.success },
    error: { main: palette.error },
    warning: { main: palette.warning },
    info: { main: palette.info },
    background: { default: '#0F0D1A', paper: '#1A1730' },
    text: { primary: '#E8E5F0', secondary: '#9CA3AF' },
  },
  typography: {
    fontFamily: '"Fira Sans", -apple-system, sans-serif',
    h1: { fontFamily: '"Fira Code", monospace', fontWeight: 700 },
    h2: { fontFamily: '"Fira Code", monospace', fontWeight: 700 },
    h3: { fontFamily: '"Fira Code", monospace', fontWeight: 600 },
    h4: { fontFamily: '"Fira Code", monospace', fontWeight: 600 },
    h5: { fontFamily: '"Fira Code", monospace', fontWeight: 600 },
    h6: { fontFamily: '"Fira Code", monospace', fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  shape: { borderRadius: 8 },
  components: {
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          border: '1px solid #2D2B3D',
          transition: 'border-color 150ms ease',
          '&:hover': { borderColor: palette.primary },
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          borderRadius: 8,
          transition: 'all 150ms ease',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontFamily: '"Fira Code", monospace', fontSize: '0.75rem' },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { border: '1px solid #2D2B3D' },
      },
    },
    MuiAppBar: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { borderBottom: '1px solid #2D2B3D' },
      },
    },
  },
});
