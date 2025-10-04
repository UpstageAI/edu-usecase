'use client';

import { useState } from 'react';
import { sendMessage } from '../utils/analytics-api';
import { AnalyticsOutputRenderer } from './AnalyticsOutputRenderer';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  chart_type?: 'line_chart' | 'bar_chart' | 'table' | 'text_summary';
  chart_data?: any;
  highlight_edge?: any;
  intent_type?: string;
  insights?: string[];
}

interface RightPanelProps {
  onHighlightEdge?: (edge: any) => void;
}

export function RightPanel({ onHighlightEdge }: RightPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendMessage(input);

      // Find/Highlight: edge highlighting
      if (response.intent_type === 'find_highlight' && response.highlight_edge && onHighlightEdge) {
        onHighlightEdge(response.highlight_edge);
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.analysis_result || '분석 완료',
        chart_type: response.chart_type || undefined,
        chart_data: response.chart_data,
        highlight_edge: response.highlight_edge,
        intent_type: response.intent_type,
        insights: response.insights
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: '오류가 발생했습니다. 백엔드 서버가 실행 중인지 확인해주세요.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !loading) {
      handleSend();
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#0f172a'
    }}>
      {/* Header */}
      <div style={{
        padding: '12px',
        borderBottom: '1px solid #334155',
        background: '#1e293b'
      }}>
        <h2 style={{
          fontSize: '18px',
          fontWeight: '600',
          color: 'white',
          margin: 0
        }}>
          Analytics Agent
        </h2>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        {messages.length === 0 ? (
          <div style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#64748b'
          }}>
            <div style={{ textAlign: 'center' }}>
              <p style={{ fontSize: '24px', marginBottom: '8px' }}>💬</p>
              <p style={{ marginBottom: '16px' }}>질문을 입력하여 분석을 시작하세요</p>
              <div style={{ fontSize: '12px', color: '#475569' }}>
                <p style={{ marginBottom: '8px' }}>예시:</p>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                  <li style={{ marginBottom: '4px' }}>• 가장 포화가 많은 노선은?</li>
                  <li style={{ marginBottom: '4px' }}>• 월별 운행 단가 추이를 보여줘</li>
                  <li>• 노선별 수익률 비교해줘</li>
                </ul>
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id}>
              {/* User message */}
              {msg.role === 'user' && (
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <div style={{
                    background: '#3b82f6',
                    color: 'white',
                    borderRadius: '8px',
                    padding: '12px 16px',
                    maxWidth: '80%'
                  }}>
                    {msg.content}
                  </div>
                </div>
              )}

              {/* Assistant message */}
              {msg.role === 'assistant' && (
                <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                  <div style={{
                    background: '#1e293b',
                    borderRadius: '8px',
                    padding: '16px',
                    maxWidth: '90%',
                    width: '100%'
                  }}>
                    {/* Find/Highlight response */}
                    {msg.intent_type === 'find_highlight' && msg.highlight_edge && (
                      <>
                        {/* Highlight box */}
                        <div style={{
                          marginBottom: '12px',
                          padding: '12px',
                          background: 'rgba(34, 197, 94, 0.1)',
                          border: '1px solid rgba(34, 197, 94, 0.3)',
                          borderRadius: '6px'
                        }}>
                          <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0, fontFamily: 'monospace' }}>
                            🎯 {msg.highlight_edge.source} → {msg.highlight_edge.target}
                          </p>
                        </div>

                        {/* Analysis result (separated) */}
                        <div style={{
                          padding: '12px',
                          background: 'rgba(100, 116, 139, 0.1)',
                          border: '1px solid rgba(100, 116, 139, 0.3)',
                          borderRadius: '6px'
                        }}>
                          <p style={{ color: '#cbd5e1', fontSize: '13px', fontWeight: '600', marginBottom: '8px' }}>
                            📊 분석 결과
                          </p>
                          <p style={{ color: '#e2e8f0', fontSize: '14px', margin: 0, lineHeight: '1.6' }}>
                            {msg.content}
                          </p>
                        </div>
                      </>
                    )}

                    {/* Analysis response */}
                    {msg.intent_type === 'analysis' && msg.chart_type && (
                      <AnalyticsOutputRenderer
                        chartType={msg.chart_type}
                        chartData={msg.chart_data}
                        analysisResult={msg.content}
                        renderHint={{
                          insights: msg.insights || [],
                          chart_config: {}
                        }}
                      />
                    )}

                    {/* Fallback text */}
                    {!msg.chart_type && !msg.highlight_edge && (
                      <p style={{ color: '#e5e7eb', margin: 0, whiteSpace: 'pre-wrap' }}>
                        {msg.content}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              background: '#1e293b',
              borderRadius: '8px',
              padding: '12px 16px'
            }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  background: '#64748b',
                  borderRadius: '50%',
                  animation: 'bounce 1s infinite'
                }} />
                <div style={{
                  width: '8px',
                  height: '8px',
                  background: '#64748b',
                  borderRadius: '50%',
                  animation: 'bounce 1s infinite 0.1s'
                }} />
                <div style={{
                  width: '8px',
                  height: '8px',
                  background: '#64748b',
                  borderRadius: '50%',
                  animation: 'bounce 1s infinite 0.2s'
                }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{
        padding: '10px',
        borderTop: '1px solid #334155',
        background: '#1e293b'
      }}>
        <div style={{ display: 'flex', gap: '3px' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="질문을 입력하세요..."
            disabled={loading}
            style={{
              flex: 1,
              background: '#0f172a',
              color: 'white',
              border: '1px solid #334155',
              borderRadius: '6px',
              padding: '12px',
              outline: 'none',
              opacity: loading ? 0.5 : 1
            }}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            style={{
              background: loading || !input.trim() ? '#475569' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              padding: '12px 20px',
              fontWeight: '500',
              cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
              transition: 'background 0.2s'
            }}
          >
            전송
          </button>
        </div>
      </div>

      {/* CSS for bounce animation */}
      <style jsx>{`
        @keyframes bounce {
          0%, 80%, 100% {
            transform: translateY(0);
          }
          40% {
            transform: translateY(-10px);
          }
        }
      `}</style>
    </div>
  );
}
