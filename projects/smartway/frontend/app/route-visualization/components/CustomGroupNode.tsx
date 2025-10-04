import React, { memo } from 'react';
import { GroupNodeData } from '../types/route.types';
import { nodeStyles } from '../utils/styleConfig';

interface CustomGroupNodeProps {
  data: GroupNodeData;
  id: string;
}

const CustomGroupNode: React.FC<CustomGroupNodeProps> = ({ data, id }) => {
  const { label } = data;

  // 출근/퇴근 구분
  const isCommute = label.includes('출근');
  const groupStyle = isCommute ? nodeStyles.group.commute : nodeStyles.group.return;

  return (
    <div
      style={{
        ...groupStyle,
        borderRadius: '12px',
        padding: '40px',
        minWidth: '280px',
        minHeight: '600px',
        position: 'relative',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: '10px',
          left: '10px',
          fontWeight: '700',
          fontSize: '16px',
          color: isCommute ? '#1e40af' : '#c2410c',
        }}
      >
        {label}
      </div>
    </div>
  );
};

export default memo(CustomGroupNode);
