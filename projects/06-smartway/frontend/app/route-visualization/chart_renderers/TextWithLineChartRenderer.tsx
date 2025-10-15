'use client';

import { Message as MessageType } from '@/lib/types';
import { ChartRenderer } from '@/components/charts/ChartRenderer';

interface TextWithLineChartRendererProps {
  message: MessageType;
  renderHint?: Record<string, any>;
}

export function TextWithLineChartRenderer({
  message,
  renderHint
}: TextWithLineChartRendererProps) {
  // Debug logging (only in development)
  if (process.env.NODE_ENV === 'development') {
    console.log('📈 TextWithLineChartRenderer received:', {
      has_message_chart_data: !!message.chart_data,
      has_message_chart_config: !!message.chart_config,
      has_render_hint: !!renderHint,
      render_hint_has_chart_data: !!renderHint?.chart_data,
      render_hint_has_chart_config: !!renderHint?.chart_config
    });
  }

  // Try to get chart data from render_hint if not in message
  const chartData = message.chart_data || renderHint?.chart_data;
  const messageChartConfig = message.chart_config || renderHint?.chart_config || {};

  // Prepare chart config with line type (output_type: text+line_chart always uses line charts)
  const chartConfig = {
    ...messageChartConfig,
    type: 'line' as const, // Ensure line chart for text+line_chart output type
    ...renderHint?.chart_config,
  };

  return (
    <div className="text-with-line-chart space-y-6 w-full">
      
      {/* Chart section - only show if data is available */}
      {chartData && (messageChartConfig || renderHint?.chart_config) ? (
        <div className="w-full">
          <ChartRenderer
            data={chartData}
            config={chartConfig}
            height={400}
            className="w-full h-full"
          />
        </div>
      ) : (
        // Fallback when no chart data is available
        <div className="min-h-[200px] bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="text-2xl mb-2">📈</div>
            <p>라인 차트 데이터가 없습니다</p>
            <p className="text-xs mt-1">출력 타입: text+line_chart</p>
          </div>
        </div>
      )}

      {/* Insights and metadata panel */}
      <div className="space-y-4">
          {/* Key insights */}
          {renderHint?.insights && Array.isArray(renderHint.insights) && (
            <div className="p-4 bg-blue-900 border border-blue-700 rounded-lg h-fit">
              <h4 className="font-semibold text-white mb-3 flex items-center">
                <span className="mr-2">💡</span>
                Key Insights
              </h4>
              <div className="space-y-3 text-sm text-white">
                {renderHint.insights.map((insight: string, idx: number) => (
                  <p key={idx} className="leading-relaxed">
                    {insight}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Trend analysis */}
          {renderHint?.trend && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <h4 className="font-semibold text-green-900 mb-2 flex items-center">
                <span className="mr-2">📈</span>
                Trend Analysis
              </h4>
              <p className="text-sm text-green-800 leading-relaxed">
                {renderHint.trend}
              </p>
            </div>
          )}

          {/* Key metrics */}
          {renderHint?.metrics && (
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                <span className="mr-2">📊</span>
                Key Metrics
              </h4>
              <div className="space-y-2 text-sm">
                {Object.entries(renderHint.metrics).map(([key, value]) => (
                  <div key={key} className="flex justify-between items-center">
                    <span className="text-gray-600">{key}:</span>
                    <span className="font-medium text-gray-900">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {renderHint?.recommendations && Array.isArray(renderHint.recommendations) && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <h4 className="font-semibold text-amber-900 mb-3 flex items-center">
                <span className="mr-2">🎯</span>
                Recommendations
              </h4>
              <ul className="space-y-2 text-sm text-amber-800">
                {renderHint.recommendations.map((rec: string, idx: number) => (
                  <li key={idx} className="flex items-start">
                    <span className="text-amber-600 mr-2 mt-0.5">→</span>
                    <span className="leading-relaxed">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

      {/* Additional context or summary */}
      {renderHint?.summary && (
        <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <h4 className="font-semibold text-gray-900 mb-2 flex items-center">
            <span className="mr-2">📝</span>
            Summary
          </h4>
          <p className="text-gray-700 leading-relaxed">
            {renderHint.summary}
          </p>
        </div>
      )}
    </div>
  );
}