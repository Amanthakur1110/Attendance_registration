import { client } from './client';
import type { User } from '../types';

export interface SendOtpResponse {
  ok: boolean;
  message: string;
  code: string;
  email: string;
  cooldown: number;
}

export interface VerifyOtpResponse {
  ok: boolean;
  message: string;
  code: string;
  roll: string;
}

export interface MeResponse {
  ok: boolean;
  message: string;
  code: string;
  user: User;
}

export interface ProfileResponse {
  ok: boolean;
  message: string;
  code: string;
  user: User;
}

export const authApi = {
  sendOtp: (roll: string) =>
    client.post<SendOtpResponse>('/api/auth/send-otp', { roll }),

  verifyOtp: (roll: string, otp: string) =>
    client.post<VerifyOtpResponse>('/api/auth/verify-otp', { roll, otp }),

  saveProfile: (name: string, branch: string) =>
    client.post<ProfileResponse>('/api/auth/profile', { name, branch }),

  logout: () => client.post<{ ok: boolean }>('/api/auth/logout', {}),

  me: () => client.get<MeResponse>('/api/auth/me'),
};

