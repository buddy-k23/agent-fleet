import { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { Alert, Box, Button, Container, Link, TextField, Typography } from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const { error: err } = await signIn(email, password);
    setLoading(false);
    if (err) {
      setError(err.message);
    } else {
      navigate('/');
    }
  };

  return (
    <Container maxWidth="xs" sx={{ py: 8 }}>
      <Typography variant="h4" align="center" gutterBottom data-testid="login-title">
        Agent Fleet
      </Typography>
      <Typography variant="body2" align="center" color="text.secondary" sx={{ mb: 4 }}>
        Sign in to your account
      </Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }} data-testid="login-error">{error}</Alert>}
      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          label="Email"
          type="email"
          fullWidth
          margin="normal"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          data-testid="login-email"
        />
        <TextField
          label="Password"
          type="password"
          fullWidth
          margin="normal"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          data-testid="login-password"
        />
        <Button
          type="submit"
          variant="contained"
          fullWidth
          size="large"
          disabled={loading}
          sx={{ mt: 2, mb: 2 }}
          data-testid="login-submit"
        >
          {loading ? 'Signing in...' : 'Sign In'}
        </Button>
        <Typography variant="body2" align="center">
          Don't have an account?{' '}
          <Link component={RouterLink} to="/signup" data-testid="login-signup-link">
            Sign up
          </Link>
        </Typography>
      </Box>
    </Container>
  );
}
