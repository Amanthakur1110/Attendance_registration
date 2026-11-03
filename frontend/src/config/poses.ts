/**
 * Face capture sequence configuration — kept in sync with backend/app/services/pose_service.py
 *
 * 4 progressive face photo captures (Photo 1 to 4) replicating Apple Face ID enrollment.
 * Focuses on natural face presence, valid centering, and effortless auto-capture.
 */
import type { PoseConfig, PoseName } from '../types';

export const POSES: PoseConfig[] = [
  {
    name: 'PHOTO_1' as PoseName,
    label: 'Photo 1',
    instruction: 'Center your face inside the circle',
    yawMin: -90,
    yawMax: 90,
    pitchMin: -90,
    pitchMax: 90,
    rollMax: 35,
  },
  {
    name: 'PHOTO_2' as PoseName,
    label: 'Photo 2',
    instruction: 'Move your head slowly to complete the circle',
    yawMin: -90,
    yawMax: 90,
    pitchMin: -90,
    pitchMax: 90,
    rollMax: 35,
  },
  {
    name: 'PHOTO_3' as PoseName,
    label: 'Photo 3',
    instruction: 'Move your head slowly to complete the circle',
    yawMin: -90,
    yawMax: 90,
    pitchMin: -90,
    pitchMax: 90,
    rollMax: 35,
  },
  {
    name: 'PHOTO_4' as PoseName,
    label: 'Photo 4',
    instruction: 'Move your head slowly to complete the circle',
    yawMin: -90,
    yawMax: 90,
    pitchMin: -90,
    pitchMax: 90,
    rollMax: 35,
  },
];

const POSE_NAME_MAP: Record<string, string> = {
  FRONT: 'PHOTO_1',
  LEFT: 'PHOTO_2',
  RIGHT: 'PHOTO_3',
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
 * Validates natural face upright posture (roll <= 35 deg).
 * Returns null if good, or a helpful hint if tilted too far sideways.
 */
export function checkPose(
  pose: PoseConfig,
  _yaw: number,
  _pitch: number,
  roll: number
): string | null {
  if (Math.abs(roll) > pose.rollMax) {
    return roll > 0 ? 'Keep your head upright (leaning right)' : 'Keep your head upright (leaning left)';
  }
  return null;
}
