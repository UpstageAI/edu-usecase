"""
Analysis Path Nodes

버스 데이터를 로드하고 차트 타입을 선택한 후 분석을 수행하는 노드들
"""
import json
import os
from analytics.types.state_types import AnalyticsState
from config import build_chat_model
from langchain_core.messages import SystemMessage


def get_bus_data(state: AnalyticsState):
    """
    버스 데이터 로드 (LangGraph Node)

    - 승하차정보.json
    - 통근수당.json

    Args:
        state (AnalyticsState): 현재 그래프의 상태

    Returns:
        dict: 업데이트할 상태 {"transport_data": "...", "commute_allowance_data": "..."}
    """
    try:
        # 파일 경로 설정 (프로젝트 루트 기준)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

        transport_path = os.path.join(project_root, "data", "승하차정보.json")
        commute_path = os.path.join(project_root, "data", "통근수당.json")

        print(f"📂 Loading transport data from: {transport_path}")
        print(f"📂 Loading commute data from: {commute_path}")

        # 승하차 정보 로드
        with open(transport_path, 'r', encoding='utf-8') as f:
            transport_data = json.load(f)

        # 통근 수당 로드
        with open(commute_path, 'r', encoding='utf-8') as f:
            commute_data = json.load(f)

        print(f"✅ 승하차 정보 {len(transport_data)}건 로드 완료")
        print(f"✅ 통근 수당 정보 {len(commute_data)}건 로드 완료")

        return {
            "transport_data": json.dumps(transport_data, ensure_ascii=False),
            "commute_allowance_data": json.dumps(commute_data, ensure_ascii=False)
        }
    except Exception as e:
        error_msg = f"❌ 버스 데이터 로드 중 오류: {str(e)}"
        print(error_msg)
        return {
            "transport_data": "[]",
            "commute_allowance_data": "[]"
        }


def chart_type_selector(state: AnalyticsState):
    """
    사용자 질문에 적합한 차트 타입 선택 (LangGraph Node)

    Args:
        state (AnalyticsState): 현재 그래프의 상태

    Returns:
        dict: 업데이트할 상태 {"chart_type": "line_chart" | "bar_chart" | "table" | "text_summary"}

    Chart Types:
    - line_chart: 시계열 추이, 변화 분석
    - bar_chart: 비교, 순위, 노선별 비교
    - table: 상세 데이터, 전체 목록
    - text_summary: 요약, 설명
    """
    user_message = state["messages"][-1]
    user_question = user_message.content if hasattr(user_message, 'content') else str(user_message)

    system_prompt = """
당신은 차트 타입 선택 전문가입니다.

사용자 질문을 분석하여 가장 적합한 차트 타입을 선택하세요.

선택 가능한 차트 타입:
1. **line_chart**: 시계열 추이, 변화, 트렌드 분석
   - 키워드: "추이", "변화", "월별", "시간별", "트렌드"
   - 예시: "월별 운행 단가 추이를 보여줘"

2. **bar_chart**: 비교, 순위, 노선별 비교
   - 키워드: "비교", "노선별", "순위", "상위", "하위"
   - 예시: "노선별 수익률 비교해줘"

3. **table**: 상세 데이터, 전체 목록
   - 키워드: "상세", "목록", "전체", "데이터"
   - 예시: "전체 노선 데이터 보여줘"

4. **text_summary**: 요약, 설명, 분석 결과
   - 키워드: "요약", "설명", "분석 결과"
   - 예시: "야간 수당 분석 결과 요약해줘"

응답: 차트 타입만 영어로 출력 (추가 설명 금지)
출력 예시: line_chart
"""

    messages = [
        SystemMessage(content=system_prompt),
        user_message
    ]

    # LLM 호출
    llm = build_chat_model(temperature=0.3)
    response = llm.invoke(messages)

    chart_type = response.content.strip()

    # 유효성 검증
    valid_types = ["line_chart", "bar_chart", "table", "text_summary"]
    if chart_type not in valid_types:
        print(f"⚠️  Invalid chart type: {chart_type}, defaulting to text_summary")
        chart_type = "text_summary"

    print(f"📊 Chart Type Selected: {chart_type}")

    return {
        "chart_type": chart_type,
        "messages": state["messages"] + [response]
    }


