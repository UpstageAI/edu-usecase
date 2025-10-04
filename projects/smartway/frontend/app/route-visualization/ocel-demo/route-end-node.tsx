import { Handle, Position } from 'reactflow';
import { memo } from 'react';

interface RouteEndNodeData {
  routeName: string;
}

export const RouteEndNode = memo(
  ({
    data,
    isConnectable,
  }: {
    data: RouteEndNodeData;
    isConnectable: boolean;
  }) => {
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
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        {/* Small circle node at top */}
        <div
          style={{
            width: '20px',
            height: '20px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            backgroundColor: `${color}66`,
            boxShadow: `0 0 10px ${color}60`,
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
            type="target"
            position={Position.Top}
            isConnectable={isConnectable}
            style={{
              background: 'transparent',
              border: 'none',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '1px',
              height: '1px',
            }}
          />
        </div>

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
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginTop: '8px',
          }}
        >
          <div style={{
            fontSize: '14px',
            fontWeight: '700',
            color: '#f8fafc',
            textAlign: 'center',
            whiteSpace: 'nowrap',
          }}>
            {routeName} 종료
          </div>
        </div>
      </div>
    );
  }
);

RouteEndNode.displayName = 'RouteEndNode';
