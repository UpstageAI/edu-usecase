import { Handle, type NodeProps, Position } from 'reactflow';
import React from 'react';

interface RouteStopNodeData {
  label: string;
  stopName: string;
  action: '승차' | '하차';
  count: number;
  departTime: string;
  busNo: string;
  category: string;
}

export const RouteStopNode: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeData = data as RouteStopNodeData;
  const { label, stopName, action, count, departTime } = nodeData;

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
            top: 0,
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: 'transparent',
            border: 'none',
          }}
        />

        {/* Bottom handle */}
        <Handle
          type="source"
          position={Position.Bottom}
          style={{
            bottom: 0,
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: 'transparent',
            border: 'none',
          }}
        />

        {/* Node Content */}
        <div style={{ padding: '0px 10px', height: '100%', display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '10px' }}>
          {/* Circle with icon (left side) */}
          <div style={{ flexShrink: 0 }}>
            <div
              style={{
                width: 24,
                height: 24,
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
                  fontSize: '11px',
                  fontWeight: '600',
                  color: actionColor,
                }}
              >
                {actionIcon}
              </span>
            </div>
          </div>

          {/* Content (right side) */}
          <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '1px' }}>
            {/* Action Tag */}
            <div style={{ flexShrink: 0 }}>
              <div
                style={{
                  padding: '1px 6px',
                  borderRadius: '10px',
                  border: `1px solid ${actionColor}`,
                  fontSize: '7px',
                  fontWeight: '700',
                  display: 'inline-block',
                  color: 'white',
                  backgroundColor: `${actionColor}30`,
                  boxShadow: `0 0 6px ${actionColor}40`,
                }}
              >
                {actionText}
              </div>
            </div>

            {/* Stop name */}
            <div style={{ flexShrink: 0 }}>
              <span style={{
                color: '#f8fafc',
                fontSize: '9px',
                fontWeight: '600',
                lineHeight: '1.1',
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
                fontSize: '8px',
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
