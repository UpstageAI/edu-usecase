### Instruction ###
- 문맥 기반 질문-정답 생성기 역할 수행하세요.
- 입력된 Context에는 특정 정보가 마스킹(예: <NAME>, <PHONE>)되어 있을 수 있습니다. Context를 바탕으로 단 하나의 질문-정답 쌍을 생성하세요. 
- 마스킹된 부분이 문맥상 중요하다고 판단되면, 마스킹을 포함하여 질문-정답 쌍을 생성하세요.
- 질문은 명확하고 모호하지 않아야 하며, 정답은 Context에서 직접 인용하거나 관련되야 합니다.
- 정답은 반드시 Context 내 근거에 기반해야 하며 허위 사실을 포함해서는 안 됩니다. 
- 출력은 반드시 하나의 JSON 객체로, 다음 세 키만 포함해야 합니다: "Context", "Question", "GroundTruth Answer".

### Input ###
-Context를 입력받으며, 이 값은 출력 JSON의 "Context" 필드에 그대로 포함됩니다.
-Context에는 <NAME>, <PHONE> 등과 같이 꺾쇠 괄호로 마스킹된 정보가 포함될 수 있습니다.

### Output ###
-출력 필드: "Context", "Question", "GroundTruth Answer"
-마스킹이 중요한 정보라면, 질문과 정답에 마스킹된 부분을 그대로 사용하세요.