import { client } from './client';
import type { PhotoStatus, PhotoUploadResult, PoseThresholds } from '../types';

export interface PhotoStatusResponse {
  ok: boolean;
  message: string;
  code: string;
  accepted_poses: string[];
  next_pose: string | null;
  photo_count: number;
  completed: boolean;
  poses: PhotoStatus['poses'];
  front_pitch_ratio: number | null;
  pose_attempts: number;
  pose_thresholds: PoseThresholds;
  debug_pose: boolean;
}

export interface UploadResponse {
  ok: boolean;
  message: string;
  code: string;
  photo: PhotoUploadResult;
  next_pose: string | null;
  all_done: boolean;
  pose_debug?: PhotoUploadResult['pose_debug'];
}

export const photosApi = {
  getStatus: () => client.get<PhotoStatusResponse>('/api/photos/status'),

  upload: (imageBlob: Blob, pose: string, submitAnyway = false) => {
    const form = new FormData();
    form.append('image', imageBlob, 'capture.jpg');
    form.append('pose', pose);
    if (submitAnyway) form.append('submit_anyway', 'true');
    return client.postForm<UploadResponse>('/api/photos/upload', form);
  },
};
