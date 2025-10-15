import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { StopNodeData } from '../types/route.types';

interface CustomNodeProps {
  data: StopNodeData;
  selected?: boolean;
}

const CustomNode: React.FC<CustomNodeProps> = ({ data, selected }) => {
  const { label, stopName, action, count, departTime } = data;

  const actionIcon = action === '승차' ? '↑' : '↓';
  const actionText = action === '승차' ? `+${count}명` : `-${count}명`;
  const isBoarding = action === '승차';
  const actionColor = isBoarding ? '#3b82f6' : '#ef4444';

  return (
    <div
      style={{
        position: 'relative',
        backgroundColor: 'transparent',
        borderRadius: 0,
        cursor: 'pointer',
        width: 240,
        height: 56,
      }}
    >
      <div
        style={{
          backgroundColor: '#1e293b',
          borderRadius: '8px',
          width: '100%',
          height: '100%',
          border: selected ? '2px solid #3b82f6' : '1px solid transparent',
          boxShadow: selected ? '0 0 0 2px #3b82f640, 0 0 18px #3b82f633' : 'none',
          transition: 'all 0.2s',
        }}
      >
        {/* Top handle */}
        <Handle
          type="target"
          position={Position.Top}
          style={{
            top: -20,
            width: 16,
            height: 16,
            borderRadius: '50%',
            backgroundColor: 'white',
            border: `3px solid ${actionColor}`,
            visibility: 'hidden',
          }}
        />

        {/* Bottom handle */}
        <Handle
          type="source"
          position={Position.Bottom}
          style={{
            bottom: -20,
            width: 16,
            height: 16,
            borderRadius: '50%',
            backgroundColor: 'white',
            border: `3px solid ${actionColor}`,
          }}
        />

        {/* Node Content */}
        <div style={{ padding: '8px 12px', height: '100%', display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '12px' }}>
        {/* Circle with icon (left side) */}
        <div style={{ flexShrink: 0 }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              backgroundColor: `${actionColor}20`,
            }}
          >
            <span
              style={{
                fontSize: '12px',
                fontWeight: '600',
                color: actionColor,
              }}
            >
              {actionIcon}
            </span>
          </div>
        </div>

        {/* Content (right side) */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {/* Action Tag */}
          <div style={{ flexShrink: 0 }}>
            <div
              style={{
                padding: '2px 8px',
                borderRadius: '12px',
                border: `1px solid ${actionColor}`,
                fontSize: '7px',
                fontWeight: '700',
                display: 'inline-block',
                color: 'white',
                backgroundColor: `${actionColor}30`,
                boxShadow: `0 0 8px ${actionColor}40`,
              }}
            >
              {actionText}
            </div>
          </div>

          {/* Stop name */}
          <div style={{ flexShrink: 0 }}>
            <span style={{
              color: '#f8fafc',
              fontSize: '10px',
              fontWeight: '600',
              lineHeight: '1.2',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              display: 'block',
            }}>
              {stopName}
            </span>
          </div>

          {/* Metrics - time */}
          <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
            <div style={{
              color: '#94a3b8',
              fontSize: '9px',
              fontWeight: '500',
            }}>
              {departTime}
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
};

export default memo(CustomNode);
