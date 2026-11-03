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
    <div className="faceid-screen profile-page">
      {/* Face icon */}
      <header className="faceid-header" style={{ marginBottom: 0 }}>
        <div className="profile-logo" aria-hidden="true">
          <svg viewBox="0 0 60 60" width="64" height="64">
            <circle cx="30" cy="24" r="15" fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" />
            {/* Eyes */}
            <circle cx="23" cy="22" r="2.5" fill="rgba(255,255,255,0.7)" />
            <circle cx="37" cy="22" r="2.5" fill="rgba(255,255,255,0.7)" />
            {/* Smile */}
            <path d="M23 29 Q30 35 37 29" stroke="rgba(255,255,255,0.7)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            {/* Neck / body */}
            <ellipse cx="30" cy="52" rx="16" ry="10" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5" />
          </svg>
        </div>
        <h1 className="profile-title">Face Registration</h1>
        <p className="profile-subtitle" style={{ marginTop: 6 }}>IIIT Kurnool · Biometric Enrollment</p>
      </header>

      <main className="profile-main">
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
              placeholder="e.g. 524cs0019"
              autoComplete="username"
              autoFocus
              disabled={loading}
              spellCheck={false}
            />
            <p className="profile-hint">Lowercase only — e.g. 524cs0019</p>
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
              : 'Send OTP →'}
          </button>
        </form>

        <p className="profile-footer-note">
          An OTP will be sent to your institute email.<br />
          Check SPAM if not received within 30 seconds.
        </p>
      </main>
    </div>
  );
}
