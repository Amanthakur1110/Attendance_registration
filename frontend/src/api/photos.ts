import { client } from './client';
import type { PhotoStatus, PhotoUploadResult } from '../types';

export interface PhotoStatusResponse {
  ok: boolean;
  message: string;
  code: string;
  accepted_poses: string[];
  next_pose: string | null;
  photo_count: number;
  completed: boolean;
  poses: PhotoStatus['poses'];
}

export interface UploadResponse {
  ok: boolean;
  message: string;
  code: string;
  photo: PhotoUploadResult;
  next_pose: string | null;
  all_done: boolean;
}

export const photosApi = {
  getStatus: () => client.get<PhotoStatusResponse>('/api/photos/status'),

  upload: (imageBlob: Blob, pose: string) => {
    const form = new FormData();
    form.append('image', imageBlob, 'capture.jpg');
    form.append('pose', pose);
    return client.postForm<UploadResponse>('/api/photos/upload', form);
  },
};

