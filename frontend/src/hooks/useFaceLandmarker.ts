/**
 * useFaceLandmarker — loads MediaPipe FaceLandmarker and runs real-time inference.
 * Provides 3D landmark points for the face skeleton overlay and calibrated head pose angles.
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import type { FaceLandmarkResult } from '../types';

type LandmarkerState = 'loading' | 'ready' | 'error';

interface Point3D {
  x: number;
  y: number;
  z: number;
}

// Compute accurate yaw, pitch, roll using 3D landmark geometry and transformation matrix.
function computeHeadPose(
  matrix: number[] | undefined,
  landmarks: Point3D[]
): { yaw: number; pitch: number; roll: number } {
  const nose = landmarks[1] || landmarks[4];
  const rightCheek = landmarks[234];
  const leftCheek = landmarks[454];
  const forehead = landmarks[10];
  const chin = landmarks[152];
  const rightEye = landmarks[33];
  const leftEye = landmarks[263];

  let geomYaw = 0;
  let geomPitch = 0;
  let geomRoll = 0;

  if (nose && rightCheek && leftCheek) {
    const faceWidth = Math.max(0.001, leftCheek.x - rightCheek.x);
    const midX = (rightCheek.x + leftCheek.x) / 2;
    // When a person turns to their LEFT:
    // Nose shifts toward their left cheek (landmark 454, larger X in raw frame).
    // Asymmetry is positive.
    const asymmetry = (nose.x - midX) / (faceWidth * 0.5);
    const depthYaw = (leftCheek.z - rightCheek.z) / faceWidth;
    geomYaw = (asymmetry * 48) + (depthYaw * 32);
  }

  if (forehead && chin && nose) {
    const faceHeight = Math.max(0.001, chin.y - forehead.y);
    // Depth slope: when chin is tilted UP, chin is closer to camera (smaller Z) than forehead.
    const dz = (forehead.z - chin.z) / faceHeight;
    const noseRatio = (nose.y - forehead.y) / faceHeight;
    geomPitch = (dz * 75) + ((noseRatio - 0.60) * 45);
  }

  if (rightEye && leftEye) {
    geomRoll = Math.atan2(leftEye.y - rightEye.y, leftEye.x - rightEye.x) * (180 / Math.PI);
  }

  // If MediaPipe 4x4 transform matrix is available, compute matrix Euler angles
  let matYaw = geomYaw;
  let matPitch = geomPitch;
  let matRoll = geomRoll;

  if (matrix && matrix.length >= 16) {
    const r00 = matrix[0];
    const r10 = matrix[1];
    const r20 = matrix[2];
    const r21 = matrix[6];
    const r22 = matrix[10];
    const rad2deg = 180 / Math.PI;

    const mYaw = Math.asin(Math.max(-1, Math.min(1, -r20))) * rad2deg;
    const mPitch = Math.atan2(r21, r22) * rad2deg;
    const mRoll = Math.atan2(r10, r00) * rad2deg;

    matYaw = mYaw;
    matPitch = mPitch;
    matRoll = mRoll;
  }

  // Blend matrix and landmark geometry for maximum robustness
  const yaw = Number.isFinite(matYaw) ? (geomYaw * 0.55 + matYaw * 0.45) : geomYaw;
  const pitch = Number.isFinite(matPitch) ? (geomPitch * 0.55 + matPitch * 0.45) : geomPitch;
  const roll = Number.isFinite(matRoll) ? (geomRoll * 0.55 + matRoll * 0.45) : geomRoll;

  return { yaw, pitch, roll };
}

export function useFaceLandmarker(
  videoRef: React.RefObject<HTMLVideoElement | null>,
  enabled: boolean
) {
  const [status, setStatus] = useState<LandmarkerState>('loading');
  const [result, setResult] = useState<FaceLandmarkResult>({
    facesDetected: 0,
    yaw: 0,
    pitch: 0,
    roll: 0,
    faceRect: null,
    landmarks: undefined,
  });
  const landmarkerRef = useRef<unknown>(null);
  const rafRef = useRef<number>(0);
  const lastVideoTime = useRef<number>(-1);
  const smoothedAnglesRef = useRef<{ yaw: number; pitch: number; roll: number } | null>(null);
  const lastStateUpdateTime = useRef<number>(0);
  const lastFacesCount = useRef<number>(-1);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const vision = await import('@mediapipe/tasks-vision');
        const { FaceLandmarker, FilesetResolver } = vision;

        // Try local wasm first; fallback to jsdelivr CDN if local fails
        let filesetResolver;
        try {
          filesetResolver = await FilesetResolver.forVisionTasks('/mediapipe/wasm');
        } catch {
          filesetResolver = await FilesetResolver.forVisionTasks(
            'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.17/wasm'
          );
        }

        // Try local model task asset; fallback to Google Cloud Storage CDN
        let landmarker;
        try {
          landmarker = await FaceLandmarker.createFromOptions(filesetResolver, {
            baseOptions: {
              modelAssetPath: '/mediapipe/face_landmarker.task',
            },
            outputFaceBlendshapes: false,
            outputFacialTransformationMatrixes: true,
            runningMode: 'VIDEO',
            numFaces: 1,
            minFaceDetectionConfidence: 0.35,
            minFacePresenceConfidence: 0.35,
            minTrackingConfidence: 0.35,
          });
        } catch {
          landmarker = await FaceLandmarker.createFromOptions(filesetResolver, {
            baseOptions: {
              modelAssetPath:
                'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
            },
            outputFaceBlendshapes: false,
            outputFacialTransformationMatrixes: true,
            runningMode: 'VIDEO',
            numFaces: 1,
            minFaceDetectionConfidence: 0.35,
            minFacePresenceConfidence: 0.35,
            minTrackingConfidence: 0.35,
          });
        }

        if (!cancelled) {
          landmarkerRef.current = landmarker;
          setStatus('ready');
        }
      } catch (err) {
        console.error('FaceLandmarker load error:', err);
        if (!cancelled) setStatus('error');
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const runInference = useCallback(() => {
    const video = videoRef.current;
    const landmarker = landmarkerRef.current as {
      detectForVideo: (v: HTMLVideoElement, t: number) => {
        faceLandmarks: Point3D[][];
        facialTransformationMatrixes?: { data: number[] }[];
      };
    } | null;

    if (!enabled || !video || !landmarker || video.readyState < 2) {
      rafRef.current = requestAnimationFrame(runInference);
      return;
    }

    if (video.currentTime === lastVideoTime.current) {
      rafRef.current = requestAnimationFrame(runInference);
      return;
    }
    lastVideoTime.current = video.currentTime;

    try {
      const detections = landmarker.detectForVideo(video, performance.now());
      const count = detections.faceLandmarks?.length ?? 0;

      const now = performance.now();
      const shouldUpdate =
        count !== lastFacesCount.current || now - lastStateUpdateTime.current >= 45;

      if (count === 0) {
        smoothedAnglesRef.current = null;
        if (shouldUpdate) {
          lastStateUpdateTime.current = now;
          lastFacesCount.current = 0;
          setResult({
            facesDetected: 0,
            yaw: 0,
            pitch: 0,
            roll: 0,
            faceRect: null,
            landmarks: undefined,
          });
        }
      } else {
        const rawLandmarks = detections.faceLandmarks[0];
        const matrixData = detections.facialTransformationMatrixes?.[0]?.data;
        const angles = computeHeadPose(matrixData ? Array.from(matrixData) : undefined, rawLandmarks);

        let { yaw, pitch, roll } = angles;

        const previous = smoothedAnglesRef.current;
        if (previous) {
          const smoothing = 0.40;
          yaw = previous.yaw + smoothing * (yaw - previous.yaw);
          pitch = previous.pitch + smoothing * (pitch - previous.pitch);
          roll = previous.roll + smoothing * (roll - previous.roll);
        }
        smoothedAnglesRef.current = { yaw, pitch, roll };

        if (shouldUpdate) {
          lastStateUpdateTime.current = now;
          lastFacesCount.current = count;

          // Compute face bounding rect
          let minX = 1, maxX = 0, minY = 1, maxY = 0;
          for (const pt of rawLandmarks) {
            if (pt.x < minX) minX = pt.x;
            if (pt.x > maxX) maxX = pt.x;
            if (pt.y < minY) minY = pt.y;
            if (pt.y > maxY) maxY = pt.y;
          }

          setResult({
            facesDetected: count,
            yaw,
            pitch,
            roll,
            faceRect: {
              x: minX * video.videoWidth,
              y: minY * video.videoHeight,
              w: (maxX - minX) * video.videoWidth,
              h: (maxY - minY) * video.videoHeight,
            },
            landmarks: rawLandmarks,
          });
        }
      }
    } catch (err) {
      console.error('FaceLandmarker inference error:', err);
    }

    rafRef.current = requestAnimationFrame(runInference);
  }, [videoRef, enabled]);

  useEffect(() => {
    if (status === 'ready' && enabled) {
      rafRef.current = requestAnimationFrame(runInference);
    }
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [status, enabled, runInference]);

  return { status, result };
}
