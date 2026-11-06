/**
 * Pose order and ratio checks kept in sync with backend/app/services/pose_service.py.
 */
import type { PoseConfig, PoseName, PoseThresholds } from '../types';

export const POSES: PoseConfig[] = [
  {
    name: 'PHOTO_1' as PoseName,
    label: 'Front',
    instruction: 'Look straight at the camera',
  },
  {
    name: 'PHOTO_2' as PoseName,
    label: 'Turn left',
    instruction: 'Turn a bit more to your LEFT',
  },
  {
    name: 'PHOTO_3' as PoseName,
    label: 'Turn right',
    instruction: 'Turn a bit more to your RIGHT',
  },
  {
    name: 'PHOTO_4' as PoseName,
    label: 'Look up',
    instruction: 'Tilt your chin up slightly',
  },
];

const POSE_NAME_MAP: Record<string, string> = {
  FRONT: 'PHOTO_1',
  FRONT_SLIGHT_RIGHT: 'PHOTO_1',
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
  return POSES.find((pose) => pose.name === norm);
}

export function checkPose(
  pose: PoseConfig,
  yawRatio: number,
  pitchRatio: number,
  frontPitchRatio: number | null,
  thresholds: PoseThresholds
): string | null {
  const signedYawRatio = yawRatio * thresholds.yaw_sign;

  if (pose.name === 'PHOTO_1' && Math.abs(signedYawRatio) > thresholds.front_yaw_max) {
    return 'Look straight at the camera.';
  }
  if (pose.name === 'PHOTO_2' && signedYawRatio < thresholds.side_yaw_min) {
    return 'Turn a bit more to your LEFT.';
  }
  if (pose.name === 'PHOTO_3' && signedYawRatio > -thresholds.side_yaw_min) {
    return 'Turn a bit more to your RIGHT.';
  }
  if (pose.name === 'PHOTO_4') {
    if (frontPitchRatio === null) {
      return 'Front photo reference is missing; please contact the supervisor.';
    }
    if (Math.abs(signedYawRatio) > thresholds.up_yaw_max) {
      return 'Face the camera more directly, then tilt your chin up.';
    }
    if (pitchRatio > frontPitchRatio - thresholds.up_pitch_delta) {
      return 'Tilt your chin up slightly.';
    }
  }
  return null;
}
