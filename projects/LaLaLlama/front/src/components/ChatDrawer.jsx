import { useState, useRef, useEffect } from 'react';
import { Drawer } from './Drawer';
import { Button } from './Button';
import { sendChatMessage } from '../lib/api';
import './ChatDrawer.css';

export function ChatDrawer({ isOpen, onClose, proposalId, companyName, globalState }) {
  const { state, addChatMessage } = globalState;
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);
  
  const messages = state.chats[proposalId] || [];
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const handleSend = async () => {
    if (!input.trim() || sending) return;
    
    const userMessage = {
      role: 'user',
      text: input.trim(),
      ts: new Date().toISOString()
    };
    
    addChatMessage(proposalId, userMessage);
    setInput('');
    setSending(true);
    
    try {
      // 현재 사용자 질문 개수 계산 (assistant 메시지는 제외)
      const userQuestionCount = messages.filter(msg => msg.role === 'user').length;
      
      const response = await sendChatMessage(proposalId, userMessage.text, userQuestionCount);
      
      const assistantMessage = {
        role: 'assistant',
        text: response.assistant,
        ts: new Date().toISOString()
      };
      
      addChatMessage(proposalId, assistantMessage);
    } catch (error) {
      console.error('메시지 전송 실패:', error);
      const errorMessage = {
        role: 'assistant',
        text: '죄송합니다. 메시지 전송에 실패했습니다.',
        ts: new Date().toISOString()
      };
      addChatMessage(proposalId, errorMessage);
    } finally {
      setSending(false);
    }
  };
  
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title={`${companyName} 보고서 Q&A`}
    >
      <div className="chat-container">
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-empty">
              <p>이 회사 보고서에 대해 무엇이 궁금하신가요?</p>
            </div>
          ) : (
            messages.map((msg, index) => (
              <div
                key={index}
                className={`chat-message chat-message-${msg.role}`}
              >
                <div className="chat-bubble">
                  {msg.text}
                </div>
                <span className="chat-timestamp">
                  {new Date(msg.ts).toLocaleTimeString('ko-KR', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              </div>
            ))
          )}
          {sending && (
            <div className="chat-message chat-message-assistant">
              <div className="chat-bubble">
                <div className="chat-loading">
                  <span className="dot"></span>
                  <span className="dot"></span>
                  <span className="dot"></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <div className="chat-input-container">
          <textarea
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="이 회사 보고서에 대해 무엇이 궁금하신가요?"
            disabled={sending}
            rows={1}
          />
          <Button
            variant="primary"
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="chat-send-button"
          >
            전송
          </Button>
        </div>
      </div>
    </Drawer>
  );
}

