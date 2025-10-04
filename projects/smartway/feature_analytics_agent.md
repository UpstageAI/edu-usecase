# Feature: Analytics Agent Implementation

## Overview
사용자 질문에 기반한 버스 노선 데이터 분석 및 시각화 시스템. LangGraph를 활용한 intelligent routing으로 두 가지 주요 경로(Find/Highlight, Analysis)를 처리.

## Architecture

### System Flow
```
User Question
    ↓
Intent Analysis (Router Node)
    ↓
    ├─→ [Find/Highlight Path]
    │   ├─ get_graph_data (node_edge.json)
    │   ├─ select_edge (edge selection logic)
    │   ├─ Output: highlight_edge + analysis_result
    │   └─ Action: highlighting_edge on graph
    │
    └─→ [Analysis Path]
        ├─ get_bus_data (승하차정보.json + 통근수당.json)
        ├─ chart_type_selector (line/bar/table/text)
        ├─ analytic (Solar Pro2 analysis)
        ├─ Output: chart_data + result
        └─ output_router
            ├─ line_chart
            ├─ bar_chart
            ├─ table
            └─ text_summary
```

## Data Sources

### 1. Find/Highlight Path Data
- **node_edge.json**: React Flow graph structure
  - nodes: 정류장 노드 (id, type, label, position, parentId)
  - edges: 노선 연결 (id, source, target, label)

### 2. Analysis Path Data
- **승하차정보.json** (45 records)
  ```json
  {
    "노선명": "출근1호-한국대서문",
    "구분": "업스테이지 출근",
    "출발시간": "07:00",
    "차량번호": "경기12어1234",
    "순번": 1,
    "정류장명": "한국대 동문 버스정류장",
    "승/하차": "승차",
    "인원": 1
  }
  ```

- **통근수당.json** (8 records)
  ```json
  {
    "구분": "업스테이지 출근",
    "노선명": "출근1호-한국대서문",
    "출발시간": "07:00:00",
    "운행거리": "10KM",
    "운행단가": 73000,
    "지급수당": 10000,
    "야간수당": 15000
  }
  ```

## Implementation Plan

### Phase 1: Core LangGraph Setup

#### 1.1 State Definition (LangGraph)
```python
# backend/analytics/types/state_types.py
from typing import TypedDict, Annotated, Optional, Literal
from langgraph.graph.message import add_messages

class AnalyticsState(TypedDict):
    """
    Analytics Agent의 전체 상태를 정의하는 클래스

    LangGraph 실행 중 유지되는 상태:
    - messages: 대화 메시지 리스트 (자동 누적)
    - intent_type: 질문 유형 (find_highlight | analysis | fallback)

    Find/Highlight Path 상태:
    - graph_data: ReactFlow 그래프 데이터
    - highlight_edge: 선택된 엣지 정보

    Analysis Path 상태:
    - transport_data: 승하차 정보 JSON 문자열
    - commute_allowance_data: 통근 수당 JSON 문자열
    - chart_type: 차트 타입
    - chart_data: 차트 데이터
    - analysis_result: 분석 결과 텍스트
    """
    messages: Annotated[list, add_messages]
    intent_type: Optional[Literal['find_highlight', 'analysis', 'fallback']]

    # Find/Highlight specific
    graph_data: Optional[dict]
    highlight_edge: Optional[dict]

    # Analysis specific
    transport_data: Optional[str]
    commute_allowance_data: Optional[str]
    chart_type: Optional[Literal['line_chart', 'bar_chart', 'table', 'text_summary']]
    chart_data: Optional[dict]
    analysis_result: Optional[str]
```