def generate_analytic(state: AnalyticsState):
    """
    Solar Pro2를 사용하여 데이터 분석 및 차트 데이터 생성 (LangGraph Node)

    Args:
        state (AnalyticsState): 현재 그래프의 상태

    Returns:
        dict: 업데이트할 상태 {"chart_data": {...}, "analysis_result": "...", "messages": [...]}
    """
    user_question = state["messages"][0].content if hasattr(state["messages"][0], 'content') else str(state["messages"][0])
    chart_type = state.get("chart_type", "text_summary")
    transport_data = state.get("transport_data", "")
    commute_data = state.get("commute_allowance_data", "")

    print(f"🔬 Generating analytics for: {chart_type}")

    # 차트별 output format 정의
    output_formats = {
        "line_chart": """
{
    "chart_data": {
        "labels": ["January", "February", "March", ...],
        "datasets": [{
            "label": "Dataset Label",
            "data": [65, 59, 80, ...],
            "borderColor": "rgb(75, 192, 192)",
            "tension": 0.1
        }]
    },
    "insights": [
        "1월부터 3월까지 데이터가 지속적으로 상승하는 추세를 보이며, 특히 2월에 가장 큰 증가폭을 기록했습니다.",
        "전체 기간 동안 평균 70 수준을 유지하고 있으며, 계절적 변동성이 관찰됩니다.",
        "향후 이러한 상승 추세가 계속될 것으로 예상되며, 4월에는 85를 넘어설 가능성이 있습니다."
    ],
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
            "backgroundColor": "rgba(59, 130, 246, 0.6)",
            "borderColor": "rgb(59, 130, 246)",
            "borderWidth": 1
        }]
    },
    "insights": [
        "출근1호 노선이 73,000원으로 가장 높은 운행단가를 기록했으며, 이는 평균 대비 약 15% 높은 수준입니다.",
        "노선별 운행단가 편차가 크게 나타나고 있으며, 가장 높은 노선과 낮은 노선 간 약 20,000원의 차이를 보입니다.",
        "운행단가가 높은 노선들은 주로 장거리 운행 구간을 포함하고 있어 연료비와 시간 비용이 많이 발생하는 것으로 분석됩니다."
    ],
    "reason": "분석 결과 설명"
}
        """,
        "table": """
{
    "chart_data": {
        "columns": ["노선명", "운행단가", "지급수당"],
        "rows": [
            ["출근1호-한국대서문", 73000, 10000],
            ["출근2호-한국전자기술연구원", 68000, 10000],
            ...
        ]
    },
    "insights": [
        "전체 8개 노선 중 출퇴근 노선이 6개로 대부분을 차지하며, 모든 노선의 지급수당은 동일하게 10,000원으로 책정되어 있습니다.",
        "운행단가는 노선의 거리와 소요 시간에 비례하여 책정되며, 최소 53,000원부터 최대 73,000원까지 분포하고 있습니다.",
        "평균 운행단가는 약 65,000원 수준이며, 출근 노선이 퇴근 노선보다 평균적으로 약 5,000원 더 높은 것으로 나타났습니다."
    ],
    "reason": "분석 결과 설명"
}
        """,
        "text_summary": """
{
    "chart_data": null,
    "insights": [
        "전체 데이터를 분석한 결과, 주요 패턴과 트렌드가 명확하게 나타났으며 예상 범위 내에서 움직이고 있습니다.",
        "특정 구간에서 이상치가 발견되었으나 전체적인 데이터 품질은 양호하며, 추가적인 조사가 필요한 부분은 제한적입니다.",
        "향후 지속적인 모니터링을 통해 추세 변화를 감지하고, 필요시 개선 조치를 취하는 것이 권장됩니다."
    ],
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

중요 지침:
1. insights는 반드시 완전한 문장으로 작성하세요 (주어, 서술어 포함).
2. 각 insight는 구체적인 수치와 분석 내용을 포함해야 합니다.
3. insights는 3개의 문장으로 구성되며, 각 문장은 마침표로 끝납니다.
4. "핵심 통찰 1:", "•" 같은 불릿 포인트나 번호는 사용하지 마세요.

Output Format:
{output_formats[chart_type]}
"""

    # Solar Pro2 LLM 호출
    llm = build_chat_model(model="solar-pro2", temperature=0.5)
    response = llm.invoke([SystemMessage(content=system_prompt)])

    try:
        # JSON 파싱
        content = response.content.strip()

        # ```json 블록 제거
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        result = json.loads(content)

        print(f"✅ 분석 완료")
        print(f"   - insights: {len(result.get('insights', []))}개")

        return {
            "chart_data": result.get("chart_data"),
            "analysis_result": result.get("reason", ""),
            "insights": result.get("insights", []),
            "messages": state["messages"] + [response]
        }
    except json.JSONDecodeError as e:
        print(f"⚠️  분석 결과 JSON 파싱 실패: {str(e)}")
        print(f"   Raw content: {response.content[:200]}")
        return {
            "analysis_result": response.content,
            "messages": state["messages"] + [response]
        }
