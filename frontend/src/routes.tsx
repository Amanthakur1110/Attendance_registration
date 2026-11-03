import { Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import OtpPage from './pages/OtpPage';
import ProfilePage from './pages/ProfilePage';
import CapturePage from './pages/CapturePage';
import DonePage from './pages/DonePage';

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/otp" element={<OtpPage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="/capture" element={<CapturePage />} />
      <Route path="/done" element={<DonePage />} />
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

