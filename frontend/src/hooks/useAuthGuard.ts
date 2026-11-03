import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';

/**
 * Redirect to /login if the user is not authenticated.
 * Returns the roll number on success.
 */
export function useAuthGuard(): void {
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    authApi.me().catch(() => {
      if (!cancelled) navigate('/login', { replace: true });
    });
    return () => { cancelled = true; };
  }, [navigate]);
}

