'use client';

import { Message as MessageType } from '@/lib/types';
import { ChartRenderer } from '@/components/charts/ChartRenderer';

interface TextWithBarChartRendererProps {
  message: MessageType;
  renderHint?: Record<string, any>;
}

export function TextWithBarChartRenderer({ 
  message, 
  renderHint 
}: TextWithBarChartRendererProps) {
  // Get chart data from message or render hint
  const chartData = message.chart_data || renderHint?.chart_data;
  const messageChartConfig = message.chart_config || renderHint?.chart_config || {};

  // Prepare chart config with bar type (output_type: text+bar_chart always uses bar charts)
  const chartConfig = {
    ...messageChartConfig,
    type: 'bar' as const, // Ensure bar chart for text+bar_chart output type
    ...renderHint?.chart_config,
  };

  // Helper function to get ranking indicators
  const getRankingData = () => {
    if (!chartData || !Array.isArray(chartData)) return null;
    
    const data = chartData;
    const valueColumn = chartConfig.y_column || chartConfig.values_column;
    
    if (!valueColumn) return null;

    // Sort by value for ranking
    const sorted = [...data].sort((a, b) => {
      const aVal = Number(a[valueColumn]) || 0;
      const bVal = Number(b[valueColumn]) || 0;
      return bVal - aVal; // Descending order
    });

    return {
      highest: sorted[0],
      lowest: sorted[sorted.length - 1],
      count: sorted.length,
    };
  };

  const rankingData = getRankingData();

  return (
    <div className="text-with-bar-chart space-y-6">      
      {/* Chart and analysis layout - only show if chart data exists */}
      {chartData && (messageChartConfig || renderHint?.chart_config) ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Bar chart - spans 2 columns on large screens */}
          <div className="lg:col-span-2">
            <ChartRenderer 
              data={chartData}
              config={chartConfig}
              height={250}
              className="w-full"
            />
          </div>
        
        {/* Analysis and ranking panel */}
        <div className="lg:col-span-1 space-y-4">
          {/* Ranking highlights */}
          {rankingData && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-3 flex items-center">
                <span className="mr-2">🏆</span>
                Ranking Analysis
              </h4>
              <div className="space-y-3 text-sm">
                <div className="p-2 bg-blue-100 rounded">
                  <div className="font-medium text-blue-900">Highest Value</div>
                  <div className="text-blue-800">
                    {chartConfig.x_column && rankingData.highest[chartConfig.x_column]}
                    {chartConfig.names_column && rankingData.highest[chartConfig.names_column]}
                  </div>
                  <div className="text-xs text-blue-700 mt-1">
                    {chartConfig.y_column && rankingData.highest[chartConfig.y_column] && 
                      `Value: ${new Intl.NumberFormat('en-US').format(Number(rankingData.highest[chartConfig.y_column]))}`}
                  </div>
                </div>
                
                <div className="p-2 bg-gray-100 rounded">
                  <div className="font-medium text-gray-900">Lowest Value</div>
                  <div className="text-gray-800">
                    {chartConfig.x_column && rankingData.lowest[chartConfig.x_column]}
                    {chartConfig.names_column && rankingData.lowest[chartConfig.names_column]}
                  </div>
                  <div className="text-xs text-gray-700 mt-1">
                    {chartConfig.y_column && rankingData.lowest[chartConfig.y_column] && 
                      `Value: ${new Intl.NumberFormat('en-US').format(Number(rankingData.lowest[chartConfig.y_column]))}`}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Key insights */}
          {renderHint?.insights && Array.isArray(renderHint.insights) && (
            <div className="p-4 bg-blue-900 border border-blue-700 rounded-lg">
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

          {/* Comparison analysis */}
          {renderHint?.comparison && (
            <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
              <h4 className="font-semibold text-purple-900 mb-2 flex items-center">
                <span className="mr-2">⚖️</span>
                Comparative Analysis
              </h4>
              <p className="text-sm text-purple-800 leading-relaxed">
                {renderHint.comparison}
              </p>
            </div>
          )}

          {/* Performance metrics */}
          {renderHint?.metrics && (
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                <span className="mr-2">📈</span>
                Performance Metrics
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

          {/* Action items */}
          {renderHint?.action_items && Array.isArray(renderHint.action_items) && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <h4 className="font-semibold text-amber-900 mb-3 flex items-center">
                <span className="mr-2">✅</span>
                Action Items
              </h4>
              <ul className="space-y-2 text-sm text-amber-800">
                {renderHint.action_items.map((item: string, idx: number) => (
                  <li key={idx} className="flex items-start">
                    <span className="text-amber-600 mr-2 mt-0.5">→</span>
                    <span className="leading-relaxed">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        </div>
      ) : (
        // Fallback when no chart data is available
        <div className="min-h-[200px] bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="text-2xl mb-2">📊</div>
            <p>바 차트 데이터가 없습니다</p>
            <p className="text-xs mt-1">출력 타입: text+bar_chart</p>
          </div>
        </div>
      )}

      {/* Additional context or notes */}
      {renderHint?.summary && (
        <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <h4 className="font-semibold text-gray-900 mb-2 flex items-center">
            <span className="mr-2">📝</span>
            Analysis Summary
          </h4>
          <p className="text-gray-700 leading-relaxed">
            {renderHint.summary}
          </p>
        </div>
      )}
    </div>
  );
}