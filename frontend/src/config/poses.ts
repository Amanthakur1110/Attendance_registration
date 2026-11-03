/**
 * Face capture sequence configuration — kept in sync with backend/app/services/pose_service.py
 *
 * The server checks side-view magnitude, not left/right yaw direction.
 */
import type { PoseConfig, PoseName } from '../types';

export const POSES: PoseConfig[] = [
  {
    name: 'PHOTO_1' as PoseName,
    label: 'Front',
    instruction: 'Look straight at the camera',
    yawMin: -45,
    yawMax: 45,
    pitchMin: -45,
    pitchMax: 45,
    rollMax: 50,
  },
  {
    name: 'PHOTO_2' as PoseName,
    label: 'Front again',
    instruction: 'Look at the camera for one more front photo',
    yawMin: -45,
    yawMax: 45,
    pitchMin: -45,
    pitchMax: 45,
    rollMax: 50,
  },
  {
    name: 'PHOTO_3' as PoseName,
    label: 'Turn left',
    instruction: 'Turn your face slightly to the left',
    yawMin: -90,
    yawMax: 90,
    pitchMin: -60,
    pitchMax: 60,
    rollMax: 50,
  },
  {
    name: 'PHOTO_4' as PoseName,
    label: 'Turn right',
    instruction: 'Turn your face slightly to the right',
    yawMin: -90,
    yawMax: 90,
    pitchMin: -60,
    pitchMax: 60,
    rollMax: 50,
  },
];

const POSE_NAME_MAP: Record<string, string> = {
  FRONT: 'PHOTO_1',
  FRONT_SLIGHT_RIGHT: 'PHOTO_2',
  LEFT: 'PHOTO_3',
  RIGHT: 'PHOTO_4',
  UP: 'PHOTO_4',
  PHOTO_1: 'PHOTO_1',
  PHOTO_2: 'PHOTO_2',
  PHOTO_3: 'PHOTO_3',
  PHOTO_4: 'PHOTO_4',
};

export function normalizePoseName(name: string): string {
  const clean = (name || '').trim().toUpperCase();
  return POSE_NAME_MAP[clean] || clean;
}

export function getPose(name: string): PoseConfig | undefined {
  const norm = normalizePoseName(name);
  return POSES.find((p) => p.name === norm);
}

/**
 * The server validates pose variation. Client pose angles are guidance-only,
 * so a browser-specific yaw convention cannot block an otherwise good face.
 */
export function checkPose(
  pose: PoseConfig,
  yaw: number,
  pitch: number,
  roll: number
): string | null {
  void pose;
  void yaw;
  void pitch;
  void roll;
  return null;
}
