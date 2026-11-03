import { useRef, useEffect, forwardRef, useImperativeHandle } from 'react';

export interface CameraViewHandle {
  captureFrame(): Promise<Blob>;
}

interface Point3D {
  x: number;
  y: number;
  z: number;
}

interface CameraViewProps {
  landmarks?: Point3D[];
  isGood: boolean;
  holdProgress: number; // 0.0 to 1.0 within current step
  currentStepIndex: number; // 0, 1, 2, 3
  shutterEffect?: boolean;
  showSkeleton?: boolean;
  onReady?: (video: HTMLVideoElement) => void;
  onError?: (msg: string) => void;
}

// MediaPipe 478 face mesh contour indices
const CONTOUR_JAW = [
  10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
  397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
  172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 10,
];
const RIGHT_EYEBROW = [70, 63, 105, 66, 107];
const LEFT_EYEBROW = [336, 296, 334, 293, 300];
const RIGHT_EYE = [33, 160, 158, 133, 153, 144, 33];
const LEFT_EYE = [263, 387, 385, 362, 380, 373, 263];
const NOSE_BRIDGE = [168, 6, 197, 195, 5, 4, 1];
const LIPS_OUTER = [
  61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61,
];

// Total radial tick lines around the circle (like Apple Face ID in user's image)
const TOTAL_TICKS = 64;
const VIEWPORT_SIZE = 400; // viewBox 0 0 400 400
const CENTER = 200;
const INNER_RADIUS = 138;
const OUTER_RADIUS = 160;

// Precompute radial tick lines
const TICKS = Array.from({ length: TOTAL_TICKS }, (_, i) => {
  // Start from top (angle = -90 deg) and go clockwise
  const angle = (i / TOTAL_TICKS) * 2 * Math.PI - Math.PI / 2;
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  return {
    index: i,
    x1: CENTER + INNER_RADIUS * cos,
    y1: CENTER + INNER_RADIUS * sin,
    x2: CENTER + OUTER_RADIUS * cos,
    y2: CENTER + OUTER_RADIUS * sin,
  };
});

