import React from 'react';
import { BaseEdge, EdgeLabelRenderer, EdgeProps, getBezierPath } from 'reactflow';

interface RouteEdgeData {
  currentPassengers: number;
  isStartEdge?: boolean;
}

export const RouteEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}) => {
  const edgeData = data as RouteEdgeData;
  const { currentPassengers, isStartEdge } = edgeData;

  // Calculate path for the edge
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: 0.2,
  });

  // Edge styling
  const baseColor = '#94a3b8';
  const strokeWidth = isStartEdge ? 2 : Math.max(3, 2 + (currentPassengers / 20) * 4);
  const strokeDasharray = isStartEdge ? '5,5' : selected ? '5,5' : 'none';

  // Create unique marker ID for this edge
  const markerId = `arrowhead-${id}`;

  return (
    <>
      {/* Define arrow marker */}
      <svg style={{ position: 'absolute', width: 0, height: 0 }}>
        <defs>
          <marker
            id={markerId}
            viewBox="0 0 10 10"
            refY="5"
            markerWidth="15"
            markerHeight="15"
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={baseColor} />
          </marker>
        </defs>
      </svg>

      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={`url(#${markerId})`}
        style={{
          stroke: baseColor,
          strokeWidth,
          strokeOpacity: 1,
          strokeDasharray,
          filter: selected ? `drop-shadow(0 0 6px ${baseColor}77)` : undefined,
        }}
      />

      {/* Edge label - only show for non-start edges */}
      {!isStartEdge && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'none',
              backgroundColor: `${baseColor}B0`,
              borderColor: baseColor,
              borderWidth: '1px',
              height: '20px',
              borderRadius: '999px',
              padding: '0 8px',
              boxShadow: `0 2px 12px rgba(0, 0, 0, 0.5), 0 0 8px ${baseColor}60`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: `1px solid ${baseColor}`,
            }}
          >
            <span
              style={{
                fontSize: '12px',
                color: 'white',
                fontWeight: '700',
              }}
            >
              {currentPassengers}명
            </span>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};
