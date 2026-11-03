import { useState, useEffect, useRef, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { authApi } from '../api/auth';
import { ApiError } from '../api/client';
import { useCountdown } from '../hooks/useCountdown';

interface LocationState {
  roll: string;
  email: string;
  cooldown: number;
}

export default function OtpPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState | null;

  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [resendKey, setResendKey] = useState(0);
  const [resendLoading, setResendLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const COOLDOWN = state?.cooldown ?? 60;
  const { seconds: countdown } = useCountdown(COOLDOWN, false, resendKey);

  useEffect(() => {
    if (!state?.roll) navigate('/login', { replace: true });
  }, [state, navigate]);

  if (!state?.roll) return null;

  const otpString = otp.join('');

  function handleOtpChange(index: number, value: string) {
    const digit = value.replace(/\D/g, '').slice(-1);
    const next = [...otp];
    next[index] = digit;
    setOtp(next);
    setError('');
    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  }

  function handleOtpKeyDown(index: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  }

  function handleOtpPaste(e: React.ClipboardEvent) {
    const paste = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (paste.length === 6) {
      e.preventDefault();
      setOtp(paste.split(''));
      inputRefs.current[5]?.focus();
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (otpString.length !== 6) {
      setError('Please enter all 6 digits.');
      return;
    }
    setLoading(true);
    try {
      await authApi.verifyOtp(state!.roll, otpString);
      navigate('/profile', { replace: true });
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setError('');
    setSuccessMsg('');
    setResendLoading(true);
    try {
      const res = await authApi.sendOtp(state!.roll);
      setSuccessMsg(`OTP email is being sent to ${res.email}.`);
      setOtp(['', '', '', '', '', '']);
      setResendKey((k) => k + 1);
      inputRefs.current[0]?.focus();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError('Network error. Please try again.');
    } finally {
      setResendLoading(false);
    }
  }

  return (
    <div className="faceid-screen profile-page">
      <header className="faceid-header" style={{ marginBottom: 0 }}>
        <div className="profile-logo" aria-hidden="true">
          <svg viewBox="0 0 60 60" width="52" height="52">
            <rect x="12" y="8" width="36" height="44" rx="6" fill="rgba(255,255,255,0.1)" stroke="rgba(255,255,255,0.35)" strokeWidth="1.5" />
            <rect x="22" y="4" width="16" height="8" rx="3" fill="rgba(255,255,255,0.15)" stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" />
            <circle cx="30" cy="32" r="6" fill="none" stroke="rgba(255,255,255,0.5)" strokeWidth="1.5" />
            <line x1="30" y1="26" x2="30" y2="20" stroke="rgba(255,255,255,0.5)" strokeWidth="1.5" />
          </svg>
        </div>
        <h1 className="profile-title">Enter OTP</h1>
        <p className="profile-subtitle" style={{ marginTop: 6 }}>
          Sending to <strong style={{ color: '#b6f36a' }}>{state.email}</strong>
        </p>
        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>
          Check your SPAM folder if not received.
        </p>
      </header>

      <main className="profile-main">
        <form onSubmit={handleSubmit} noValidate>
          {/* 6-box OTP input */}
          <div className="otp-boxes" onPaste={handleOtpPaste}>
            {otp.map((digit, i) => (
              <input
                key={i}
                ref={(el) => { inputRefs.current[i] = el; }}
                type="text"
                inputMode="numeric"
                pattern="\d*"
                maxLength={1}
                className={`otp-box ${digit ? 'otp-box--filled' : ''} ${error ? 'otp-box--error' : ''}`}
                value={digit}
                onChange={(e) => handleOtpChange(i, e.target.value)}
                onKeyDown={(e) => handleOtpKeyDown(i, e)}
                disabled={loading}
                aria-label={`Digit ${i + 1}`}
                autoFocus={i === 0}
              />
            ))}
          </div>

          {error && (
            <div className="profile-error" role="alert" style={{ marginTop: 16 }}>{error}</div>
          )}
          {successMsg && (
            <div className="profile-success" role="status" style={{ marginTop: 16 }}>{successMsg}</div>
          )}

          <button
            type="submit"
            className="profile-submit-btn"
            disabled={loading || otpString.length < 6}
            style={{ marginTop: 28 }}
          >
            {loading
              ? <span className="faceid-spinner" style={{ borderTopColor: '#000', borderColor: 'rgba(0,0,0,0.2)' }} />
              : 'Verify OTP'}
          </button>
        </form>

        <div className="otp-footer">
          {countdown > 0 ? (
            <p className="otp-timer">Resend available in <strong>{countdown}s</strong></p>
          ) : (
            <button className="otp-resend-btn" onClick={handleResend} disabled={resendLoading}>
              {resendLoading ? 'Sending…' : 'Resend OTP'}
            </button>
          )}
          <button className="otp-back-btn" onClick={() => navigate('/login')}>
            ← Back
          </button>
        </div>
      </main>
    </div>
  );
}