export const CameraView = forwardRef<CameraViewHandle, CameraViewProps>(
  function CameraView(
    {
      landmarks,
      isGood,
      holdProgress,
      currentStepIndex,
      shutterEffect,
      showSkeleton = true,
      onReady,
      onError,
    },
    ref
  ) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const streamRef = useRef<MediaStream | null>(null);

    // Keep stable references to callbacks so effect doesn't re-run
    const onReadyRef = useRef(onReady);
    onReadyRef.current = onReady;
    const onErrorRef = useRef(onError);
    onErrorRef.current = onError;

    // Expose captureFrame to parent via ref
    useImperativeHandle(ref, () => ({
      async captureFrame(): Promise<Blob> {
        const video = videoRef.current;
        if (!video) throw new Error('Camera not initialized');

        // Wait if video hasn't loaded first frame yet
        if (video.videoWidth === 0 || video.readyState < 2) {
          await new Promise((resolve) => setTimeout(resolve, 150));
        }

        const vw = video.videoWidth || 640;
        const vh = video.videoHeight || 480;

        const canvas = document.createElement('canvas');
        canvas.width = vw;
        canvas.height = vh;
        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('Canvas context unavailable');

        // Draw the raw camera frame
        ctx.drawImage(video, 0, 0, vw, vh);

        // Check center region brightness and boost if dark
        try {
          const sampleW = Math.min(vw, 160);
          const sampleH = Math.min(vh, 160);
          const startX = Math.floor((vw - sampleW) / 2);
          const startY = Math.floor((vh - sampleH) / 2);
          const imgData = ctx.getImageData(startX, startY, sampleW, sampleH);
          let lumSum = 0;
          const totalPixels = sampleW * sampleH;
          for (let i = 0; i < imgData.data.length; i += 4) {
            lumSum +=
              imgData.data[i] * 0.299 +
              imgData.data[i + 1] * 0.587 +
              imgData.data[i + 2] * 0.114;
          }
          const avgLum = lumSum / totalPixels;

          // If frame is dark (< 60), apply auto-gain to illuminate face clearly
          if (avgLum < 60 && avgLum > 5) {
            const boost = Math.min(1.45, 75 / Math.max(avgLum, 20));
            const fullImgData = ctx.getImageData(0, 0, vw, vh);
            const d = fullImgData.data;
            for (let i = 0; i < d.length; i += 4) {
              d[i] = Math.min(255, d[i] * boost);
              d[i + 1] = Math.min(255, d[i + 1] * boost);
              d[i + 2] = Math.min(255, d[i + 2] * boost);
            }
            ctx.putImageData(fullImgData, 0, 0);
          }
        } catch {
          // Fall back to original frame
        }

        return new Promise<Blob>((resolve, reject) => {
          canvas.toBlob(
            (blob) => (blob ? resolve(blob) : reject(new Error('Capture failed'))),
            'image/jpeg',
            0.94
          );
        });
      },
    }));

    // Start webcam once on mount - empty dependency array ensures NO camera stop/restart loops
    useEffect(() => {
      let cancelled = false;

      async function start() {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: {
              width: { ideal: 1280, min: 640 },
              height: { ideal: 720, min: 480 },
              facingMode: 'user',
            },
            audio: false,
          });

          if (cancelled) {
            stream.getTracks().forEach((t) => t.stop());
            return;
          }

          streamRef.current = stream;
          const video = videoRef.current;

          if (video) {
            video.srcObject = stream;
            video.muted = true;
            video.defaultMuted = true;
            video.setAttribute('playsinline', 'true');
            video.setAttribute('autoplay', 'true');

            // Force play and notify parent
            video
              .play()
              .then(() => {
                if (!cancelled) onReadyRef.current?.(video);
              })
              .catch((err) => {
                console.warn('Video play deferred:', err);
              });

            video.onloadedmetadata = () => {
              if (cancelled) return;
              video.play().catch(() => {});
              onReadyRef.current?.(video);
            };

            video.onplaying = () => {
              if (!cancelled) onReadyRef.current?.(video);
            };
          }
        } catch (err: unknown) {
          if (cancelled) return;
          let msg = 'Camera access failed.';
          if (err instanceof DOMException) {
            if (err.name === 'NotAllowedError') {
              msg = 'Camera permission denied. Please click the lock icon in the address bar to allow camera access and refresh.';
            } else if (err.name === 'NotFoundError') {
              msg = 'No camera found. Please connect a webcam and refresh.';
            } else if (err.name === 'NotReadableError') {
              msg = 'Camera is in use by another app. Please close other camera apps and refresh.';
            }
          }
          onErrorRef.current?.(msg);
        }
      }

      void start();

      return () => {
        cancelled = true;
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }
      };
    }, []);

    // Draw the facial skeleton & 3D curved horizon line on the canvas
    useEffect(() => {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      if (!canvas || !video) return;

      const w = video.videoWidth || 640;
      const h = video.videoHeight || 480;
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }

      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.clearRect(0, 0, w, h);

      if (!landmarks || landmarks.length === 0) return;

      const context = ctx;

      // 1. Draw the 3D Face ID Horizon Arc Line across the face (as seen in user's image)
      const nose = landmarks[1];
      const leftCheek = landmarks[454];
      const rightCheek = landmarks[234];
      if (nose && leftCheek && rightCheek) {
        context.save();
        context.beginPath();
        const startX = rightCheek.x * w;
        const startY = rightCheek.y * h;
        const endX = leftCheek.x * w;
        const endY = leftCheek.y * h;
        const ctrlX = nose.x * w;
        const ctrlY = nose.y * h - h * 0.04;

        context.moveTo(startX, startY);
        context.quadraticCurveTo(ctrlX, ctrlY, endX, endY);
        context.strokeStyle = isGood ? 'rgba(52, 199, 89, 0.90)' : 'rgba(56, 189, 248, 0.80)';
        context.lineWidth = Math.max(2.2, w * 0.0035);
        context.shadowColor = isGood ? 'rgba(52, 199, 89, 0.75)' : 'rgba(56, 189, 248, 0.65)';
        context.shadowBlur = 8;
        context.stroke();
        context.restore();
      }

      if (!showSkeleton) return;

      // 2. Draw subtle facial skeleton contours
      context.save();
      const strokeColor = isGood ? 'rgba(52, 199, 89, 0.65)' : 'rgba(56, 189, 248, 0.55)';
      const dotColor = isGood ? '#34c759' : '#38bdf8';

      context.lineWidth = Math.max(1.5, w * 0.0022);
      context.strokeStyle = strokeColor;
      context.shadowColor = strokeColor;
      context.shadowBlur = 6;
      context.lineCap = 'round';
      context.lineJoin = 'round';

      function drawPath(indices: number[], close = false) {
        if (!context || !landmarks) return;
        context.beginPath();
        let first = true;
        for (const idx of indices) {
          const pt = landmarks[idx];
          if (!pt) continue;
          const x = pt.x * w;
          const y = pt.y * h;
          if (first) {
            context.moveTo(x, y);
            first = false;
          } else {
            context.lineTo(x, y);
          }
        }
        if (close) context.closePath();
        context.stroke();
      }

      drawPath(CONTOUR_JAW, true);
      drawPath(RIGHT_EYEBROW);
      drawPath(LEFT_EYEBROW);
      drawPath(RIGHT_EYE, true);
      drawPath(LEFT_EYE, true);
      drawPath(NOSE_BRIDGE);
      drawPath(LIPS_OUTER, true);

      // 3. Glowing landmark anchor dots
      const KEY_DOTS = [1, 10, 152, 33, 263, 61, 291, 234, 454];
      context.fillStyle = dotColor;
      for (const idx of KEY_DOTS) {
        const pt = landmarks[idx];
        if (!pt) continue;
        context.beginPath();
        const r = idx === 1 ? Math.max(3.2, w * 0.005) : Math.max(2.0, w * 0.003);
        context.arc(pt.x * w, pt.y * h, r, 0, Math.PI * 2);
        context.fill();
      }

      context.restore();
    }, [landmarks, isGood, showSkeleton]);

    // Calculate how many of the 64 radial ticks should be lit up green
    // 4 steps in total: each step accounts for 16 ticks (1/4 of circle).
    const completedTicksBase = currentStepIndex * (TOTAL_TICKS / 4);
    const inProgressTicks = Math.round(holdProgress * (TOTAL_TICKS / 4));
    const activeTicksCount = Math.min(TOTAL_TICKS, completedTicksBase + inProgressTicks);

    return (
      <div className="faceid-container">
        {/* Shutter Camera Flash Effect */}
        {shutterEffect && <div className="faceid-flash" />}

        {/* Circular Camera Viewport */}
        <div className="faceid-viewport">
          <div className="faceid-viewport__stream">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="faceid-viewport__video"
              aria-label="Live camera feed"
            />
            <canvas
              ref={canvasRef}
              className="faceid-viewport__canvas"
              aria-hidden="true"
            />
          </div>
        </div>

        {/* Apple Face ID Radial Ticks Ring (matches attached image) */}
        <svg
          className="faceid-ticks-overlay"
          viewBox={`0 0 ${VIEWPORT_SIZE} ${VIEWPORT_SIZE}`}
          aria-hidden="true"
        >
          {TICKS.map((tick) => {
            const isCompleted = tick.index < activeTicksCount;
            return (
              <line
                key={tick.index}
                x1={tick.x1}
                y1={tick.y1}
                x2={tick.x2}
                y2={tick.y2}
                stroke={isCompleted ? '#34c759' : 'rgba(255, 255, 255, 0.22)'}
                strokeWidth={isCompleted ? 3.5 : 2.5}
                strokeLinecap="round"
                style={{
                  transition: 'stroke 0.12s ease, stroke-width 0.12s ease',
                  filter: isCompleted ? 'drop-shadow(0 0 3px rgba(52, 199, 89, 0.7))' : 'none',
                }}
              />
            );
          })}
        </svg>
      </div>
    );
  }
);
