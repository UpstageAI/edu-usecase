# main.py

import os
import asyncio
import json # Dispatcher의 결과(문자열)를 파싱하기 위해 import
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai.llm import LLM

load_dotenv()

# --- LLM 정의 ---
llm = LLM(
    model="huggingface/meta-llama/Meta-Llama-3-8B-Instruct",
    api_key=os.getenv("HUGGINGFACEHUB_API_TOKEN")
)

# --- RAG 함수 정의 ---
def get_context_for_topic(proposal_file, topic):
    print(f"INFO: '{proposal_file}'에서 '{topic}'에 대한 RAG 검색 중...")
    return f"'{proposal_file}'의 '{topic}' 관련 내용입니다. (가상 RAG 결과)"

async def main():
    print("## Dispatcher Agent 기반 동적 평가 프로세스를 시작합니다.")

    # 1. 고정된 전문가 에이전트들을 미리 정의합니다.
    technical_agent = Agent(
        role='IT 제안서 기술 분석가',
        goal='할당된 기술 관련 심사 항목들을 평가하고 보고서를 작성',
        backstory='당신은 기술 아키텍처, 성능, 보안 등 기술적 측면을 평가하는 전문가입니다.',
        llm=llm, verbose=True
    )

    management_agent = Agent(
        role='IT 제안서 사업수행 및 관리 역량 분석가',
        goal='할당된 관리 관련 심사 항목들을 평가하고 보고서를 작성',
        backstory='당신은 프로젝트 관리, 인력 구성, 예산 등 사업 관리 측면을 평가하는 전문가입니다.',
        llm=llm, verbose=True
    )

    # 2. 오늘의 전체 심사 항목 리스트 (섞여있음)
    unstructured_evaluation_items = [
        {"topic": "시스템 아키텍처", "criteria": "MSA 기반의 유연하고 확장 가능한 아키텍처인가?"},
        {"topic": "프로젝트 관리 방안", "criteria": "WBS 기반의 상세하고 실현 가능한 일정을 제시하였는가?"},
        {"topic": "데이터베이스 암호화", "criteria": "개인정보보호 및 데이터 암호화 방안이 명시되었는가?"},
        {"topic": "투입 인력 계획", "criteria": "투입 인력의 역할과 경력이 적절한가?"},
        # ... 여기에 어떤 항목이 몇 개가 들어와도 상관 없습니다.
    ]

    # =================================================================
    # Phase 1: Dispatcher Agent를 통해 심사 항목 분류하기
    # =================================================================
    print("\n--- [Phase 1] Dispatcher Agent가 심사 항목을 분류합니다 ---")
    
    # 3. Dispatcher(작업 분배) 역할을 할 에이전트 정의
    dispatcher_agent = Agent(
        role="평가 항목 분류 매니저",
        goal="주어진 심사 항목 리스트를 분석하여 각 항목이 어떤 유형('technical', 'management')에 속하는지 분류",
        backstory="당신은 여러 전문가 팀의 작업을 효율적으로 분배하는 역할을 맡은 프로젝트 매니저입니다. 각 항목의 핵심을 파악하여 정확한 담당자에게 전달해야 합니다.",
        llm=llm,
        verbose=True
    )

    # 4. Dispatcher에게 분류 작업을 지시하는 Task 생성
    # json.dumps를 사용하여 파이썬 리스트를 문자열로 변환하여 전달
    items_as_string = json.dumps(unstructured_evaluation_items, ensure_ascii=False)
    
    dispatcher_task = Task(
        description=f"""아래는 오늘 평가해야 할 전체 심사 항목 리스트입니다.
        각 항목을 읽고, 그 내용이 'technical'(기술) 또는 'management'(관리) 중 어느 분야에 더 가까운지 판단하여 분류해주세요.

        [전체 심사 항목 리스트]
        {items_as_string}

        결과는 반드시 아래와 같은 JSON 형식으로만 응답해야 합니다. 다른 어떤 설명도 추가하지 마세요.
        {{
          "technical": [{{항목1}}, {{항목2}}, ...],
          "management": [{{항목3}}, {{항목4}}, ...]
        }}
        """,
        expected_output="'technical'과 'management' 두 개의 키를 가진 JSON 객체. 각 키의 값은 분류된 심사 항목 객체들의 리스트입니다.",
        agent=dispatcher_agent
    )

    # 5. 분류 작업을 위한 임시 Crew 실행
    dispatcher_crew = Crew(agents=[dispatcher_agent], tasks=[dispatcher_task], verbose=False)
    categorization_result = dispatcher_crew.kickoff()

    # 6. Dispatcher의 결과(JSON 문자열)를 파이썬 딕셔너리로 변환
    try:
        # 👈 categorization_result 객체 안의 .raw 속성(순수 텍스트)을 전달
        categorized_items = json.loads(categorization_result.raw)
        print("✅ 항목 분류 완료:")
        print(f"  - 기술 항목: {len(categorized_items.get('technical', []))}개")
        print(f"  - 관리 항목: {len(categorized_items.get('management', []))}개")
    except json.JSONDecodeError:
        print("❌ 항목 분류 실패! Dispatcher가 JSON 형식으로 응답하지 않았습니다.")
        categorized_items = {'technical': [], 'management': []} # 실패 시 빈 리스트로 처리


    # =================================================================
    # Phase 2: 분류된 항목을 전문가들에게 할당하여 병렬 평가
    # =================================================================
    print("\n--- [Phase 2] 전문가 Agent들이 분류된 항목을 병렬로 평가합니다 ---")
    
    evaluation_tasks = []

    # 7. 분류된 기술 항목들에 대해 Task 생성 및 'technical_agent'에게 할당
    for item in categorized_items.get('technical', []):
        context = get_context_for_topic("A사_제안서.pdf", item['topic'])
        task = Task(
            description=f"기술 항목 '{item['topic']}'을 평가하시오.\n- 심사 기준: {item['criteria']}\n- 관련 내용: {context}",
            expected_output="평가 점수, 요약문, 근거가 포함된 기술 평가 보고서",
            agent=technical_agent
        )
        evaluation_tasks.append(task)

    # 8. 분류된 관리 항목들에 대해 Task 생성 및 'management_agent'에게 할당
    for item in categorized_items.get('management', []):
        context = get_context_for_topic("A사_제안서.pdf", item['topic'])
        task = Task(
            description=f"관리 항목 '{item['topic']}'을 평가하시오.\n- 심사 기준: {item['criteria']}\n- 관련 내용: {context}",
            expected_output="평가 점수, 요약문, 근거가 포함된 관리 평가 보고서",
            agent=management_agent
        )
        evaluation_tasks.append(task)

    # 9. 최종 평가 Crew를 구성하고 병렬 실행
    if evaluation_tasks:
        evaluation_crew = Crew(
            agents=[technical_agent, management_agent],
            tasks=evaluation_tasks,
            verbose=True
        )
        final_results = await evaluation_crew.kickoff_async()

        print("\n\n--- [Phase 2] 개별 평가 완료 ---")
        # 개별 결과 확인용 출력
        for result in final_results:
            print(result)
            print("-" * 20)

        # =================================================================
        # Phase 3: 개별 결과들을 종합하여 최종 보고서 작성하기
        # =================================================================
        print("\n--- [Phase 3] Reporting Agent가 최종 보고서를 작성합니다 ---")

        # 1. 이전 단계(Phase 2)의 모든 결과들을 하나의 문자열로 합칩니다.
        individual_reports = "\n\n".join([str(result) for result in final_results])

        # 2. 보고서 작성(종합) 역할을 할 에이전트 정의
        reporting_agent = Agent(
            role="수석 평가 분석가 (Chief Evaluation Analyst)",
            goal="여러 개의 개별 평가 보고서를 종합하여, 경영진이 의사결정을 내릴 수 있도록 하나의 완성된 최종 보고서를 작성",
            backstory="당신은 여러 부서의 보고를 취합하여 핵심만 요약하고, 전체적인 관점에서 강점과 약점을 분석하여 최종 보고서를 작성하는 데 매우 능숙합니다.",
            llm=llm,
            verbose=True
        )
        
        # 3. 보고서 작성 Task 생성
        reporting_task = Task(
            description=f"""아래는 각 분야 전문가들이 작성한 개별 평가 보고서들입니다.
            
            [개별 평가 보고서 목록]
            {individual_reports}
            
            위 보고서들을 모두 종합하여, 제안서 전체에 대한 최종 평가 보고서를 작성해주세요.
            보고서에는 다음 내용이 반드시 포함되어야 합니다:
            1. 서론: 평가 개요
            2. 종합 의견: 제안서의 핵심적인 강점과 약점에 대한 총평
            3. 항목별 요약: 각 평가 항목(기술, 관리)의 점수와 핵심 내용을 간략히 요약
            4. 최종 결론 및 추천 사항
            """,
            expected_output="서론, 종합 의견, 항목별 요약, 최종 결론이 포함된 완성된 형태의 최종 평가 보고서",
            agent=reporting_agent
        )

        # 4. 보고서 작성을 위한 최종 Crew 실행
        reporting_crew = Crew(
            agents=[reporting_agent],
            tasks=[reporting_task],
            verbose=False # 최종 결과만 깔끔하게 보기 위해 False로 설정
        )
        
        final_comprehensive_report = reporting_crew.kickoff()

        # 5. 최종 종합 보고서 출력
        print("\n\n==========================================")
        print("🚀 최종 종합 평가 보고서")
        print("==========================================")
        print(final_comprehensive_report.raw)
    else:
        print("평가할 작업이 없습니다.")

if __name__ == '__main__':
    asyncio.run(main())