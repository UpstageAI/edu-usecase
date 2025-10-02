import './Skeleton.css';

export function Skeleton({ type = 'text', width, height, count = 1 }) {
  if (type === 'text') {
    return (
      <div className="skeleton-group">
        {Array.from({ length: count }).map((_, i) => (
          <div 
            key={i} 
            className="skeleton skeleton-text" 
            style={{ width }}
          />
        ))}
      </div>
    );
  }
  
  if (type === 'box') {
    return (
      <div 
        className="skeleton skeleton-box" 
        style={{ width, height }}
      />
    );
  }
  
  if (type === 'row') {
    return (
      <div className="skeleton-group">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="skeleton skeleton-row" />
        ))}
      </div>
    );
  }
  
  return null;
}

