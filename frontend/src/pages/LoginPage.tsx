import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import { ApiError } from '../api/client';

export default function LoginPage() {
  const [roll, setRoll] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    const normalised = roll.trim().toLowerCase();
    if (!normalised) {
      setError('Please enter your roll number.');
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.sendOtp(normalised);
      navigate('/otp', { state: { roll: normalised, email: res.email, cooldown: res.cooldown } });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError('Registration already complete for this roll number.');
        } else if (err.status === 429) {
          const remaining = (err.data as { remaining?: number }).remaining;
          setError(remaining ? `Wait ${remaining}s before requesting a new OTP.` : 'Too many requests. Please wait.');
        } else {
          setError(err.message);
        }
      } else {
        setError('Network error. Check your connection and try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="faceid-screen profile-page login-page">
      <header className="faceid-header login-header">
        <div className="profile-logo" aria-hidden="true">
          <svg viewBox="0 0 60 60" width="56" height="56">
            <circle cx="30" cy="24" r="15" fill="none" stroke="currentColor" strokeWidth="1.8" />
            {/* Eyes */}
            <circle cx="23" cy="22" r="2.5" fill="currentColor" />
            <circle cx="37" cy="22" r="2.5" fill="currentColor" />
            {/* Smile */}
            <path d="M23 29 Q30 35 37 29" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" />
            {/* Neck / body */}
            <ellipse cx="30" cy="52" rx="16" ry="10" fill="none" stroke="currentColor" strokeWidth="1.8" />
          </svg>
        </div>
        <p className="profile-campus">IIIT Kurnool</p>
        <h1 className="profile-title">Photo registration</h1>
        <p className="profile-subtitle">Sign in with your institute roll number.</p>
      </header>

      <main className="profile-main login-card">
        <form className="profile-form" onSubmit={handleSubmit} noValidate>
          <div className="profile-field">
            <label className="profile-label" htmlFor="roll-input">
              Roll Number
            </label>
            <input
              id="roll-input"
              type="text"
              className="profile-input"
              value={roll}
              onChange={(e) => { setRoll(e.target.value); setError(''); }}
              placeholder="Your roll number"
              autoComplete="username"
              autoFocus
              disabled={loading}
              spellCheck={false}
            />
          </div>

          {error && (
            <div className="profile-error" role="alert">{error}</div>
          )}

          <button
            type="submit"
            className="profile-submit-btn"
            disabled={loading || !roll.trim()}
          >
            {loading
              ? <span className="faceid-spinner" style={{ borderTopColor: '#000', borderColor: 'rgba(0,0,0,0.2)' }} />
              : 'Send sign-in code'}
          </button>
        </form>

        <p className="profile-footer-note">
          We will send a sign-in code to your institute email.
        </p>
      </main>
    </div>
  );
}
