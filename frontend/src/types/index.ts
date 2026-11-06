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
  front_pitch_ratio: number | null;
  pose_attempts: number;
  pose_thresholds: PoseThresholds;
  debug_pose: boolean;
}

export interface PoseThresholds {
  front_yaw_max: number;
  side_yaw_min: number;
  up_pitch_delta: number;
  up_yaw_max: number;
  yaw_sign: 1 | -1;
  side_face_confidence: number;
}

export interface PhotoUploadResult {
  photo_no: number;
  pose: string;
  confidence: number;
  pose_verified: boolean;
  pose_debug?: {
    yaw_ratio: number | null;
    pitch_ratio: number | null;
    thresholds: PoseThresholds;
  };
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
  yawRatio: number;
  pitchRatio: number;
  faceRect: { x: number; y: number; w: number; h: number } | null;
  landmarks?: { x: number; y: number; z: number }[];
}
