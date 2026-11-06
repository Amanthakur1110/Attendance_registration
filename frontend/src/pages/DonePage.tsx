import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';

export default function DonePage() {
  const navigate = useNavigate();
  const [userInfo, setUserInfo] = useState<{ roll: string; name?: string | null; branch?: string | null } | null>(null);

  useEffect(() => {
    authApi
      .me()
      .then((res) =>
        setUserInfo({
          roll: res.user.roll,
          name: res.user.name,
          branch: res.user.branch,
        })
      )
      .catch(() => navigate('/login', { replace: true }));
  }, [navigate]);

  async function handleLogout() {
    await authApi.logout().catch(() => {});
    navigate('/login', { replace: true });
  }

  return (
    <div className="faceid-screen profile-page">
      <main
        className="profile-main"
        style={{ justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}
      >
        <div className="done-check" aria-hidden="true">
          <svg viewBox="0 0 80 80" width="100" height="100">
            <circle cx="40" cy="40" r="38" fill="none" stroke="currentColor" strokeWidth="2" />
            <polyline
              points="22,40 34,54 58,28"
              stroke="currentColor"
              strokeWidth="5"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <p className="profile-campus">IIIT Kurnool</p>
        <h1 className="profile-title" style={{ marginTop: 10 }}>Registration complete</h1>

        {userInfo && (
          <div className="done-info">
            {userInfo.name && (
              <p className="done-info__row">
                <span className="done-info__label">Name</span>
                <span className="done-info__value">{userInfo.name}</span>
              </p>
            )}
            {userInfo.branch && (
              <p className="done-info__row">
                <span className="done-info__label">Branch</span>
                <span className="done-info__value">{userInfo.branch}</span>
              </p>
            )}
            <p className="done-info__row">
              <span className="done-info__label">Roll</span>
              <span className="done-info__value">{userInfo.roll}</span>
            </p>
          </div>
        )}

        <p className="profile-subtitle" style={{ marginTop: 16, maxWidth: 300 }}>
          Your photos and details have been saved.
        </p>

        <button
          type="button"
          className="profile-submit-btn"
          onClick={handleLogout}
          style={{ marginTop: 32 }}
        >
          Done
        </button>
      </main>
    </div>
  );
}
