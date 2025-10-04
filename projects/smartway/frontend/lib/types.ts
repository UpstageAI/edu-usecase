/**
 * Message Type Definition
 *
 * Chart renderer에서 사용하는 메시지 타입
 */

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  chart_data?: any;
  chart_config?: Record<string, any>;
  timestamp: Date;
}
