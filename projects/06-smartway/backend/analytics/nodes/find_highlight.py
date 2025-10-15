"""
Find/Highlight Path Nodes

그래프 데이터를 로드하고 LLM을 사용하여 엣지를 선택하는 노드들
"""
import json
import os
from analytics.types.state_types import AnalyticsState
from config import build_chat_model
from langchain_core.messages import SystemMessage


def get_graph_data(state: AnalyticsState):
    """
    ReactFlow 그래프 데이터를 JSON 파일에서 로드하는 노드 (LangGraph Node)

    Args:
        state (AnalyticsState): 현재 그래프의 상태

    Returns:
        dict: 업데이트할 상태 {"graph_data": {노드와 엣지 정보}}

    동작 과정:
    1. data/reactflow_graph_route_stop.json 파일 경로 설정
    2. JSON 파일을 읽어서 파싱
    3. LLM이 이해하기 쉬운 형태로 데이터 구조화
    4. state에 graph_data로 저장

    데이터 구조:
    - nodes: 노드 리스트 (id, type, label 등)
    - edges: 엣지 리스트 (source, target, label 등)
    - summary: 그래프 요약 정보 (노드 수, 엣지 수 등)
    """
    try:
        # 1. JSON 파일 경로 설정 (프로젝트 루트 기준)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        json_path = os.path.join(project_root, "frontend", "public", "reactflow_graph.json")

        print(f"📂 Loading graph data from: {json_path}")

        # 2. JSON 파일 읽기
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # 3. LLM이 이해하기 쉬운 형태로 데이터 구조화
        # 노드 정보 추출 및 정리
        nodes = []
        for node in raw_data.get("nodes", []):
            node_info = {
                "id": node.get("id"),
                "type": node.get("type"),
                "label": node.get("data", {}).get("label", "")
            }
            # 추가 데이터가 있으면 포함
            if "position" in node:
                node_info["position"] = node["position"]
            if "parentId" in node:
                node_info["parentId"] = node["parentId"]
            nodes.append(node_info)

        # 엣지 정보 추출 및 정리
        edges = []
        for edge in raw_data.get("edges", []):
            edge_info = {
                "id": edge.get("id"),
                "source": edge.get("source"),
                "target": edge.get("target"),
                "label": edge.get("label", "")
            }
            edges.append(edge_info)

        # 4. 그래프 요약 정보 생성
        summary = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_types": list(set(node.get("type") for node in nodes if node.get("type"))),
            "description": "버스 노선과 정류장 정보를 담은 ReactFlow 그래프 데이터"
        }

        # 5. 구조화된 데이터 생성
        structured_data = {
            "summary": summary,
            "nodes": nodes,
            "edges": edges,
            "raw_data": raw_data  # 필요시 원본 데이터도 포함
        }

        print(f"✅ 그래프 데이터 로드 완료: {summary['total_nodes']}개 노드, {summary['total_edges']}개 엣지")

        # 6. state 업데이트
        return {"graph_data": structured_data}

    except FileNotFoundError:
        error_msg = f"❌ 파일을 찾을 수 없습니다: {json_path}"
        print(error_msg)
        return {"graph_data": {"error": error_msg}}
    except json.JSONDecodeError as e:
        error_msg = f"❌ JSON 파싱 오류: {str(e)}"
        print(error_msg)
        return {"graph_data": {"error": error_msg}}
    except Exception as e:
        error_msg = f"❌ 데이터 로드 중 오류 발생: {str(e)}"
        print(error_msg)
        return {"graph_data": {"error": error_msg}}