#### 1.2 Router Node (LLM-based Intent Analysis)
```python
# backend/analytics/nodes/router.py
from analytics.types.state_types import AnalyticsState
from config import build_chat_model
from langchain_core.messages import SystemMessage
import json

def intent_analyzer(state: AnalyticsState):
    """
    LLM을 사용하여 사용자 질문의 Intent 분석 (LangGraph Node)

    Args:
        state (AnalyticsState): 현재 그래프 상태

    Returns:
        dict: 업데이트할 상태 {"intent_type": "find_highlight" | "analysis" | "fallback"}

    Intent Types:
    - find_highlight: 특정 노선/정류장을 찾거나 하이라이트하는 질문
    - analysis: 데이터 분석, 차트 생성, 통계 요청
    - fallback: 위 두 가지에 해당하지 않는 질문

    Examples:
    - "가장 포화가 많은 노선은?" → find_highlight
    - "월별 운행 단가 추이를 보여줘" → analysis
    - "안녕하세요" → fallback
    """
    # 사용자 메시지 추출
    user_message = state["messages"][-1]
    user_question = user_message.content if hasattr(user_message, 'content') else str(user_message)

    # LLM을 사용한 Intent 분류
    system_prompt = """
당신은 버스 노선 데이터 분석 시스템의 Intent Classifier입니다.

사용자 질문을 분석하여 다음 3가지 중 하나로 분류하세요:

1. **find_highlight**: 특정 노선이나 정류장을 찾거나 하이라이트하는 질문
   - 예시: "가장 포화가 많은 노선은?", "운행 단가가 가장 높은 노선은?", "BYC 사거리는 어디야?"
   - 특징: "어디", "어느", "가장", "최대", "최소", "높은", "낮은" 등의 표현 포함
   - 목적: 그래프에서 특정 edge/node를 하이라이트

2. **analysis**: 데이터 분석, 차트 생성, 통계 정보 요청
   - 예시: "월별 운행 단가 추이를 보여줘", "노선별 수익률 비교", "전체 노선 통계"
   - 특징: "분석", "추이", "비교", "그래프", "차트", "통계", "현황" 등의 표현 포함
   - 목적: 차트나 표를 생성하여 데이터 시각화

3. **fallback**: 위 두 가지에 해당하지 않는 질문
   - 예시: "안녕하세요", "도움말", "무엇을 할 수 있나요?"
   - 목적: 기본 응답 제공

응답 형식 (JSON만 출력, 다른 설명 금지):
{
    "intent": "find_highlight" | "analysis" | "fallback",
    "confidence": 0.0-1.0,
    "reason": "분류 근거 간단히 설명"
}
"""

    messages = [
        SystemMessage(content=system_prompt),
        user_message
    ]

    # LLM 호출
    llm = build_chat_model(temperature=0.3)
    response = llm.invoke(messages)

    try:
        # JSON 파싱
        result = json.loads(response.content.strip())
        intent = result.get("intent", "fallback")
        confidence = result.get("confidence", 0.0)
        reason = result.get("reason", "")

        print(f"🎯 Intent Analysis (LLM): {intent} (confidence: {confidence:.2f})")
        print(f"   Reason: {reason}")

    except json.JSONDecodeError:
        # JSON 파싱 실패 시 fallback
        print(f"⚠️  Intent parsing failed, using fallback")
        intent = "fallback"

    return {"intent_type": intent}


def conditional_router(state: AnalyticsState) -> str:
    """
    Intent에 따라 다음 노드 결정 (LangGraph Conditional Edge)

    Args:
        state (AnalyticsState): 현재 그래프 상태

    Returns:
        str: 다음 노드 이름
    """
    intent = state.get("intent_type", "fallback")

    route_map = {
        "find_highlight": "get_graph_data",
        "analysis": "get_bus_data",
        "fallback": "fallback_response"
    }

    next_node = route_map.get(intent, "fallback_response")
    print(f"🔀 Routing to: {next_node}")

    return next_node
```

### Phase 2: Find/Highlight Path

#### 2.1 Get Graph Data Node
```python
# backend/src/analytics/nodes/find_highlight.py
def get_graph_data(state: AnalyticsState):
    """
    ReactFlow 그래프 데이터 로드
    - data/reactflow_graph_route_stop.json 읽기
    - LLM이 이해하기 쉬운 구조로 변환
    """
    try:
        with open("data/reactflow_graph_route_stop.json", 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # 노드 정보 추출
        nodes = [
            {
                "id": node["id"],
                "type": node["type"],
                "label": node.get("data", {}).get("label", "")
            }
            for node in raw_data.get("nodes", [])
        ]

        # 엣지 정보 추출
        edges = [
            {
                "id": edge["id"],
                "source": edge["source"],
                "target": edge["target"],
                "label": edge.get("label", "")
            }
            for edge in raw_data.get("edges", [])
        ]

        summary = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "description": "버스 노선과 정류장 정보를 담은 ReactFlow 그래프"
        }

        return {
            "graph_data": {
                "nodes": nodes,
                "edges": edges,
                "summary": summary
            }
        }
    except Exception as e:
        return {"graph_data": {"error": str(e)}}
```

