import { useEffect, useRef, useState } from 'react';

/**
 * Countdown from `initialSeconds` to 0.
 * Pauses when `paused` is true (e.g. tab hidden).
 * Resets when `key` changes.
 */
export function useCountdown(initialSeconds: number, paused: boolean, key: unknown) {
  const [seconds, setSeconds] = useState(initialSeconds);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setSeconds(initialSeconds);
  }, [key, initialSeconds]);

  useEffect(() => {
    if (paused) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    if (seconds <= 0) return;

    intervalRef.current = setInterval(() => {
      setSeconds((s) => Math.max(0, s - 1));
    }, 1000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [paused, seconds]);

  const reset = () => setSeconds(initialSeconds);

  return { seconds, reset };
}

