# main.py

import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai.llm import LLM



# HuggingFace 토큰 설정 (.env 파일에서 로드)
# HUGGINGFACEHUB_API_TOKEN을 .env 파일에 설정하세요

llm = LLM(
    model="huggingface/meta-llama/Meta-Llama-3-8B-Instruct",
    api_key=os.getenv("HUGGINGFACEHUB_API_TOKEN")
)

# llm = LLM(
#     model="ollama/llama3.2",
#     base_url="http://localhost:11434"
# )


# --- 유틸리티 함수 정의 ---
def ensure_output_directory():
    """output 폴더가 존재하지 않으면 생성합니다."""
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir

def save_report_to_file(content, filename_prefix, report_type=""):
    """보고서 내용을 타임스탬프가 포함된 파일명으로 저장합니다."""
    output_dir = ensure_output_directory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if report_type:
        filename = f"{filename_prefix}_{report_type}_{timestamp}.txt"
    else:
        filename = f"{filename_prefix}_{timestamp}.txt"
    
    filepath = os.path.join(output_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 보고서가 저장되었습니다: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ 보고서 저장 실패: {str(e)}")
        return None

# --- RAG 함수 정의 ---
def get_context_for_topic(proposal_file, topic):
    print(f"INFO: '{proposal_file}'에서 '{topic}'에 대한 RAG 검색 중...")
    
    # 실제 파일에서 내용을 읽어서 topic과 관련된 부분을 찾아 반환
    try:
        with open(proposal_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 간단한 키워드 기반 검색 (실제 RAG 구현 시 더 정교한 검색 로직 필요)
        lines = content.split('\n')
        relevant_lines = []
        
        # topic과 관련된 키워드들
        topic_keywords = {
            "시스템 아키텍처": ["아키텍처", "시스템 구성", "MSA", "마이크로서비스", "구조"],
            "프로젝트 관리 방안": ["프로젝트", "일정", "WBS", "관리", "계획"],
            "데이터베이스 암호화": ["암호화", "보안", "데이터", "개인정보", "보호"],
            "투입 인력 계획": ["인력", "투입", "역할", "경력", "팀"],
            "비용 산정 내역": ["비용", "예산", "산정", "가격", "금액"]
        }
        
        keywords = topic_keywords.get(topic, [topic])
        
        for line in lines:
            if any(keyword in line for keyword in keywords):
                relevant_lines.append(line.strip())
        
        if relevant_lines:
            return f"'{proposal_file}'의 '{topic}' 관련 내용:\n" + "\n".join(relevant_lines[:10])  # 최대 10줄
        else:
            return f"'{proposal_file}'에서 '{topic}' 관련 내용을 찾을 수 없습니다."
            
    except FileNotFoundError:
        return f"파일 '{proposal_file}'을 찾을 수 없습니다."
    except Exception as e:
        return f"파일 읽기 중 오류 발생: {str(e)}"

async def main():
    print("## 동적 Agent 생성 및 평가 프로세스를 시작합니다.")
    start_time = datetime.now()
    print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 평가할 제안서 파일 목록 (data 폴더의 모든 txt 파일 자동 수집)
    data_dir = "data"
    proposal_files = []
    if os.path.exists(data_dir):
        for file in os.listdir(data_dir):
            if file.endswith('.txt'):
                proposal_files.append(os.path.join(data_dir, file))
        print(f"발견된 제안서 파일: {len(proposal_files)}개")
        for file in proposal_files:
            print(f"  - {file}")
    else:
        print("❌ data 폴더가 존재하지 않습니다.")
        return
    
    if not proposal_files:
        print("❌ data 폴더에 txt 파일이 없습니다.")
        return
    
    # 전체 심사 항목 리스트 (어떤 대분류가 들어올지 모름)
    unstructured_evaluation_items = [
        {"대분류": "기술", "topic": "시스템 아키텍처", "criteria": "MSA 기반의 유연하고 확장 가능한 아키텍처인가?"},
        {"대분류": "관리", "topic": "프로젝트 관리 방안", "criteria": "WBS 기반의 상세하고 실현 가능한 일정을 제시하였는가?"},
        {"대분류": "기술", "topic": "데이터베이스 암호화", "criteria": "개인정보보호 및 데이터 암호화 방안이 명시되었는가?"},
        {"대분류": "관리", "topic": "투입 인력 계획", "criteria": "투입 인력의 역할과 경력이 적절한가?"},
        {"대분류": "가격", "topic": "비용 산정 내역", "criteria": "제시된 비용이 합리적이고 구체적인 근거를 포함하는가?"},
    ]

    # 각 제안서별로 개별 평가 수행
    all_proposal_results = {}
    
    for proposal_file in proposal_files:
        print(f"\n{'='*60}")
        print(f"📄 {proposal_file} 평가 시작...")
        print(f"{'='*60}")
        
        # 해당 제안서에 대한 평가 수행
        proposal_result = await evaluate_single_proposal(proposal_file, unstructured_evaluation_items)
        all_proposal_results[proposal_file] = proposal_result
    
    # 모든 제안서의 결과를 종합하여 최종 비교 보고서 생성
    await generate_comparison_report(all_proposal_results)
    
    # 전체 프로세스 완료 시간 측정
    end_time = datetime.now()
    total_duration = end_time - start_time
    print(f"\n{'='*60}")
    print(f"🏁 전체 프로세스 완료!")
    print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"완료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 소요 시간: {total_duration}")
    print(f"{'='*60}")

async def evaluate_single_proposal(proposal_file, unstructured_evaluation_items):
    """단일 제안서에 대한 평가를 수행합니다."""
    proposal_start_time = datetime.now()
    print(f"제안서 평가 시작 시간: {proposal_start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # =================================================================
    # Phase 1: Dispatcher가 대분류를 스스로 찾아내고 항목 분류
    # =================================================================
    print("\n--- [Phase 1] Dispatcher Agent가 대분류를 식별하고 항목을 분류합니다 ---")
    
    dispatcher_agent = Agent(
        role="평가 항목 자동 분류 및 그룹화 전문가",
        goal="주어진 심사 항목 리스트에서 '대분류'를 기준으로 모든 항목을 그룹화하여 JSON으로 반환",
        backstory="당신은 복잡한 목록을 받아서 주요 카테고리별로 깔끔하게 정리하고 구조화하는 데 매우 뛰어난 능력을 가졌습니다.",
        llm=llm,
        verbose=True
    )

    items_as_string = json.dumps(unstructured_evaluation_items, ensure_ascii=False)
    
    dispatcher_task = Task(
        description=f"""아래 심사 항목 리스트를 분석하여 '대분류' 키 값을 기준으로 그룹화해주세요.
        
        [전체 심사 항목 리스트]
        {items_as_string}

        결과 JSON의 key는 리스트에 존재하는 '대분류'의 이름이어야 합니다.
        예를 들어, 대분류가 '기술'과 '관리'만 있다면 결과는 다음과 같아야 합니다.
        {{
          "기술": [{{'대분류':'기술', ...}}, ...],
          "관리": [{{'대분류':'관리', ...}}, ...]
        }}
        """,
        expected_output="JSON 객체. 각 key는 심사 항목 리스트에 있던 '대분류'이며, value는 해당 대분류에 속하는 항목 객체들의 리스트입니다.",
        agent=dispatcher_agent
    )

    dispatcher_crew = Crew(agents=[dispatcher_agent], tasks=[dispatcher_task], verbose=False)
    categorization_result = dispatcher_crew.kickoff()

    try:
        categorized_items = json.loads(categorization_result.raw)
        print("✅ 항목 분류 완료. 발견된 대분류:")
        for category, items in categorized_items.items():
            print(f"  - {category}: {len(items)}개 항목")
    except json.JSONDecodeError:
        print("❌ 항목 분류 실패!")
        categorized_items = {}


    # =================================================================
    # Phase 2: 대분류 개수만큼 동적으로 Agent를 생성하고 병렬 평가
    # =================================================================
    print("\n--- [Phase 2] 발견된 대분류별로 전문가 Agent를 동적으로 생성하여 병렬 평가합니다 ---")
    
    specialist_agents = []
    evaluation_tasks = []

    # 1. 분류된 결과(딕셔너리)를 순회하며 대분류별로 Agent와 Task를 생성
    for category, items in categorized_items.items():
        
        # 2. 해당 대분류를 위한 전문가 Agent 동적 생성
        specialist_agent = Agent(
            role=f"'{category}' 부문 전문 평가관",
            goal=f"제안서의 '{category}' 부문에 해당하는 모든 심사 항목들을 전문적으로 평가",
            backstory=f"당신은 오직 '{category}' 분야의 평가만을 위해 투입된 최고의 전문가입니다.",
            llm=llm,
            verbose=True
        )
        specialist_agents.append(specialist_agent)

        # 3. 해당 전문가가 수행할 Task들을 생성
        for item in items:
            context = get_context_for_topic(proposal_file, item['topic'])  # 실제 파일명 사용
            task = Task(
                description=f"'{category}' 부문의 '{item['topic']}' 항목을 평가하시오.\n- 심사 기준: {item['criteria']}\n- 관련 내용: {context}",
                expected_output=f"'{item['topic']}'에 대한 평가 점수, 요약문, 근거가 포함된 평가 보고서",
                agent=specialist_agent # 👈 방금 생성한 해당 분야 전문가에게 할당
            )
            evaluation_tasks.append(task)

    # 4. 동적으로 생성된 모든 전문가와 Task들로 최종 평가 Crew 구성 및 실행
    if evaluation_tasks:
        evaluation_crew = Crew(
            agents=specialist_agents, # 동적으로 생성된 Agent 리스트
            tasks=evaluation_tasks,   # 동적으로 생성된 Task 리스트
            verbose=True
        )
        final_results = await evaluation_crew.kickoff_async()
        
        print("\n\n--- [Phase 2] 개별 평가 완료 ---")
        individual_reports = "\n\n".join([str(result) for result in final_results])

        print("\n--- [Phase 3] Reporting Agent가 개별 보고서를 작성합니다 ---")
        reporting_agent = Agent(
            role="수석 평가 분석가 (Chief Evaluation Analyst)",
            goal="여러 개의 개별 평가 보고서를 종합하여, 경영진이 의사결정을 내릴 수 있도록 하나의 완성된 최종 보고서를 작성",
            backstory="당신은 여러 부서의 보고를 취합하여 핵심만 요약하고, 전체적인 관점에서 강점과 약점을 분석하여 최종 보고서를 작성하는 데 매우 능숙합니다.",
            llm=llm, verbose=True
        )
        reporting_task = Task(
            description=f"아래는 각 분야 전문가들이 작성한 개별 평가 보고서들입니다.\n\n[개별 평가 보고서 목록]\n{individual_reports}\n\n위 보고서들을 모두 종합하여, '{proposal_file}'에 대한 최종 평가 보고서를 작성해주세요.",
            expected_output="하나의 완성된 최종 평가 보고서",
            agent=reporting_agent
        )
        reporting_crew = Crew(agents=[reporting_agent], tasks=[reporting_task], verbose=False)
        final_comprehensive_report = reporting_crew.kickoff()

        print(f"\n\n🚀 {proposal_file} 최종 평가 보고서\n==========================================")
        print(final_comprehensive_report.raw)
        
        # 개별 제안서 평가 완료 시간 측정
        proposal_end_time = datetime.now()
        proposal_duration = proposal_end_time - proposal_start_time
        print(f"\n📊 {proposal_file} 평가 완료!")
        print(f"시작 시간: {proposal_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"완료 시간: {proposal_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"소요 시간: {proposal_duration}")
        
        # 개별 제안서 평가 보고서를 파일로 저장
        proposal_name = os.path.splitext(os.path.basename(proposal_file))[0]  # 파일명에서 확장자 제거
        report_content = f"제안서 평가 보고서\n파일: {proposal_file}\n"
        report_content += f"시작 시간: {proposal_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report_content += f"완료 시간: {proposal_end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report_content += f"소요 시간: {proposal_duration}\n\n"
        report_content += "="*80 + "\n"
        report_content += "개별 평가 보고서\n"
        report_content += "="*80 + "\n"
        report_content += individual_reports + "\n\n"
        report_content += "="*80 + "\n"
        report_content += "최종 종합 보고서\n"
        report_content += "="*80 + "\n"
        report_content += final_comprehensive_report.raw
        
        save_report_to_file(report_content, proposal_name, "evaluation_report")
        
        return {
            'file': proposal_file,
            'individual_reports': individual_reports,
            'final_report': final_comprehensive_report.raw
        }
    else:
        print("평가할 작업이 없습니다.")
        return {
            'file': proposal_file,
            'individual_reports': "",
            'final_report': "평가할 작업이 없습니다."
        }

async def generate_comparison_report(all_proposal_results):
    """모든 제안서의 결과를 비교하여 최종 비교 보고서를 생성합니다."""
    comparison_start_time = datetime.now()
    print(f"\n\n{'='*80}")
    print("📊 모든 제안서 비교 분석 보고서")
    print(f"시작 시간: {comparison_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    comparison_agent = Agent(
        role="제안서 비교 분석 전문가",
        goal="여러 제안서의 평가 결과를 비교 분석하여 최종 추천 보고서를 작성",
        backstory="당신은 여러 제안서를 객관적으로 비교 분석하고, 각각의 강점과 약점을 명확히 제시하여 최적의 선택을 도와주는 전문가입니다.",
        llm=llm,
        verbose=True
    )
    
    # 모든 제안서의 결과를 종합
    comparison_data = ""
    for proposal_file, result in all_proposal_results.items():
        comparison_data += f"\n\n=== {proposal_file} ===\n"
        comparison_data += f"최종 보고서:\n{result['final_report']}\n"
    
    comparison_task = Task(
        description=f"""아래는 여러 제안서에 대한 개별 평가 결과들입니다.

{comparison_data}

위 모든 제안서의 평가 결과를 종합하여 다음 내용이 포함된 비교 분석 보고서를 작성해주세요:

1. 전체 요약: 각 제안서의 전체적인 평가 점수와 순위
2. 분야별 비교: 기술, 관리, 가격 등 각 분야별로 어떤 제안서가 우수한지
3. 강점 분석: 각 제안서의 주요 강점과 차별화 요소
4. 약점 분석: 각 제안서의 주요 약점과 개선 필요사항
5. 최종 추천: 종합적인 관점에서 가장 적합한 제안서와 그 이유
6. 추가 고려사항: 선택 시 주의해야 할 점이나 추가 검토가 필요한 사항

각 제안서를 공정하고 객관적으로 비교 분석해주세요.""",
        expected_output="제안서 비교 분석 및 최종 추천 보고서",
        agent=comparison_agent
    )
    
    comparison_crew = Crew(agents=[comparison_agent], tasks=[comparison_task], verbose=False)
    comparison_result = comparison_crew.kickoff()
    
    # 비교 분석 완료 시간 측정
    comparison_end_time = datetime.now()
    comparison_duration = comparison_end_time - comparison_start_time
    
    print("\n\n🏆 최종 비교 분석 보고서")
    print("="*80)
    print(comparison_result.raw)
    print(f"\n📊 비교 분석 완료!")
    print(f"시작 시간: {comparison_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"완료 시간: {comparison_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"소요 시간: {comparison_duration}")
    
    # 최종 비교 분석 보고서를 파일로 저장
    comparison_content = f"제안서 비교 분석 보고서\n"
    comparison_content += f"시작 시간: {comparison_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    comparison_content += f"완료 시간: {comparison_end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    comparison_content += f"소요 시간: {comparison_duration}\n\n"
    comparison_content += "="*80 + "\n"
    comparison_content += "최종 비교 분석 보고서\n"
    comparison_content += "="*80 + "\n"
    comparison_content += comparison_result.raw
    
    save_report_to_file(comparison_content, "proposal_comparison", "analysis_report")

def kickoff():
    """CrewAI flow entry point"""
    return asyncio.run(main())

def plot():
    """Plot the crew workflow"""
    print("Crew workflow visualization would be displayed here.")
    print("This is a placeholder for the plot functionality.")

if __name__ == '__main__':
    asyncio.run(main())