#### 2.2 Select Edge Node
```python
def select_edge(state: AnalyticsState):
    """
    LLM을 사용하여 사용자 질문에 맞는 엣지 선택

    예시 질문:
    - "가장 포화가 많은 노선은?"
    - "BYC 사거리에서 업스테이지로 가는 경로는?"
    """
    user_question = state["messages"][-1].content
    graph_data = state.get("graph_data", {})

    edges_json = json.dumps(graph_data.get("edges", []), ensure_ascii=False)

    system_prompt = f"""
    사용자 질문: {user_question}

    엣지 데이터:
    {edges_json}

    위 데이터를 참고하여 질문에 맞는 엣지를 찾아주세요.

    응답 형식 (JSON만 출력):
    {{
        "highlight": {{
            "id": "엣지ID",
            "source": "출발노드ID",
            "target": "도착노드ID",
            "label": "엣지라벨"
        }},
        "reason": "선택 이유"
    }}
    """

    llm = build_chat_model(temperature=0.3)
    response = llm.invoke([SystemMessage(content=system_prompt)])

    result = json.loads(response.content)

    return {
        "highlight_edge": result["highlight"],
        "analysis_result": result["reason"],
        "messages": [response]
    }
```

### Phase 3: Analysis Path

#### 3.1 Get Bus Data Node
```python
# backend/src/analytics/nodes/analysis.py
def get_bus_data(state: AnalyticsState):
    """
    버스 데이터 로드
    - 승하차정보.json
    - 통근수당.json
    """
    try:
        with open("data/승하차정보.json", 'r', encoding='utf-8') as f:
            transport_data = json.load(f)

        with open("data/통근수당.json", 'r', encoding='utf-8') as f:
            commute_data = json.load(f)

        return {
            "transport_data": json.dumps(transport_data, ensure_ascii=False),
            "commute_allowance_data": json.dumps(commute_data, ensure_ascii=False)
        }
    except Exception as e:
        return {
            "transport_data": "[]",
            "commute_allowance_data": "[]"
        }
```

#### 3.2 Chart Type Selector Node
```python
def chart_type_selector(state: AnalyticsState):
    """
    사용자 질문에 적합한 차트 타입 선택

    Keywords:
    - line_chart: "추이", "변화", "월별", "시간별", "트렌드"
    - bar_chart: "비교", "노선별", "순위", "상위", "하위"
    - table: "상세", "목록", "전체", "데이터"
    - text_summary: "요약", "설명", "분석 결과"
    """
    user_question = state["messages"][-1].content

    system_prompt = f"""
    사용자 질문: {user_question}

    적합한 차트 타입을 선택하세요.
    선택 가능: line_chart, bar_chart, table, text_summary

    응답: 차트 타입만 영어로 출력 (추가 설명 금지)
    """

    llm = build_chat_model(temperature=0.3)
    response = llm.invoke([SystemMessage(content=system_prompt)])

    chart_type = response.content.strip()

    return {
        "chart_type": chart_type,
        "messages": state["messages"] + [response]
    }
```

#### 3.3 Generate Analytic Node
```python
def generate_analytic(state: AnalyticsState):
    """
    Solar Pro2를 사용하여 데이터 분석 및 차트 데이터 생성
    """
    user_question = state["messages"][0].content
    chart_type = state.get("chart_type", "text_summary")
    transport_data = state.get("transport_data", "")
    commute_data = state.get("commute_allowance_data", "")

    # 차트별 output format 정의
    output_formats = {
        "line_chart": """
        {
            "chart_data": {
                "labels": ["January", "February", ...],
                "datasets": [{
                    "label": "Dataset Label",
                    "data": [65, 59, 80, ...],
                    "borderColor": "rgb(75, 192, 192)",
                    "tension": 0.1
                }]
            },
            "reason": "분석 결과 설명"
        }
        """,
        "bar_chart": """
        {
            "chart_data": {
                "labels": ["노선1", "노선2", ...],
                "datasets": [{
                    "label": "운행단가",
                    "data": [73000, 68000, ...],
                    "backgroundColor": "rgba(75, 192, 192, 0.6)"
                }]
            },
            "reason": "분석 결과 설명"
        }
        """,
        "table": """
        {
            "chart_data": {
                "columns": ["노선명", "운행단가", "지급수당"],
                "rows": [
                    ["출근1호-한국대서문", 73000, 10000],
                    ...
                ]
            },
            "reason": "분석 결과 설명"
        }
        """,
        "text_summary": """
        {
            "chart_data": null,
            "reason": "상세 분석 결과 텍스트"
        }
        """
    }

    system_prompt = f"""
    교통 데이터: {transport_data}
    통근 수당 데이터: {commute_data}

    사용자 질문: {user_question}
    선택된 차트: {chart_type}

    위 데이터를 분석하여 아래 JSON 형식으로만 출력하세요.
    ```json 감싸지 말고 순수 JSON만 출력.

    Output Format:
    {output_formats[chart_type]}
    """

    llm = build_chat_model(model="solar-pro2", temperature=0.5)
    response = llm.invoke([SystemMessage(content=system_prompt)])

    result = json.loads(response.content)

    return {
        "chart_data": result["chart_data"],
        "analysis_result": result["reason"],
        "messages": state["messages"] + [response]
    }
```

### Phase 4: LangGraph Construction

```python
# backend/analytics/graph/analytics_graph.py
"""
Analytics Agent LangGraph 구성

