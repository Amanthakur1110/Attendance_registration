import { useEffect, useRef, useState } from 'react';

export interface CameraState {
  stream: MediaStream | null;
  error: string | null;
  isReady: boolean;
}

export function useCamera(videoRef: React.RefObject<HTMLVideoElement | null>) {
  const [state, setState] = useState<CameraState>({
    stream: null,
    error: null,
    isReady: false,
  });
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: 'user',
          },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setState({ stream, error: null, isReady: true });
      } catch (err: unknown) {
        if (cancelled) return;
        let message = 'Camera access failed.';
        if (err instanceof DOMException) {
          if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            message =
              'Camera permission denied. Please allow camera access in your browser settings and refresh.';
          } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
            message = 'No camera found. Please connect a camera and refresh.';
          } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
            message = 'Camera is in use by another application. Please close it and refresh.';
          }
        }
        setState({ stream: null, error: message, isReady: false });
      }
    }

    startCamera();

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, [videoRef]);

  async function captureFrameAsync(videoEl: HTMLVideoElement): Promise<Blob> {
    const canvas = document.createElement('canvas');
    canvas.width = videoEl.videoWidth;
    canvas.height = videoEl.videoHeight;
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(videoEl, 0, 0);
    return new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob);
          else reject(new Error('Canvas toBlob failed'));
        },
        'image/jpeg',
        0.92
      );
    });
  }

  return { ...state, captureFrameAsync };
}

