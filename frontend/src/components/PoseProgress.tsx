import { POSES } from '../config/poses';

interface PoseProgressProps {
  acceptedPoses: string[];
  currentPose: string | null;
  thumbnails?: Record<string, string>; // pose name -> data URL
}

export function PoseProgress({ acceptedPoses, currentPose, thumbnails = {} }: PoseProgressProps) {
  return (
    <div className="pose-progress" role="list" aria-label="Photo progress">
      {POSES.map((pose, i) => {
        const accepted = acceptedPoses.includes(pose.name);
        const current = pose.name === currentPose;
        let stateClass = 'pose-progress__step';
        if (accepted) stateClass += ' pose-progress__step--done';
        else if (current) stateClass += ' pose-progress__step--current';
        else stateClass += ' pose-progress__step--pending';

        return (
          <div key={pose.name} className={stateClass} role="listitem" aria-label={`${pose.label}: ${accepted ? 'done' : current ? 'in progress' : 'pending'}`}>
            <div className="pose-progress__dot">
              {accepted ? (
                thumbnails[pose.name] ? (
                  <img src={thumbnails[pose.name]} alt={`${pose.label} thumbnail`} className="pose-progress__thumb" />
                ) : (
                  <span className="pose-progress__check" aria-hidden="true">✓</span>
                )
              ) : (
                <span className="pose-progress__number" aria-hidden="true">{i + 1}</span>
              )}
            </div>
            <span className="pose-progress__label">{pose.label}</span>
          </div>
        );
      })}
    </div>
  );
}