Graph Flow:
    START
      ↓
    intent_analyzer
      ↓ (conditional_router)
    ┌─────────────┬──────────────┐
    ↓             ↓              ↓
get_graph_data  get_bus_data  fallback_response
    ↓             ↓              ↓
select_edge   chart_type_selector  END
    ↓             ↓
   END      generate_analytic
                  ↓
                 END
"""
from langgraph.graph import StateGraph, START, END
from analytics.types.state_types import AnalyticsState
from analytics.nodes.router import intent_analyzer, conditional_router
from analytics.nodes.find_highlight import get_graph_data, select_edge
from analytics.nodes.analysis import get_bus_data, chart_type_selector, generate_analytic
from analytics.nodes.fallback import fallback_response


def build_analytics_graph():
    """
    Analytics Agent LangGraph 구축

    Returns:
        CompiledGraph: 실행 가능한 LangGraph 인스턴스
    """
    # StateGraph 초기화
    workflow = StateGraph(AnalyticsState)

    # ============================================================
    # Nodes 추가
    # ============================================================
    workflow.add_node("intent_analyzer", intent_analyzer)

    # Find/Highlight path nodes
    workflow.add_node("get_graph_data", get_graph_data)
    workflow.add_node("select_edge", select_edge)

    # Analysis path nodes
    workflow.add_node("get_bus_data", get_bus_data)
    workflow.add_node("chart_type_selector", chart_type_selector)
    workflow.add_node("generate_analytic", generate_analytic)

    # Fallback node
    workflow.add_node("fallback_response", fallback_response)

    # ============================================================
    # Edges 구성
    # ============================================================

    # Entry point
    workflow.set_entry_point("intent_analyzer")

    # Conditional routing (intent에 따라 분기)
    workflow.add_conditional_edges(
        "intent_analyzer",
        conditional_router,
        {
            "get_graph_data": "get_graph_data",
            "get_bus_data": "get_bus_data",
            "fallback_response": "fallback_response"
        }
    )

    # Find/Highlight path: get_graph_data → select_edge → END
    workflow.add_edge("get_graph_data", "select_edge")
    workflow.add_edge("select_edge", END)

    # Analysis path: get_bus_data → chart_type_selector → generate_analytic → END
    workflow.add_edge("get_bus_data", "chart_type_selector")
    workflow.add_edge("chart_type_selector", "generate_analytic")
    workflow.add_edge("generate_analytic", END)

    # Fallback: fallback_response → END
    workflow.add_edge("fallback_response", END)

    # ============================================================
    # Compile and return
    # ============================================================
    compiled_graph = workflow.compile()

    print("✅ Analytics Agent LangGraph 구축 완료")

    return compiled_graph


# 싱글톤 패턴으로 그래프 인스턴스 생성
_analytics_graph = None

def get_analytics_graph():
    """
    Analytics Graph 싱글톤 인스턴스 반환

    Returns:
        CompiledGraph: Analytics Agent 그래프
    """
    global _analytics_graph
    if _analytics_graph is None:
        _analytics_graph = build_analytics_graph()
    return _analytics_graph
```

#### Fallback Node 추가

```python
# backend/analytics/nodes/fallback.py
from analytics.types.state_types import AnalyticsState
from langchain_core.messages import AIMessage

def fallback_response(state: AnalyticsState):
    """
    Intent 분류 실패 시 기본 응답 (LangGraph Node)

    Args:
        state (AnalyticsState): 현재 그래프 상태

    Returns:
        dict: 업데이트할 상태
    """
    fallback_message = """
