import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

interface RouteStartNodeProps {
  data: {
    routeName: string;
  };
}

const RouteStartNode: React.FC<RouteStartNodeProps> = ({ data }) => {
  const { routeName } = data;

  // 출근/퇴근 구분
  const isCommute = routeName?.includes('출근');
  const color = isCommute ? '#3b82f6' : '#f97316';

  return (
    <div
      style={{
        background: 'transparent',
        borderRadius: 0,
        width: 200,
        height: 72,
        color: 'white',
        position: 'relative',
      }}
    >
      {/* Main rounded rectangle box */}
      <div
        style={{
          backgroundColor: `${color}30`,
          borderColor: color,
          borderWidth: '2px',
          backdropFilter: 'blur(10px)',
          boxShadow: `0 0 20px ${color}40, 0 4px 15px rgba(0, 0, 0, 0.3)`,
          minWidth: '120px',
          minHeight: '36px',
          padding: '8px 12px',
          borderRadius: '24px',
          border: `2px solid ${color}`,
        }}
      >
        <div style={{
          fontSize: '14px',
          fontWeight: '700',
          color: '#f8fafc',
          textAlign: 'center',
          whiteSpace: 'nowrap',
        }}>
          {routeName}
        </div>
      </div>

      {/* Small circle node */}
      <div
        style={{
          marginTop: '8px',
          width: '20px',
          height: '20px',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          backgroundColor: `${color}66`,
          boxShadow: `0 0 10px ${color}60`,
          margin: '8px auto 0',
        }}
      >
        <div
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: color,
          }}
        />

        <Handle
          type="source"
          position={Position.Bottom}
          style={{
            background: 'transparent',
            border: 'none',
            bottom: '50%',
            left: '50%',
            transform: 'translate(-50%, 50%)',
            width: '1px',
            height: '1px',
          }}
        />
      </div>
    </div>
  );
};

export default memo(RouteStartNode);
