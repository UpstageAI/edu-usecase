const DATA_SOURCE = import.meta.env.VITE_DATA_SOURCE || 'mock';

/**
 * Mock 모드: public/mock/*.json 파일을 로드
 * 20초 고정 딜레이를 적용하여 로딩 연출
 */
async function fetchMockJson(resourceKey, delayMs = 0) {
  if (delayMs > 0) {
    await new Promise(resolve => setTimeout(resolve, delayMs));
  }

  const response = await fetch(`/mock/${resourceKey}.json`);
  if (!response.ok) {
    throw new Error(`Failed to load mock data: ${resourceKey}`);
  }
  return response.json();
}

/**
 * API 모드: 실제 서버 호출 (단발성, 폴링 없음)
 * 응답의 status/progress/estNextUpdateSec는 UI 애니메이션 용도로만 사용
 */
async function callApi(endpoint, options = {}) {
  const response = await fetch(`/api${endpoint}`, {
    method: options.method || 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    body: options.body ? JSON.stringify(options.body) : undefined
  });
  
  if (!response.ok) {
    throw new Error(`API call failed: ${endpoint}`);
  }
  
  return response.json();
}

/**
 * 평가 트리거 (evaluation.create)
 */
export async function createEvaluation(files) {
  if (DATA_SOURCE === 'mock') {
    return fetchMockJson('evaluation.create', 20000);
  } else {
    return callApi('/evaluations', {
      method: 'POST',
      body: files
    });
  }
}

/**
 * 보고서 조회 (report-{proposalId})
 */
export async function getReport(proposalId) {
  if (DATA_SOURCE === 'mock') {
    return fetchMockJson(`report-${proposalId}`);
  } else {
    return callApi(`/reports/${proposalId}`);
  }
}

export async function downloadReportPdf(proposalId) {
  if (DATA_SOURCE === 'mock') {
    const response = await fetch(`/mock/report-${proposalId}.pdf`);
    if (!response.ok) {
      throw new Error(`Failed to download mock report PDF: ${proposalId}`);
    }
    return response.blob();
  }

  const response = await fetch(`/api/reports/${proposalId}/pdf`);
  if (!response.ok) {
    throw new Error(`Report PDF download failed: ${proposalId}`);
  }
  return response.blob();
}

/**
 * 챗 메시지 전송 (chat.send-{proposalId})
 */
export async function sendChatMessage(proposalId, message, questionCount = 0) {
  if (DATA_SOURCE === 'mock') {
    // Mock 모드에서 10초 고정 딜레이로 응답 연출
    await new Promise(resolve => setTimeout(resolve, 10000));
    
    // 질문 순서에 따라 다른 답변 파일 선택
    // 첫 번째 질문(questionCount === 0): abc 답변
    // 두 번째 질문(questionCount === 1): def 답변
    // 세 번째 질문 이후(questionCount >= 2): ghi 답변
    let mockFile;
    if (questionCount === 0) {
      mockFile = 'chat.send-p-abc';
    } else if (questionCount === 1) {
      mockFile = 'chat.send-p-def';
    } else {
      mockFile = 'chat.send-p-ghi';
    }
    
    return fetchMockJson(mockFile);
  } else {
    return callApi(`/chat/${proposalId}/messages`, {
      method: 'POST',
      body: { message }
    });
  }
}

/**
 * 챗 히스토리 조회 (chat.history-{proposalId})
 * v1에서는 사용하지 않지만, 확장을 위해 정의
 */
export async function getChatHistory(proposalId) {
  if (DATA_SOURCE === 'mock') {
    return fetchMockJson(`chat.history-${proposalId}`);
  } else {
    return callApi(`/chat/${proposalId}/history`);
  }
}

