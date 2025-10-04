'use client';

import { Message as MessageType } from '@/lib/types';
import { cn } from '@/lib/utils';

interface DetailTextRendererProps {
  message: MessageType;
  renderHint?: Record<string, any>;
}

export function DetailTextRenderer({ 
  message, 
  renderHint 
}: DetailTextRendererProps) {
  return (
    <div className="detail-text-container space-y-4">
      {/* Main content with enhanced typography */}
      <div className={cn(
        "prose prose-lg max-w-none",
        "prose-invert prose-headings:text-gray-100",
        "prose-p:text-gray-200 prose-p:leading-relaxed",
        "prose-strong:text-gray-100 prose-strong:font-semibold",
        "prose-code:bg-gray-800 prose-code:px-1 prose-code:rounded",
        "prose-blockquote:border-l-blue-500 prose-blockquote:bg-blue-900/30",
        "prose-ul:space-y-1 prose-ol:space-y-1",
        "prose-li:text-gray-200"
      )}>
        <div className="whitespace-pre-wrap">{message.content}</div>
      </div>
      
      {/* Render hint based additional information */}
      {renderHint?.title && (
        <div className="mt-6 p-4 bg-gray-800 border border-gray-700 rounded-lg">
          <h3 className="text-lg font-semibold text-gray-100 mb-2">
            {renderHint.title}
          </h3>
          {renderHint.description && (
            <p className="text-gray-200 leading-relaxed">
              {renderHint.description}
            </p>
          )}
        </div>
      )}

      {/* Summary section if provided */}
      {renderHint?.summary && (
        <div className="mt-4 p-4 bg-blue-900/30 border border-blue-700/50 rounded-lg">
          <h4 className="text-base font-semibold text-blue-200 mb-2">
            📋 Summary
          </h4>
          <p className="text-blue-100 leading-relaxed">
            {renderHint.summary}
          </p>
        </div>
      )}

      {/* Key points section if provided */}
      {renderHint?.key_points && Array.isArray(renderHint.key_points) && (
        <div className="mt-4 p-4 bg-green-900/30 border border-green-700/50 rounded-lg">
          <h4 className="text-base font-semibold text-green-200 mb-3">
            🎯 Key Points
          </h4>
          <ul className="space-y-2">
            {renderHint.key_points.map((point: string, idx: number) => (
              <li key={idx} className="flex items-start text-green-100">
                <span className="text-green-400 mr-2 mt-1">•</span>
                <span className="leading-relaxed">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions or recommendations if provided */}
      {renderHint?.actions && Array.isArray(renderHint.actions) && (
        <div className="mt-4 p-4 bg-amber-900/30 border border-amber-700/50 rounded-lg">
          <h4 className="text-base font-semibold text-amber-200 mb-3">
            ⚡ Recommended Actions
          </h4>
          <ul className="space-y-2">
            {renderHint.actions.map((action: string, idx: number) => (
              <li key={idx} className="flex items-start text-amber-100">
                <span className="text-amber-400 mr-2 mt-1">→</span>
                <span className="leading-relaxed">{action}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Metadata section */}
      {(renderHint?.confidence || renderHint?.llm_reasoning) && (
        <div className="mt-6 pt-4 border-t border-gray-700">
          <div className="text-xs text-gray-400 space-y-1">
            {renderHint.confidence && (
              <div className="flex items-center justify-between">
                <span>Confidence:</span>
                <span className="font-medium">
                  {Math.round(renderHint.confidence * 100)}%
                </span>
              </div>
            )}
            {renderHint.llm_reasoning && (
              <div className="mt-2">
                <span className="font-medium">Reasoning:</span>
                <p className="mt-1 text-gray-300 text-xs leading-relaxed">
                  {renderHint.llm_reasoning}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}