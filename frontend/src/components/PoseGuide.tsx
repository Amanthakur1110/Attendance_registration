import type { ReactNode } from 'react';
import type { PoseConfig } from '../types';

interface PoseGuideProps {
  pose: PoseConfig;
  feedback: string;
  isGood: boolean;
}

const POSE_ICONS: Record<string, ReactNode> = {
  FRONT: (
    <svg viewBox="0 0 80 80" className="pose-icon" aria-hidden="true">
      {/* Head */}
      <ellipse cx="40" cy="35" rx="18" ry="22" fill="none" stroke="currentColor" strokeWidth="3" />
      {/* Eyes */}
      <circle cx="32" cy="31" r="3" fill="currentColor" />
      <circle cx="48" cy="31" r="3" fill="currentColor" />
      {/* Nose */}
      <path d="M40 35 L37 43 L43 43" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      {/* Neck */}
      <line x1="35" y1="57" x2="35" y2="65" stroke="currentColor" strokeWidth="3" />
      <line x1="45" y1="57" x2="45" y2="65" stroke="currentColor" strokeWidth="3" />
    </svg>
  ),
  LEFT: (
    <svg viewBox="0 0 80 80" className="pose-icon pose-icon--animated-left" aria-hidden="true">
      <ellipse cx="44" cy="35" rx="16" ry="22" fill="none" stroke="currentColor" strokeWidth="3" />
      <circle cx="38" cy="31" r="3" fill="currentColor" />
      <circle cx="50" cy="31" r="3" fill="currentColor" />
      <path d="M44 35 L41 43 L47 43" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      {/* Arrow pointing left */}
      <path d="M28 35 L16 35 M16 35 L22 29 M16 35 L22 41" stroke="#b6f36a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  RIGHT: (
    <svg viewBox="0 0 80 80" className="pose-icon pose-icon--animated-right" aria-hidden="true">
      <ellipse cx="36" cy="35" rx="16" ry="22" fill="none" stroke="currentColor" strokeWidth="3" />
      <circle cx="30" cy="31" r="3" fill="currentColor" />
      <circle cx="42" cy="31" r="3" fill="currentColor" />
      <path d="M36 35 L33 43 L39 43" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      {/* Arrow pointing right */}
      <path d="M52 35 L64 35 M64 35 L58 29 M64 35 L58 41" stroke="#b6f36a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  UP: (
    <svg viewBox="0 0 80 80" className="pose-icon pose-icon--animated-up" aria-hidden="true">
      <ellipse cx="40" cy="38" rx="18" ry="20" fill="none" stroke="currentColor" strokeWidth="3" />
      <circle cx="32" cy="34" r="3" fill="currentColor" />
      <circle cx="48" cy="34" r="3" fill="currentColor" />
      {/* Arrow pointing up */}
      <path d="M40 18 L40 6 M40 6 L34 12 M40 6 L46 12" stroke="#b6f36a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
};

export function PoseGuide({ pose, feedback, isGood }: PoseGuideProps) {
  return (
    <div className={`pose-guide ${isGood ? 'pose-guide--good' : ''}`}>
      <div className="pose-guide__icon">
        {POSE_ICONS[pose.name] ?? POSE_ICONS['FRONT']}
      </div>
      <div className="pose-guide__text">
        <p className="pose-guide__instruction">{pose.instruction}</p>
        {feedback && (
          <p className={`pose-guide__feedback ${isGood ? 'pose-guide__feedback--good' : 'pose-guide__feedback--hint'}`}>
            {feedback}
          </p>
        )}
      </div>
    </div>
  );
}
