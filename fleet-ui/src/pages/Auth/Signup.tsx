import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Alert, Box, Button, Container, Link, TextField, Typography } from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';

export default function Signup() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const { signUp } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    const { error: err } = await signUp(email, password);
    setLoading(false);
    if (err) {
      setError(err.message);
    } else {
      setSuccess('Account created! Check your email to confirm, then sign in.');
    }
  };

  return (
    <Container maxWidth="xs" sx={{ py: 8 }}>
      <Typography variant="h4" align="center" gutterBottom data-testid="signup-title">
        Create Account
      </Typography>
      <Typography variant="body2" align="center" color="text.secondary" sx={{ mb: 4 }}>
        Sign up for Agent Fleet
      </Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }} data-testid="signup-error">{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} data-testid="signup-success">{success}</Alert>}
      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          label="Email"
          type="email"
          fullWidth
          margin="normal"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          data-testid="signup-email"
        />
        <TextField
          label="Password"
          type="password"
          fullWidth
          margin="normal"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          helperText="Minimum 6 characters"
          data-testid="signup-password"
        />
        <Button
          type="submit"
          variant="contained"
          fullWidth
          size="large"
          disabled={loading}
          sx={{ mt: 2, mb: 2 }}
          data-testid="signup-submit"
        >
          {loading ? 'Creating account...' : 'Sign Up'}
        </Button>
        <Typography variant="body2" align="center">
          Already have an account?{' '}
          <Link component={RouterLink} to="/login" data-testid="signup-login-link">
            Sign in
          </Link>
        </Typography>
      </Box>
    </Container>
  );
}
