import './Banner.css';

export function Banner({ message, type = 'info', onClose }) {
  if (!message) return null;
  
  return (
    <div className={`banner banner-${type} slide-down`}>
      <span>{message}</span>
      {onClose && (
        <button className="banner-close" onClick={onClose}>
          ✕
        </button>
      )}
    </div>
  );
}

