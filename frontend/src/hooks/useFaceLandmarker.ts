/**
 * useFaceLandmarker — loads MediaPipe FaceLandmarker and runs real-time inference.
 * Provides face mesh points and keypoint ratios for the pose checks.
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import type { FaceLandmarkResult } from '../types';

type LandmarkerState = 'loading' | 'ready' | 'error';

interface Point3D {
  x: number;
  y: number;
  z: number;
}

function computePoseRatios(landmarks: Point3D[]): { yawRatio: number; pitchRatio: number } {
  const nose = landmarks[1];
  const leftEye = landmarks[33];
  const rightEye = landmarks[263];
  const leftMouth = landmarks[61];
  const rightMouth = landmarks[291];
  const eyeMidX = (leftEye.x + rightEye.x) / 2;
  const eyeMidY = (leftEye.y + rightEye.y) / 2;
  const interEyeDistance = Math.hypot(rightEye.x - leftEye.x, rightEye.y - leftEye.y);
  const mouthMidY = (leftMouth.y + rightMouth.y) / 2;
  const verticalEyeMouthDistance = mouthMidY - eyeMidY;

  if (interEyeDistance < 1e-6 || Math.abs(verticalEyeMouthDistance) < 1e-6) {
    return { yawRatio: 0, pitchRatio: 0 };
  }
  return {
    yawRatio: (nose.x - eyeMidX) / interEyeDistance,
    pitchRatio: (nose.y - eyeMidY) / verticalEyeMouthDistance,
  };
}

export function useFaceLandmarker(
  videoRef: React.RefObject<HTMLVideoElement | null>,
  enabled: boolean
) {
  const [status, setStatus] = useState<LandmarkerState>('loading');
  const [result, setResult] = useState<FaceLandmarkResult>({
    facesDetected: 0,
    yawRatio: 0,
    pitchRatio: 0,
    faceRect: null,
    landmarks: undefined,
  });
  const landmarkerRef = useRef<unknown>(null);
  const rafRef = useRef<number>(0);
  const lastVideoTime = useRef<number>(-1);
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
            outputFacialTransformationMatrixes: false,
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
            outputFacialTransformationMatrixes: false,
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
        if (shouldUpdate) {
          lastStateUpdateTime.current = now;
          lastFacesCount.current = 0;
          setResult({
            facesDetected: 0,
            yawRatio: 0,
            pitchRatio: 0,
            faceRect: null,
            landmarks: undefined,
          });
        }
      } else {
        const rawLandmarks = detections.faceLandmarks[0];
        const ratios = computePoseRatios(rawLandmarks);

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
            yawRatio: ratios.yawRatio,
            pitchRatio: ratios.pitchRatio,
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
