# main.py

import os
from dotenv import load_dotenv
from proposal_evaluator_flow.crews.technical_eval_crew.technical_eval_crew import TechnicalEvalCrew

load_dotenv()

def get_context_from_proposal(proposal_file, topic):
    print(f"'{proposal_file}'에서 '{topic}' 관련 내용 검색 중...")
    return f"'{proposal_file}'의 '{topic}'에 대한 내용을 찾았습니다. (가상 RAG 결과)"

if __name__ == '__main__':
    print("## 제안서 평가 프로세스를 시작합니다.")

    proposal_files = ["A사_제안서.pdf", "B사_제안서.pdf"]

    tech_evaluation_topics = {
        "시스템 아키텍처": "MSA 기반의 유연하고 확장 가능한 아키텍처인가?",
    }
    
    manage_evaluation_topics = {
        "프로젝트 관리 방안": "WBS 기반의 상세하고 실현 가능한 일정을 제시하였는가?",
    }

    all_results = {}

    for proposal in proposal_files:
        print(f"\n==========================================")
        print(f"📄 {proposal} 평가 시작...")
        print(f"==========================================")
        
        # 지금은 각 항목이 하나씩이지만, 여러 개를 반복 처리할 수도 있습니다.
        for tech_topic, tech_criteria in tech_evaluation_topics.items():
            for manage_topic, manage_criteria in manage_evaluation_topics.items():
                
                # 각 Task에 필요한 context를 별도로 준비
                tech_context = get_context_from_proposal(proposal, tech_topic)
                manage_context = get_context_from_proposal(proposal, manage_topic)
                
                # 두 Task에 필요한 모든 정보를 한번에 inputs에 담습니다.
                inputs = {
                    'tech_topic': tech_topic,
                    'tech_criteria': tech_criteria,
                    'manage_topic': manage_topic,
                    'manage_criteria': manage_criteria,
                    'context': tech_context  # context를 공유하거나, task별로 따로 전달할 수도 있습니다.
                                             # task description에서 명시적으로 구분해야 합니다.
                }
                
                proposal_crew = TechnicalEvalCrew() # 클래스명을 바꾸셨다면 여기도 수정
                result = proposal_crew.crew().kickoff(inputs=inputs)
                
                print(f"✔️ '{proposal}'에 대한 병렬 평가 완료.")
                
                # 병렬 처리 결과 확인
                # result.tasks_output에는 각 Task의 결과가 리스트 형태로 담겨 있습니다.
                print("\n--- 병렬 실행 결과 ---")
                for task_output in result.tasks_output:
                    # task_output.description, task_output.raw, task_output.agent 등을 통해 상세 결과 확인 가능
                    print(f"AGENT: {task_output.agent}")
                    print(f"RESULT: {task_output.raw}") 
                    print("-" * 20)

                all_results[proposal] = result.raw # 최종 결과 저장 방식은 필요에 따라 변경

    print("\n\n## 🚀 모든 제안서 평가 완료!")