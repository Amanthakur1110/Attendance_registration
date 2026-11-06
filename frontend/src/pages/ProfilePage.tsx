import { useState, type FormEvent, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import { ApiError } from '../api/client';

const BRANCHES = [
  { value: 'CSE', label: 'CSE – Computer Science & Engineering' },
  { value: 'AIDS', label: 'AIDS – AI & Data Science' },
  { value: 'MECH', label: 'MECH – Mechanical Engineering' },
  { value: 'ECE', label: 'ECE – Electronics & Communication' },
];

export default function ProfilePage() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [branch, setBranch] = useState('');
  const [roll, setRoll] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Guard: must be logged in
  useEffect(() => {
    authApi
      .me()
      .then((res) => {
        setRoll(res.user.roll);
        // If profile already filled, skip straight to capture
        if (res.user.name && res.user.branch) {
          if (res.user.completed) {
            navigate('/done', { replace: true });
          } else {
            navigate('/capture', { replace: true });
          }
        }
      })
      .catch(() => navigate('/login', { replace: true }));
  }, [navigate]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');

    const trimmedName = name.trim();
    if (!trimmedName || trimmedName.length < 2) {
      setError('Please enter your full name.');
      return;
    }
    if (!branch) {
      setError('Please select your branch.');
      return;
    }

    setLoading(true);
    try {
      await authApi.saveProfile(trimmedName, branch);
      navigate('/capture', { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Network error. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="faceid-screen profile-page">
      <header className="faceid-header" style={{ marginBottom: 0 }}>
        <div className="profile-logo" aria-hidden="true">
          <svg viewBox="0 0 60 60" width="56" height="56">
            <circle cx="30" cy="22" r="14" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <ellipse cx="30" cy="52" rx="20" ry="12" fill="none" stroke="currentColor" strokeWidth="1.8" />
          </svg>
        </div>
        <p className="profile-campus">IIIT Kurnool</p>
        <h1 className="profile-title">Your Details</h1>
        {roll && <p className="profile-roll">{roll}</p>}
      </header>

      <main className="profile-main">
        <p className="profile-subtitle">
          We need a few details before capturing your photos.
        </p>

        <form className="profile-form" onSubmit={handleSubmit} noValidate>
          {/* Name field */}
          <div className="profile-field">
            <label className="profile-label" htmlFor="student-name">
              Full Name
            </label>
            <input
              id="student-name"
              type="text"
              className="profile-input"
              value={name}
              onChange={(e) => { setName(e.target.value); setError(''); }}
              placeholder="Your full name"
              autoComplete="name"
              autoFocus
              disabled={loading}
              maxLength={100}
            />
          </div>

          {/* Branch selection */}
          <div className="profile-field">
            <label className="profile-label">Branch</label>
            <div className="profile-branches">
              {BRANCHES.map((b) => (
                <button
                  key={b.value}
                  type="button"
                  className={`profile-branch-btn ${branch === b.value ? 'profile-branch-btn--selected' : ''}`}
                  onClick={() => { setBranch(b.value); setError(''); }}
                  disabled={loading}
                >
                  <span className="profile-branch-btn__tag">{b.value}</span>
                  <span className="profile-branch-btn__name">
                    {b.label.split('–')[1]?.trim()}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="profile-error" role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="profile-submit-btn"
            disabled={loading || !name.trim() || !branch}
          >
            {loading ? (
              <span className="faceid-spinner" style={{ borderTopColor: '#000', borderColor: 'rgba(0,0,0,0.2)' }} />
            ) : (
              'Continue'
            )}
          </button>
        </form>
      </main>
    </div>
  );
}
