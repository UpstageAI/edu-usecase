import './ProgressBar.css';

export function ProgressBar({ progress = 0, duration = 800 }) {
  return (
    <div className="progress-bar-container">
      <div 
        className="progress-bar-fill" 
        style={{ 
          width: `${progress}%`,
          transition: `width ${duration}ms ease-in-out`
        }}
      />
    </div>
  );
}

