import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { photosApi } from '../api/photos';
import { authApi } from '../api/auth';
import { ApiError } from '../api/client';
import { Alert } from '../components/Alert';
import { CameraView, CameraViewHandle } from '../components/CameraView';
import { useFaceLandmarker } from '../hooks/useFaceLandmarker';
import { checkPose, POSES } from '../config/poses';
import type { PoseConfig, PoseThresholds } from '../types';

type CaptureState = 'idle' | 'holding' | 'uploading' | 'accepted';

// Simple web audio synthesizer click/chime for Face ID feedback
function playAudioBeep(success = false) {
  try {
    const AudioContextClass =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) return;
    const ctx = new AudioContextClass();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (success) {
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12); // A5
      gain.gain.setValueAtTime(0.18, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
      osc.start();
      osc.stop(ctx.currentTime + 0.25);
    } else {
      osc.frequency.setValueAtTime(440, ctx.currentTime);
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);
      osc.start();
      osc.stop(ctx.currentTime + 0.08);
    }
  } catch {
    // Audio is optional enhancement
  }
}

// Live feedback helper
function getGuidance(
  facesDetected: number,
  faceRect: { x: number; y: number; w: number; h: number } | null,
  videoWidth: number,
  landmarkerStatus: string,
  pose: PoseConfig,
  yawRatio: number,
  pitchRatio: number,
  frontPitchRatio: number | null,
  thresholds: PoseThresholds | null
): { text: string; isGood: boolean; faceReady: boolean } {
  if (landmarkerStatus === 'loading') {
    return { text: 'Starting facial scanner…', isGood: false, faceReady: false };
  }
  if (!thresholds) {
    return { text: 'Loading pose settings…', isGood: false, faceReady: false };
  }

  if (facesDetected === 0) {
    return { text: 'Position your face in the circle', isGood: false, faceReady: false };
  }

  if (facesDetected > 1) {
    return { text: 'Only 1 person in frame please', isGood: false, faceReady: false };
  }

  if (faceRect && videoWidth > 0) {
    const faceW = faceRect.w;
    if (faceW / videoWidth < 0.16) {
      return { text: 'Move a little closer', isGood: false, faceReady: false };
    }
    if (faceW / videoWidth > 0.85) {
      return { text: 'Move back a little', isGood: false, faceReady: false };
    }
  }

  const poseError = checkPose(pose, yawRatio, pitchRatio, frontPitchRatio, thresholds);
  if (poseError) return { text: poseError, isGood: false, faceReady: true };

  return {
    text: 'Face found — hold still for automatic capture',
    isGood: true,
    faceReady: true,
  };
}

