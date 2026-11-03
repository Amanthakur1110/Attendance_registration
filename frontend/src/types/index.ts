// Shared TypeScript types

export interface ApiResponse<T = Record<string, unknown>> {
  ok: boolean;
  message: string;
  code: string;
  data?: T;
  [key: string]: unknown;
}

export interface User {
  roll: string;
  email: string;
  name: string | null;
  branch: string | null;
  photo_count: number;
  completed: boolean;
  created_at: string;
  completed_at: string | null;
}

export interface PoseInfo {
  name: string;
  label: string;
  instruction: string;
  accepted: boolean;
}

export interface PhotoStatus {
  accepted_poses: string[];
  next_pose: string | null;
  photo_count: number;
  completed: boolean;
  poses: PoseInfo[];
}

export interface PhotoUploadResult {
  photo_no: number;
  pose: string;
  confidence: number;
  yaw: number;
  pitch: number;
  roll_angle: number;
}

export type PoseName =
  | 'PHOTO_1'
  | 'PHOTO_2'
  | 'PHOTO_3'
  | 'PHOTO_4'
  | 'FRONT'
  | 'LEFT'
  | 'RIGHT'
  | 'UP';

export interface PoseConfig {
  name: PoseName;
  label: string;
  instruction: string;
  yawMin: number;
  yawMax: number;
  pitchMin: number;
  pitchMax: number;
  rollMax: number;
}

export type LiveFeedback =
  | 'NO_CAMERA'
  | 'NO_FACE'
  | 'MULTIPLE_FACES'
  | 'MOVE_CLOSER'
  | 'MOVE_BACK'
  | 'CENTER_FACE'
  | 'ADJUST_POSE'
  | 'GOOD'
  | 'LOADING';

export interface FaceLandmarkResult {
  facesDetected: number;
  yaw: number;
  pitch: number;
  roll: number;
  faceRect: { x: number; y: number; w: number; h: number } | null;
  landmarks?: { x: number; y: number; z: number }[];
}

