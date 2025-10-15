'use client';

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

interface ChartRendererProps {
  data: any;
  config?: {
    type?: 'line' | 'bar';
    [key: string]: any;
  };
  height?: number;
  className?: string;
}

export function ChartRenderer({
  data,
  config = {},
  height = 300,
  className = ''
}: ChartRendererProps) {
  if (!data) return null;

  const chartType = config.type || 'line';

  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  };

  const mergedOptions = {
    ...defaultOptions,
    ...config,
  };

  return (
    <div className={className} style={{ height: `${height}px` }}>
      {chartType === 'line' ? (
        <Line data={data} options={mergedOptions} />
      ) : (
        <Bar data={data} options={mergedOptions} />
      )}
    </div>
  );
}