def select_edge(state: AnalyticsState):
    """
    LLM을 사용하여 사용자 질문에 맞는 엣지 선택 (LangGraph Node)

    Args:
        state (AnalyticsState): 현재 그래프의 상태 (메시지 리스트 및 그래프 데이터 포함)

    Returns:
        dict: 업데이트할 상태 {"messages": [AI 응답], "highlight_edge": {...}, "analysis_result": "..."}

    동작 과정:
    1. state에서 graph_data 가져오기
    2. 그래프 데이터를 JSON 형태로 컨텍스트에 포함
    3. build_chat_model()로 LLM 인스턴스 생성
    4. 사용자 메시지 + 그래프 컨텍스트를 LLM에 전달하여 응답 생성
    5. 생성된 응답을 messages 리스트에 추가
    6. LLM이 선택한 엣지를 원본 데이터 구조 형태로 출력

    예시 질문:
    - "가장 포화가 많은 노선은?"
    - "BYC 사거리에서 업스테이지로 가는 경로는?"
    """
    print("🔍 select_edge 노드 실행 중...")

    # 1. 그래프 데이터 가져오기
    graph_data = state.get("graph_data", {})

    # 2. 그래프 데이터를 JSON 형태로 컨텍스트 변환
    context_message = ""
    if graph_data and "error" not in graph_data:
        summary = graph_data.get("summary", {})
        edges = graph_data.get("edges", [])
        nodes = graph_data.get("nodes", [])

        # JSON 형태로 edges 데이터 구조 포함
        edges_json = json.dumps(edges, ensure_ascii=False, indent=2)

        # 노드 정보도 제공 (정류장 상세 정보)
        nodes_json = json.dumps(nodes, ensure_ascii=False, indent=2)

        # 그래프 정보를 텍스트로 구성
        context_message = f"""
[그래프 데이터 컨텍스트]
- 총 노드 수: {summary.get('total_nodes', 0)}개
- 총 엣지 수: {summary.get('total_edges', 0)}개
- 노드 타입: {', '.join(summary.get('node_types', []))}
- 설명: {summary.get('description', '')}

[노드 데이터 (정류장 상세 정보)]
각 노드는 다음 정보를 포함합니다:
- id: 노드의 고유 ID
- data.label: 정류장 이름과 순서 (예: "1. 한국대 동문 버스정류장")
- data.route: 노선명
- data.stopName: 정류장 이름
- data.departTime: 출발 시간
- data.busNo: 버스 번호

{nodes_json}

[엣지 데이터 (승하차 정보)]
각 엣지는 다음 정보를 포함합니다:
- id: 엣지의 고유 ID
- source: 출발 정류장 ID
- target: 도착 정류장 ID
- label: 엣지 라벨 (예: "승차 21" - 숫자는 승차 인원수)
- data.count: 실제 승차/하차 인원수 (포화도를 판단하는 핵심 지표)
- data.action: "승차" 또는 "하차"

{edges_json}

중요:
- "가장 포화가 많은 노선"은 data.count 값이 가장 큰 엣지를 의미합니다.
- label의 "승차 X" 에서 X는 data.count와 동일한 승차 인원수입니다.
- 위 데이터를 분석하여 사용자 질문에 가장 적합한 엣지 1개를 선택하세요.

응답 형식: 아래의 output format에 맞춰 선택한 엣지 정보를 JSON으로 출력해줘, 이외에 절대 다른 내용은 출력하지 말아줘.
참고 정보도 보여주지말고 딱 JSON만 보여줘. 데이터 재확인 과정이나 추가적인 설명은 절대 보여주지말고 최종 json 결과만 보여줘.

output format:
{{
    "highlight": {{
        "id": "엣지ID",
        "source": "출발노드ID",
        "target": "도착노드ID",
        "label": "엣지라벨"
    }},
    "reason": "엣지를 선택한 이유를 상세하게 설명해주세요. 다음 내용을 포함하세요:\n1. 선택된 엣지의 승차/하차 인원수\n2. 전체 엣지 중 몇 번째로 포화도가 높은지\n3. 해당 노선의 특징 (출발지, 도착지 정보 포함)\n4. 포화도가 높은 이유 추론 (시간대, 위치 등)\n\n예시: '출근2호 노선의 첫 번째 정류장에서 두 번째 정류장으로 가는 구간에서 21명이 승차하여 전체 엣지 중 가장 높은 포화도를 기록했습니다. 원평공영주차장 맞은편 정류장은 주거 지역에 위치하여 출근 시간대(7:20)에 많은 승객이 집중되는 것으로 보입니다. 전체 37개 엣지 중 1위에 해당하며, 2위 대비 약 X명 더 많은 인원이 승차했습니다.'"
}}
"""

        print(f"📊 그래프 컨텍스트 포함: {summary.get('total_nodes', 0)}개 노드, {summary.get('total_edges', 0)}개 엣지")
    else:
        context_message = "[그래프 데이터를 로드하지 못했습니다. 일반적인 질문에 대해서만 답변할 수 있습니다.]"
        print("⚠️  그래프 데이터 없이 실행")

    # 3. LLM 인스턴스 생성 (높은 temperature로 더 상세한 분석 생성)
    llm = build_chat_model(temperature=0.8)

    # 4. 기존 메시지에 컨텍스트 추가
    messages = state["messages"].copy()

    # 시스템 메시지로 컨텍스트 추가 (첫 번째 위치에)
    messages.insert(0, SystemMessage(content=context_message))

    # 5. LLM 호출 및 응답 반환
    response = llm.invoke(messages)

    # 6. 응답에서 highlight_edge 추출
    try:
        result = json.loads(response.content.strip())
        highlight_edge = result.get("highlight", {})
        reason = result.get("reason", "")

        print(f"✅ 엣지 선택 완료: {highlight_edge.get('label', 'N/A')}")

        return {
            "messages": [response],
            "highlight_edge": highlight_edge,
            "analysis_result": reason
        }
    except json.JSONDecodeError:
        print("⚠️  응답 JSON 파싱 실패")
        return {
            "messages": [response],
            "analysis_result": response.content
        }
