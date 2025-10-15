'use client';

import { useMemo, useState } from 'react';
import { Message as MessageType } from '@/lib/types';
import { DataTable } from '@/components/charts/DataTable';
import { Button } from '@/components/ui/button';

interface TextWithTableRendererProps {
  message: MessageType;
  renderHint?: Record<string, any>;
}

export function TextWithTableRenderer({ 
  message, 
  renderHint 
}: TextWithTableRendererProps) {
  const [showFullTable, setShowFullTable] = useState(false);

  const previewLimit = useMemo(() => {
    const hintValue = Number(renderHint?.preview_limit);
    if (!Number.isFinite(hintValue) || hintValue <= 0) {
      return 10;
    }
    return Math.max(1, Math.floor(hintValue));
  }, [renderHint?.preview_limit]);

  const originalData = Array.isArray(message.chart_data) ? message.chart_data : [];
  const tableData = useMemo(() => {
    if (!originalData.length) {
      return [];
    }
    if (!showFullTable && originalData.length > previewLimit) {
      return originalData.slice(0, previewLimit);
    }
    return originalData;
  }, [originalData, showFullTable, previewLimit]);

  const totalRows = originalData.length;
  const isPreviewing = !showFullTable && totalRows > previewLimit;
  const effectivePageSize = useMemo(() => {
    const base = Number(renderHint?.page_size) || 10;
    if (isPreviewing) {
      return Math.min(base, previewLimit);
    }
    return base;
  }, [renderHint?.page_size, isPreviewing, previewLimit]);

  // output_type: text+table always renders data as a table (no charts)
  // Calculate table statistics
  const getTableStats = () => {
    if (!originalData.length) return null;
    
    const columns = originalData.length > 0 ? Object.keys(originalData[0]) : [];
    
    return {
      totalRows,
      totalColumns: columns.length,
      columns,
    };
  };

  const tableStats = getTableStats();

  return (
    <div className="text-with-table space-y-6">
      
      {/* Table and summary layout */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Data table - spans 3 columns on extra large screens */}
        <div className="xl:col-span-3">
          {tableData.length > 0 ? (
            <DataTable
              data={tableData}
              title={renderHint?.table_title || "Data"}
              pageSize={effectivePageSize}
              searchable={renderHint?.searchable !== false}
              sortable={renderHint?.sortable !== false}
              className="h-fit"
            />
          ) : (
            <div className="min-h-[400px] bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center">
              <div className="text-center text-gray-500">
                <div className="text-2xl mb-2">📋</div>
                <p>표시할 데이터가 없습니다</p>
              </div>
            </div>
          )}

          {totalRows > 0 && (
            <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between text-xs text-gray-500">
              {isPreviewing ? (
                <>
                  <span>
                    총 {totalRows}행 중 {previewLimit}행만 미리 보여주는 중입니다.
                  </span>
                  <div className="flex gap-2 sm:justify-end">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setShowFullTable(true)}
                    >
                      전체 데이터 보기
                    </Button>
                  </div>
                </>
              ) : originalData.length > previewLimit ? (
                <>
                  <span>전체 {totalRows}행 데이터를 표시 중입니다.</span>
                  <div className="flex gap-2 sm:justify-end">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setShowFullTable(false)}
                    >
                      요약 보기로 접기
                    </Button>
                  </div>
                </>
              ) : null}
            </div>
          )}
        </div>
        
        {/* Table summary and insights panel */}
        <div className="xl:col-span-1 space-y-4">
          {/* Table statistics */}
          {tableStats && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-3 flex items-center">
                <span className="mr-2">📊</span>
                데이터 요약
              </h4>
              <div className="space-y-2 text-sm text-blue-800">
                <div className="flex justify-between">
                  <span>총 행 수:</span>
                  <span className="font-medium">{tableStats.totalRows}</span>
                </div>
                <div className="flex justify-between">
                  <span>총 열 수:</span>
                  <span className="font-medium">{tableStats.totalColumns}</span>
                </div>
                {tableStats.columns.length > 0 && (
                  <div className="mt-3">
                    <div className="font-medium text-blue-900 mb-2">컬럼:</div>
                    <div className="space-y-1">
                      {tableStats.columns.map((col, idx) => (
                        <div key={idx} className="text-xs bg-blue-100 px-2 py-1 rounded">
                          {col}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Key insights from data */}
          {renderHint?.insights && Array.isArray(renderHint.insights) && (
            <div className="p-4 bg-blue-900 border border-blue-700 rounded-lg">
              <h4 className="font-semibold text-white mb-3 flex items-center">
                <span className="mr-2">💡</span>
                데이터 인사이트
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

          {/* Data quality indicators */}
          {renderHint?.data_quality && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <h4 className="font-semibold text-amber-900 mb-3 flex items-center">
                <span className="mr-2">🔍</span>
                데이터 품질
              </h4>
              <div className="space-y-2 text-sm text-amber-800">
                {Object.entries(renderHint.data_quality).map(([key, value]) => (
                  <div key={key} className="flex justify-between items-center">
                    <span className="capitalize">{key}:</span>
                    <span className="font-medium">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Filters applied */}
          {renderHint?.filters && Array.isArray(renderHint.filters) && (
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                <span className="mr-2">🔧</span>
                적용된 필터
              </h4>
              <ul className="space-y-1 text-sm text-gray-700">
                {renderHint.filters.map((filter: string, idx: number) => (
                  <li key={idx} className="flex items-center">
                    <span className="text-gray-500 mr-2">▪</span>
                    <span>{filter}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Export options */}
          {renderHint?.export_options && (
            <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
              <h4 className="font-semibold text-purple-900 mb-3 flex items-center">
                <span className="mr-2">📁</span>
                내보내기 옵션
              </h4>
              <p className="text-sm text-purple-800 leading-relaxed">
                {renderHint.export_options}
              </p>
            </div>
          )}

          {/* Navigation tips */}
          <div className="p-4 bg-gray-100 border border-gray-300 rounded-lg">
            <h4 className="font-semibold text-gray-900 mb-2 flex items-center">
              <span className="mr-2">💡</span>
              사용 팁
            </h4>
            <ul className="space-y-1 text-xs text-gray-600">
              <li>• 열 헤더 클릭으로 정렬</li>
              <li>• 검색창으로 데이터 필터링</li>
              <li>• 페이지네이션으로 대량 데이터 탐색</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Additional notes or context */}
      {renderHint?.notes && (
        <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <h4 className="font-semibold text-gray-900 mb-2 flex items-center">
            <span className="mr-2">📝</span>
            추가 정보
          </h4>
          <p className="text-gray-700 leading-relaxed">
            {renderHint.notes}
          </p>
        </div>
      )}

      {/* Metadata */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="text-xs text-gray-500 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <span>표시 형식: 구조화된 데이터 테이블</span>
            {tableStats && (
              <span>총 {tableStats.totalRows}행 × {tableStats.totalColumns}열</span>
            )}
          </div>
          {renderHint?.confidence && (
            <span>데이터 신뢰도: {Math.round(renderHint.confidence * 100)}%</span>
          )}
        </div>
      </div>
    </div>
  );
}