죄송합니다. 질문을 이해하지 못했습니다.

다음과 같은 질문을 시도해보세요:
- "가장 포화가 많은 노선은?" (Find/Highlight)
- "월별 운행 단가 추이를 보여줘" (Analysis)
- "노선별 수익률 비교해줘" (Analysis)
    """

    response = AIMessage(content=fallback_message.strip())

    return {
        "messages": [response],
        "analysis_result": fallback_message.strip()
    }
```

### Phase 5: Frontend Integration (Right Panel)

#### 5.1 Chat Interface Component
```typescript
// frontend/app/route-visualization/components/RightPanel.tsx
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
}

export function RightPanel({ onHighlightEdge }: { onHighlightEdge: (edge: any) => void }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

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
      if (response.intent_type === 'find_highlight' && response.highlight_edge) {
        onHighlightEdge(response.highlight_edge);
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.analysis_result || '분석 완료',
        chart_type: response.chart_type,
        chart_data: response.chart_data,
        highlight_edge: response.highlight_edge,
        intent_type: response.intent_type
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: '오류가 발생했습니다. 다시 시도해주세요.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-white">Analytics Chat</h2>
        <p className="text-sm text-gray-400 mt-1">버스 노선 데이터 분석 및 질의</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">💬</p>
              <p>질문을 입력하여 분석을 시작하세요</p>
              <div className="mt-4 text-sm text-gray-600">
                <p>예시:</p>
                <ul className="mt-2 space-y-1">
                  <li>• 가장 포화가 많은 노선은?</li>
                  <li>• 월별 운행 단가 추이를 보여줘</li>
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
                <div className="flex justify-end">
                  <div className="bg-blue-600 text-white rounded-lg px-4 py-2 max-w-[80%]">
                    {msg.content}
                  </div>
                </div>
              )}

              {/* Assistant message */}
              {msg.role === 'assistant' && (
                <div className="flex justify-start">
                  <div className="bg-gray-800 rounded-lg p-4 max-w-[90%] w-full">
                    {/* Find/Highlight response */}
                    {msg.intent_type === 'find_highlight' && msg.highlight_edge && (
                      <div className="mb-4 p-3 bg-green-900/30 border border-green-700 rounded">
                        <p className="text-green-200 text-sm mb-2">
                          🎯 하이라이트: {msg.highlight_edge.label}
                        </p>
                        <p className="text-gray-300 text-sm">{msg.content}</p>
                      </div>
                    )}

                    {/* Analysis response */}
                    {msg.intent_type === 'analysis' && msg.chart_type && (
                      <AnalyticsOutputRenderer
                        chartType={msg.chart_type}
                        chartData={msg.chart_data}
                        analysisResult={msg.content}
                        renderHint={{
                          insights: [], // LLM에서 추출 가능
                          chart_config: {} // 차트 설정
                        }}
                      />
                    )}

                    {/* Fallback text */}
                    {!msg.chart_type && !msg.highlight_edge && (
                      <p className="text-gray-200">{msg.content}</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-lg px-4 py-2">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !loading && handleSend()}
            placeholder="질문을 입력하세요..."
            disabled={loading}
            className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white rounded-lg px-6 py-3 font-medium transition-colors"
          >
            전송
          </button>
        </div>
      </div>
    </div>
  );
}
```

#### 5.2 Output Renderer Integration

기존 chart renderer 활용:
- `TextWithLineChartRenderer.tsx`: Line chart + insights
- `TextWithBarChartRenderer.tsx`: Bar chart + ranking analysis
- `TextWithTableRenderer.tsx`: Data table + statistics
- `DetailTextRenderer.tsx`: Text summary + key points

```typescript
// frontend/app/route-visualization/components/AnalyticsOutputRenderer.tsx
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
```

#### 5.3 API Client
```typescript
// frontend/app/route-visualization/utils/analytics-api.ts
export async function sendMessage(question: string) {
  const response = await fetch('/api/analytics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question })
  });

  if (!response.ok) {
    throw new Error('Failed to analyze');
  }

  return response.json();
}
```

#### 5.4 Backend FastAPI Setup

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import analytics

app = FastAPI(
    title="Smartway Analytics API",
    description="버스 노선 분석 및 시각화 API",
    version="1.0.0"
)

# CORS 설정 (Next.js와 통신)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes 등록
app.include_router(analytics.router, prefix="/api", tags=["analytics"])

@app.get("/")
async def root():
    return {"message": "Smartway Analytics API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

```python
# backend/config.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def build_chat_model(model: str = "solar-pro", temperature: float = 0.7):
    """LLM 인스턴스 생성"""
    if model == "solar-pro2":
        return ChatOpenAI(
            model="solar-pro2",
            api_key=UPSTAGE_API_KEY,
            base_url="https://api.upstage.ai/v1/solar",
            temperature=temperature
        )
    return ChatOpenAI(
        model="solar-pro",
        api_key=UPSTAGE_API_KEY,
        base_url="https://api.upstage.ai/v1/solar",
        temperature=temperature
    )
```

```python
# backend/api/routes/analytics.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from langchain_core.messages import HumanMessage
from analytics.graph.analytics_graph import get_analytics_graph

router = APIRouter()

class QuestionRequest(BaseModel):
    question: str

class AnalyticsResponse(BaseModel):
    intent_type: str
    highlight_edge: Optional[Dict[str, Any]] = None
    chart_data: Optional[Dict[str, Any]] = None
    analysis_result: Optional[str] = None
    chart_type: Optional[str] = None

@router.post("/analytics", response_model=AnalyticsResponse)
async def analyze(request: QuestionRequest):
    """
    Analytics Agent API - LangGraph 실행

    Flow:
    1. 사용자 질문을 HumanMessage로 변환
    2. LangGraph invoke로 실행
    3. 결과 state에서 응답 추출
    4. FastAPI response model로 반환

    Example:
        POST /api/analytics
        Body: {"question": "가장 포화가 많은 노선은?"}
        Response: {
            "intent_type": "find_highlight",
            "highlight_edge": {...},
            "analysis_result": "..."
        }
    """
    try:
        # LangGraph 인스턴스 가져오기
        analytics_graph = get_analytics_graph()

        # Initial state 구성 (LangGraph 형식)
        initial_state = {
            "messages": [HumanMessage(content=request.question)]
        }

        # LangGraph 실행
        print(f"📨 Received question: {request.question}")
        result = analytics_graph.invoke(initial_state)
        print(f"✅ LangGraph execution completed")

        # State에서 결과 추출
        response_data = AnalyticsResponse(
            intent_type=result.get("intent_type", "fallback"),
            highlight_edge=result.get("highlight_edge"),
            chart_data=result.get("chart_data"),
            analysis_result=result.get("analysis_result"),
            chart_type=result.get("chart_type")
        )

        return response_data

    except Exception as e:
        print(f"❌ Error in analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "analytics service healthy"}
```

### Phase 6: Edge Highlighting Integration

```typescript
// frontend/app/route-visualization/ocel-demo/route-flow.tsx
export function RouteFlow({ highlightedEdge }: { highlightedEdge?: any }) {
  const [edges, setEdges] = useState<Edge[]>(initialEdges);

  useEffect(() => {
    if (highlightedEdge) {
      setEdges(edges =>
        edges.map(edge => ({
          ...edge,
          animated: edge.id === highlightedEdge.id,
          style: {
            ...edge.style,
            stroke: edge.id === highlightedEdge.id ? '#ef4444' : '#94a3b8',
            strokeWidth: edge.id === highlightedEdge.id ? 3 : 2
          }
        }))
      );
    }
  }, [highlightedEdge]);

  return <ReactFlow nodes={nodes} edges={edges} />;
}
```

## Example Queries & Expected Responses

### Find/Highlight Examples

| 질문 | Intent | Output |
|-----|--------|--------|
| "가장 포화가 많은 노선은?" | find_highlight | 승차 인원이 가장 많은 edge 하이라이팅 |
| "BYC 사거리에서 업스테이지로 가는 경로는?" | find_highlight | 해당 노드 간 edge 하이라이팅 |
| "운행 단가가 가장 높은 노선은?" | find_highlight | 통근수당 데이터 기반 edge 하이라이팅 |

### Analysis Examples

| 질문 | Chart Type | Output |
|-----|-----------|--------|
| "월별 운행 단가 현황 알려줘" | line_chart | 시계열 라인 차트 |
| "노선별 수익률 비교해줘" | bar_chart | 노선별 바 차트 |
| "지급 수당이 가장 높은 노선은?" | table | 정렬된 테이블 |
| "야간 수당 분석 결과 요약해줘" | text_summary | 텍스트 요약 |

## File Structure

```
smartway-dev/
├── backend/                    # FastAPI Backend
│   ├── main.py                # FastAPI app entry point
│   ├── config.py              # Configuration (API keys, settings)
│   ├── requirements.txt       # Python dependencies
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── types/
│   │   │   ├── __init__.py
│   │   │   └── state_types.py
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── find_highlight.py
│   │   │   └── analysis.py
│   │   └── graph/
│   │       ├── __init__.py
│   │       └── analytics_graph.py
│   └── api/
│       ├── __init__.py
│       └── routes/
│           ├── __init__.py
│           └── analytics.py
│
├── data/                      # Shared data directory
│   ├── reactflow_graph_route_stop.json
│   ├── 승하차정보.json
│   └── 통근수당.json
│
└── frontend/                  # Next.js Frontend
    └── app/
        └── route-visualization/
            ├── page.tsx (updated with RightPanel)
            ├── components/
            │   ├── RightPanel.tsx
            │   ├── ChatMessage.tsx
            │   ├── ChartRenderer.tsx
            │   └── ... (existing components)
            └── utils/
                └── analytics-api.ts
```

## Dependencies

### Backend (FastAPI)
```txt
# requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0

langgraph==0.2.0
langchain-openai==0.1.0
langchain-core==0.1.0

python-multipart==0.0.6
```

### Frontend
기존 chart renderer가 이미 설치되어 있으므로 추가 설치 불필요.

확인 필요한 의존성:
```bash
# 이미 설치되어 있어야 함
# - @/lib/types (Message 타입)
# - @/components/charts/ChartRenderer
# - @/components/charts/DataTable
# - @/components/ui/button
```

### Environment Setup
```bash
# backend/.env
UPSTAGE_API_KEY=your_api_key_here
OPENAI_API_KEY=your_api_key_here  # if needed
ENVIRONMENT=development
```

## Testing Strategy

### Unit Tests
- `router.py`: Intent classification accuracy
- `find_highlight.py`: Edge selection logic
- `analysis.py`: Chart type selection logic

### Integration Tests
- Full graph execution with sample questions
- API endpoint response validation
- Frontend-backend communication

### Example Test Cases
```python
# test_router.py
def test_find_highlight_intent():
    state = {"messages": [{"content": "가장 포화가 많은 노선은?"}]}
    result = intent_analyzer(state)
    assert result["intent_type"] == "find_highlight"

def test_analysis_intent():
    state = {"messages": [{"content": "월별 운행 단가 현황"}]}
    result = intent_analyzer(state)
    assert result["intent_type"] == "analysis"
```

## Success Metrics

1. **Accuracy**: Intent classification ≥90%
2. **Response Time**: < 3 seconds for analysis
3. **Chart Quality**: Correct chart type selection ≥85%
4. **Highlight Accuracy**: Correct edge selection ≥90%
5. **User Experience**: Smooth chat interface, no lag

## Timeline Estimate

- Phase 1 (State & Router): 2-3 hours
- Phase 2 (Find/Highlight): 3-4 hours
- Phase 3 (Analysis): 4-5 hours
- Phase 4 (Graph): 1-2 hours
- Phase 5 (Frontend): 4-5 hours
- Phase 6 (Integration): 2-3 hours
- Testing: 2-3 hours

**Total**: 18-25 hours for full implementation

## Quick Start Guide

### Backend Setup
```bash
# 1. Create backend directory
mkdir backend && cd backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
echo "UPSTAGE_API_KEY=your_key_here" > .env

# 5. Run FastAPI server
python main.py
# Server running at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend Setup
```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install react-chartjs-2 chart.js

# 3. Update Next.js config (if needed)
# Add proxy to backend in next.config.js

# 4. Run dev server
npm run dev
# Server running at http://localhost:3000
```

### Testing the API
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test analytics endpoint
curl -X POST http://localhost:8000/api/analytics \
  -H "Content-Type: application/json" \
  -d '{"question": "가장 포화가 많은 노선은?"}'
```

## Next Steps

1. ✅ Create specification document
2. ⬜ Setup FastAPI backend structure
3. ⬜ Implement LangGraph nodes
4. ⬜ Create FastAPI routes
5. ⬜ Develop frontend RightPanel
6. ⬜ Integrate with RouteFlow
7. ⬜ Test with real data
8. ⬜ Deploy and monitor