export default function CapturePage() {
  const navigate = useNavigate();
  const cameraRef = useRef<CameraViewHandle>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const [acceptedPoses, setAcceptedPoses] = useState<string[]>([]);
  const [currentPoseIndex, setCurrentPoseIndex] = useState(0);
  const [poseStatusReady, setPoseStatusReady] = useState(false);
  const [captureState, setCaptureState] = useState<CaptureState>('idle');
  const [serverFeedback, setServerFeedback] = useState('');
  const [cameraError, setCameraError] = useState('');
  const [cameraReady, setCameraReady] = useState(false);
  const [shutterFlash, setShutterFlash] = useState(false);
  const [holdProgress, setHoldProgress] = useState(0);
  const [showSkeleton, setShowSkeleton] = useState(true);
  const [frontPitchRatio, setFrontPitchRatio] = useState<number | null>(null);
  const [poseAttempts, setPoseAttempts] = useState(0);
  const [debugPoseEnabled, setDebugPoseEnabled] = useState(false);
  const [poseThresholds, setPoseThresholds] = useState<PoseThresholds | null>(null);

  const currentPose: PoseConfig = POSES[currentPoseIndex] ?? POSES[0];
  const holdStartTimeRef = useRef<number | null>(null);
  const animFrameRef = useRef<number>(0);
  const isCapturingRef = useRef(false);
  const retryAfterRef = useRef(0);

  const handleCameraReady = useCallback((el: HTMLVideoElement) => {
    videoRef.current = el;
    setCameraReady(true);
  }, []);

  const handleCameraError = useCallback((msg: string) => {
    setCameraError(msg);
  }, []);

  // Load status on mount
  useEffect(() => {
    let cancelled = false;
    authApi.me().catch(() => navigate('/login', { replace: true }));
    photosApi
      .getStatus()
      .then((status) => {
        if (cancelled) return;
        setAcceptedPoses(status.accepted_poses);
        setFrontPitchRatio(status.front_pitch_ratio);
        setPoseAttempts(status.pose_attempts);
        setPoseThresholds(status.pose_thresholds);
        setDebugPoseEnabled(status.debug_pose);
        setPoseStatusReady(true);
        if (status.completed) {
          navigate('/done', { replace: true });
          return;
        }
        const nextIdx = POSES.findIndex((p) => p.name === status.next_pose);
        if (nextIdx >= 0) setCurrentPoseIndex(nextIdx);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setServerFeedback(
          err instanceof ApiError
            ? err.message
            : 'Could not connect to photo server. Please refresh.'
        );
      });
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  // MediaPipe face detection
  const { status: landmarkerStatus, result: landmarkerResult } = useFaceLandmarker(
    videoRef,
    cameraReady && poseStatusReady && (captureState === 'idle' || captureState === 'holding')
  );
  const videoWidth = videoRef.current?.videoWidth ?? 640;
  const { text: guidanceText, isGood, faceReady } = getGuidance(
    landmarkerResult.facesDetected,
    landmarkerResult.faceRect,
    videoWidth,
    landmarkerStatus,
    currentPose,
    landmarkerResult.yawRatio,
    landmarkerResult.pitchRatio,
    frontPitchRatio,
    poseThresholds
  );

  // Trigger snapshot upload
  const doCapture = useCallback(async (submitAnyway = false) => {
    if (isCapturingRef.current) return;
    isCapturingRef.current = true;
    setCaptureState('uploading');
    setServerFeedback('');

    // Shutter flash effect & sound
    setShutterFlash(true);
    playAudioBeep(true);
    setTimeout(() => setShutterFlash(false), 250);

    try {
      const blob = await cameraRef.current!.captureFrame();
      const result = await photosApi.upload(blob, currentPose.name, submitAnyway);

      setAcceptedPoses((prev) =>
        prev.includes(currentPose.name) ? prev : [...prev, currentPose.name]
      );
      if (currentPose.name === 'PHOTO_1') {
        setFrontPitchRatio(landmarkerResult.pitchRatio);
      }
      setPoseAttempts(0);
      setCaptureState('accepted');
      setHoldProgress(1.0);

      setTimeout(() => {
        if (result.all_done) {
          navigate('/done', { replace: true });
        } else {
          const nextIdx = POSES.findIndex((p) => p.name === result.next_pose);
          if (nextIdx >= 0) {
            setCurrentPoseIndex(nextIdx);
          }
          setHoldProgress(0);
          setCaptureState('idle');
          isCapturingRef.current = false;
        }
      }, 750);
    } catch (err: unknown) {
      isCapturingRef.current = false;
      retryAfterRef.current = performance.now() + 1200;
      setCaptureState('idle');
      setHoldProgress(0);
      if (err instanceof ApiError) {
        if (err.code === 'WRONG_POSE') {
          const attempts = err.data.pose_attempts;
          if (typeof attempts === 'number') setPoseAttempts(attempts);
          setServerFeedback(err.message);
        } else {
          setServerFeedback(err.message);
        }
      } else {
        setServerFeedback(
          'Photo verification failed. Adjust your position; capture will retry automatically.'
        );
      }
    }
  }, [currentPose.name, landmarkerResult.pitchRatio, navigate]);

  // Smooth Apple Face ID auto-capture progress: holds for 600ms when face is in circle
  useEffect(() => {
    if (captureState !== 'idle' && captureState !== 'holding') {
      return;
    }

    const HOLD_DURATION_MS = 800;

    const updateHoldProgress = () => {
      if (!faceReady) {
        holdStartTimeRef.current = null;
        setHoldProgress(0);
        if (captureState === 'holding') setCaptureState('idle');
        animFrameRef.current = requestAnimationFrame(updateHoldProgress);
        return;
      }

      if (!isGood && poseAttempts >= 3) {
        holdStartTimeRef.current = null;
        setHoldProgress(0);
        animFrameRef.current = requestAnimationFrame(updateHoldProgress);
        return;
      }

      const now = performance.now();
      if (now < retryAfterRef.current || isCapturingRef.current) {
        holdStartTimeRef.current = null;
        setHoldProgress(0);
        animFrameRef.current = requestAnimationFrame(updateHoldProgress);
        return;
      }

      if (!holdStartTimeRef.current) {
        holdStartTimeRef.current = now;
        setCaptureState('holding');
      }

      const elapsed = now - holdStartTimeRef.current;
      const progress = Math.min(1.0, elapsed / HOLD_DURATION_MS);
      setHoldProgress(progress);

      if (progress >= 1.0 && !isCapturingRef.current) {
        void doCapture();
      } else {
        animFrameRef.current = requestAnimationFrame(updateHoldProgress);
      }
    };

    animFrameRef.current = requestAnimationFrame(updateHoldProgress);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [
    isGood,
    faceReady,
    landmarkerResult.facesDetected,
    landmarkerResult.pitchRatio,
    landmarkerResult.yawRatio,
    poseAttempts,
    captureState,
    doCapture,
  ]);

  return (
    <div className="faceid-screen">
      {/* Top Bar: Progress Indicator */}
      <header className="faceid-header">
        <div className="faceid-header__progress">
          {POSES.map((pose, i) => {
            const isDone = acceptedPoses.includes(pose.name) || i < currentPoseIndex;
            const isCurrent = i === currentPoseIndex;
            return (
              <div
                key={pose.name}
                className={`faceid-progress-bar ${isDone ? 'faceid-progress-bar--done' : ''} ${
                  isCurrent ? 'faceid-progress-bar--active' : ''
                }`}
              />
            );
          })}
        </div>
        <span className="faceid-header__step">Photo {currentPoseIndex + 1} of 4</span>
      </header>

      {/* Main Scanner Container */}
      <main className="faceid-main">
        {currentPoseIndex >= 1 && currentPoseIndex <= 2 && (
          <div className="faceid-angle-prompt" aria-live="polite">
            {currentPoseIndex === 1 ? 'Turn left' : 'Turn right'}
          </div>
        )}
        {cameraError ? (
          <div className="faceid-error-card">
            <p className="faceid-error-card__msg">{cameraError}</p>
            <p className="faceid-error-card__sub">
              Please grant camera permission in your browser and refresh.
            </p>
          </div>
        ) : (
          <div className="faceid-scanner-wrap">
            <CameraView
              ref={cameraRef}
              landmarks={showSkeleton ? landmarkerResult.landmarks : undefined}
              isGood={isGood}
              holdProgress={holdProgress}
              currentStepIndex={currentPoseIndex}
              shutterEffect={shutterFlash}
              showSkeleton={showSkeleton}
              onReady={handleCameraReady}
              onError={handleCameraError}
            />

            {/* Overlaid Processing / Verified Badge */}
            {captureState === 'uploading' && (
              <div className="faceid-pill faceid-pill--processing">
                <span className="faceid-spinner" />
                <span>Verifying photo…</span>
              </div>
            )}

            {captureState === 'accepted' && (
              <div className="faceid-pill faceid-pill--success">
                <span>✓ Verified</span>
              </div>
            )}
          </div>
        )}

        {/* Apple Face ID Typography Prompt */}
        <div className="faceid-prompt-block">
          <h1 className="faceid-title">
            Photo {currentPoseIndex + 1}: {currentPose.label}
          </h1>
          <p className="faceid-instruction">{currentPose.instruction}</p>
          <p className={`faceid-subtitle ${isGood ? 'faceid-subtitle--good' : ''}`}>
            {guidanceText}
          </p>
          {debugPoseEnabled && poseThresholds && landmarkerResult.facesDetected > 0 && (
            <p className="faceid-debug-pose">
              yaw_ratio: {(landmarkerResult.yawRatio * poseThresholds.yaw_sign).toFixed(3)}
            </p>
          )}
        </div>

        {/* Server rejection feedback if any */}
        {serverFeedback && (
          <div className="faceid-alert-wrap">
            <Alert type="error" message={serverFeedback} />
          </div>
        )}
        {poseAttempts >= 3 && (
          <button
            type="button"
            className="faceid-submit-anyway"
            onClick={() => void doCapture(true)}
            disabled={captureState === 'uploading' || captureState === 'accepted'}
          >
            Submit anyway
          </button>
        )}

        {/* Capture is automatic; retain only the optional overlay control. */}
        <div className="faceid-controls">
          <div className="faceid-footer-actions">
            <button
              type="button"
              className="faceid-toggle-btn"
              onClick={() => setShowSkeleton((v) => !v)}
              title="Toggle facial skeleton mesh"
            >
              Skeleton: {showSkeleton ? 'ON' : 'OFF'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
