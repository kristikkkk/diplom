/** Тема Material UI: палитра, типографика и стили компонентов для всего UI. */
import { createTheme } from '@mui/material/styles';

export const editorialTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#004ac6',
      light: '#2563eb',
      dark: '#003ea8',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#545f73',
      contrastText: '#ffffff',
    },
    success: {
      main: '#006242',
    },
    background: {
      default: '#f9f9ff',
      paper: '#ffffff',
    },
    text: {
      primary: '#111c2d',
      secondary: '#434655',
    },
    divider: 'rgba(195, 198, 215, 0.35)',
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontWeight: 700, letterSpacing: '-0.02em' },
    h2: { fontWeight: 700, letterSpacing: '-0.02em' },
    h3: { fontWeight: 700, letterSpacing: '-0.01em' },
    h4: { fontWeight: 700, letterSpacing: '-0.01em' },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    button: { fontWeight: 600, textTransform: 'none' },
  },
  shape: {
    borderRadius: 16,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#f9f9ff',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 24,
          border: '1px solid rgba(195, 198, 215, 0.18)',
          boxShadow: '0 20px 40px rgba(17, 28, 45, 0.06)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        rounded: {
          borderRadius: 20,
        },
      },
    },
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
      styleOverrides: {
        root: {
          borderRadius: 9999,
          paddingLeft: 20,
          paddingRight: 20,
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #004ac6, #2563eb)',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(255,255,255,0.8)',
          color: '#111c2d',
          backdropFilter: 'blur(16px)',
          boxShadow: '0 6px 24px rgba(17, 28, 45, 0.06)',
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined',
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 14,
          backgroundColor: '#f0f3ff',
          '&.Mui-focused': {
            backgroundColor: '#ffffff',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 10,
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 20,
        },
      },
    },
  },
});

