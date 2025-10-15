import { useState } from 'react';
import './Accordion.css';

export function Accordion({ items }) {
  const [openIndex, setOpenIndex] = useState(null);
  
  const toggleItem = (index) => {
    setOpenIndex(openIndex === index ? null : index);
  };
  
  return (
    <div className="accordion">
      {items.map((item, index) => (
        <div key={item.key} className="accordion-item">
          <button
            className="accordion-header"
            onClick={() => toggleItem(index)}
          >
            <div className="accordion-label">
              <span className="accordion-title">{item.label}</span>
              <span className="accordion-score">
                {item.score} / {item.max}
              </span>
            </div>
            <span className={`accordion-icon ${openIndex === index ? 'open' : ''}`}>
              ▼
            </span>
          </button>
          {openIndex === index && (
            <div className="accordion-body fade-in">
              <p className="accordion-rationale">{item.rationale}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

