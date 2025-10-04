'use client';

import { TextWithLineChartRenderer } from '../chart_renderers/TextWithLineChartRenderer';
import { TextWithBarChartRenderer } from '../chart_renderers/TextWithBarChartRenderer';
import { TextWithTableRenderer } from '../chart_renderers/TextWithTableRenderer';
import { DetailTextRenderer } from '../chart_renderers/DetailTextRenderer';

interface AnalyticsOutputRendererProps {
  chartType: 'line_chart' | 'bar_chart' | 'table' | 'text_summary';
  chartData: any;
  analysisResult: string;
  renderHint?: Record<string, any>;
}

export function AnalyticsOutputRenderer({
  chartType,
  chartData,
  analysisResult,
  renderHint
}: AnalyticsOutputRendererProps) {
  // Message 포맷 변환 (기존 renderer 인터페이스 준수)
  const message = {
    id: Date.now().toString(),
    role: 'assistant' as const,
    content: analysisResult,
    chart_data: chartData,
    chart_config: renderHint?.chart_config,
    timestamp: new Date()
  };

  switch (chartType) {
    case 'line_chart':
      return <TextWithLineChartRenderer message={message} renderHint={renderHint} />;

    case 'bar_chart':
      return <TextWithBarChartRenderer message={message} renderHint={renderHint} />;

    case 'table':
      return <TextWithTableRenderer message={message} renderHint={renderHint} />;

    case 'text_summary':
    default:
      return <DetailTextRenderer message={message} renderHint={renderHint} />;
  }
}
