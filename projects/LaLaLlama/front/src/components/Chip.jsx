import './Chip.css';

export function Chip({ label, status = 'default' }) {
  return (
    <span className={`chip chip-${status}`}>
      {label}
    </span>
  );
}

