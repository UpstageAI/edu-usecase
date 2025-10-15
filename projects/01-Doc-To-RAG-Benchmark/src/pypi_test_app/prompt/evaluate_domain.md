### Instruction ### 
- 입력된 Context 내용의 도메인을 자동으로 판별하세요.

- 판별 결과를 기반으로, Question이 도메인에 적합한지 평가하는 Prompt를 작성하세요.

- 출력은 반드시 하나의 JSON 객체여야 하며, 다음 다섯 개의 키만 포함해야 합니다: "Context", "Question", "Answer", "Domain", "Domain_Prompt".

### Input ### 
- Context: 문맥 정보
- Question: Context 기반 생성 질문
- Answer: Context 기반 생성 정답

### Output ### 
- Context
- Question
- Answer
- Domain: 자동 판별된 Context의 도메인(예: "금융", "의료", "IT", "교육" 등)
- Domain_Prompt: Question이 판별된 도메인에 적합하는지 평가하는 Prompt(Instruction, Input, Output으로 구성)

### Constraint ### 
- 생성된 Domain_Prompt는 "해당 도메인의 전문 용어 사용 정확성", "도메인 특화 지식의 정확성", "도메인 관련 맥락의 적절성" 등을 종합해서 1점~5점으로 평가해야 합니다.