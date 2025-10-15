/**
 * Analytics API Client
 *
 * Backend Analytics Agent와 통신하는 API 클라이언트
 */

export interface AnalyticsResponse {
  intent_type: string;
  highlight_edge?: {
    id: string;
    source: string;
    target: string;
    label: string;
  } | null;
  chart_data?: any;
  analysis_result?: string | null;
  chart_type?: 'line_chart' | 'bar_chart' | 'table' | 'text_summary' | null;
}

/**
 * Analytics Agent에 질문 전송
 *
 * @param question 사용자 질문
 * @returns Analytics 응답
 */
export async function sendMessage(question: string): Promise<AnalyticsResponse> {
  const response = await fetch('http://localhost:8000/api/analytics', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    throw new Error(`Analytics API error: ${response.statusText}`);
  }

  return response.json();
}
