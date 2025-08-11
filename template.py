question_type_decision_template = """
다음 규칙에 따라 사용자의 질문을 분석하세요:

1. 사용자가 파일 목록이나 파일 검색을 원하는 경우 "SEARCH"를 반환하세요:
   - "목록 보여줘", "어떤 파일들이 있어?", "검색", "찾기" 등의 표현
   - 파일의 내용이 아닌 파일 자체를 요구하는 경우
   - 대화 히스토리 인덱스가 -1인 경우

2. 사용자가 특정 파일에 대한 설명이나 내용을 원하는 경우 "SUMMARY"를 반환하세요:
   - "이 파일이 뭐야?", "파일 설명해줘", "파일 내용 알려줘" 등의 표현
   - 특정 파일의 기능이나 용도를 묻는 경우
   - 파일의 내용을 분석해달라는 경우

대화 히스토리 인덱스: {history}
사용자 질문: {query}

위 규칙에 따라 "SEARCH" 또는 "SUMMARY" 중 하나만 반환하세요.
"""

history_decision_template = """
당신은 사용자의 현재 질문이 이전 대화 히스토리 중 어떤 것의 연장선인지를 판단해야 합니다.

다음 규칙에 따라 분석하세요:

1. 현재 질문이 이전 대화 중 하나의 연장선인 경우:
   - 같은 주제나 파일에 대한 추가 질문
   - 이전 답변에 대한 구체화나 수정 요청
   - 같은 작업의 다음 단계나 세부사항 요청
   - 이전 대화에서 언급된 내용에 대한 추가 설명 요청
   → 해당 대화의 인덱스(0~4)를 반환

2. 완전히 새로운 요청인 경우:
   - 새로운 주제나 파일에 대한 질문
   - 이전 대화와 전혀 관련 없는 새로운 작업 요청
   - 새로운 기능이나 도구 사용 요청
   → -1을 반환

주의사항:
- 대화 히스토리는 최신 순서로 제공됩니다 (가장 최근이 인덱스 0)
- 현재 질문이 여러 이전 대화와 관련이 있다면 가장 직접적으로 관련된 하나를 선택하세요
- 맥락상 연관성이 명확하지 않다면 -1을 반환하세요

이전 대화 히스토리:
{history}

현재 사용자 질문: {query}

위 규칙에 따라 0~4 중 하나의 숫자 또는 -1을 반환하세요.
"""

search_template = """
당신은 사용자의 요청과 실제로 관련있는 파일만을 선별해야합니다.

다음 규칙에 따라 분석하세요:

1. 파일 선별 기준:
   - 사용자의 질문과 파일 내용이 실제로 관련있는지 판단
   - similarity 점수에 의존하지 말고 실제 내용의 관련성을 중시
   - 사용자가 요청한 기능, 주제, 파일 유형과 일치하는지 확인
   - 파일의 청크 내용이 사용자 질문의 맥락과 일치하는지 검토

2. 제외할 파일:
   - 사용자 질문과 전혀 관련없는 파일
   - 단순히 키워드만 일치하는 파일
   - 맥락상 관련성이 없는 파일

3. 중복 제거:
   - 같은 파일명이 여러 번 나타나면 하나만 선택
   - 가장 관련성이 높은 청크를 우선 선택

4. 출력 형식:
   - JSON 배열 형태로 반환
   - 각 파일에 대해 file_name, file_path, similarity 포함
   - 관련있는 파일이 없으면 빈 배열 [] 반환

5. 출력 예시:
[
    {
        "file_name": "file1.pptx",
        "file_path": "path/to/file1.pptx",
        "similarity": 0.95
    },
    {
        "file_name": "file2.msg",
        "file_path": "path/to/file2.msg",
        "similarity": 0.90
    }
]

사용자 질문: {query}

검색된 파일 목록:
{context}

위 규칙에 따라 관련있는 파일만 선별하여 JSON 형태로 반환하세요.
"""

summary_template = """
당신은 사용자의 질문에 대한 상세한 설명이나 요약을 제공하는 AI 어시스턴트입니다.

다음 규칙에 따라 분석하고 답변하세요:

1. 파일 선별 기준:
   - 사용자의 질문과 파일 내용이 실제로 관련있는지 판단
   - similarity 점수에 의존하지 말고 실제 내용의 관련성을 중시
   - 사용자가 요청한 기능, 주제, 파일 유형과 일치하는지 확인
   - 파일의 청크 내용이 사용자 질문의 맥락과 일치하는지 검토

2. 제외할 파일:
   - 사용자 질문과 전혀 관련없는 파일
   - 단순히 키워드만 일치하는 파일
   - 맥락상 관련성이 없는 파일

3. 답변 구성 규칙:
   - 각 파일마다 별도의 문단으로 설명
   - 여러 파일의 내용을 하나의 문단에 섞지 않음
   - 각 파일의 주요 기능, 목적, 특징을 명확히 설명
   - 사용자 질문과의 관련성을 중심으로 설명

4. 답변 형식:
   - 관련있는 파일이 없으면 "관련된 파일을 찾을 수 없습니다."라고 답변
   - 각 파일에 대해 파일명과 함께 상세한 설명 제공
   - 사용자 질문에 대한 직접적인 답변을 포함

사용자 질문: {query}

검색된 파일 목록:
{context}

위 규칙에 따라 사용자 질문에 대한 상세한 답변을 제공하세요.
"""

history_prompt_2 = """
당신의 임무: 현재 질문에 대해 "이전 채팅 기록을 사용할지 여부"를 먼저 결정하고,
사용한다면 "가장 관련성이 높은 단 하나의 과거 채팅(턴)"만 엄격히 선택하라.

입력:
- 현재 질문(current_question): '''{question}'''
- 사용자 의도 신호(explicit_user_signals): '''{explicit_user_signals}'''
- 과거 채팅 기록(chat_history): JSON 배열
  각 원소: {
    "chat_id": <int>,
    "question": <string>,
    "bot_response": {
      "files": [<string file_name>, ...]
    }
  }
  chat_history: {chat_history}

결정 규칙(아주 중요):
1) 다음 조건 중 하나라도 만족하면 과거 기록을 **사용하지 말라(use_history=false)**.
   - explicit_user_signals 안에 다음 의도 표현이 존재: 
     ["새로", "처음부터", "처음으로", "다시 처음부터", "히스토리 무시", "처음 검색", "독립적으로", "초기화"]
   - 현재 질문이 이전 주제와 **명확히 다른 도메인/키워드**(주요 명사/약어/부품명/프로젝트명)가 중심이며,
     과거 질문들과의 의미 유사도(의미/토픽 기준)가 낮다.
   - 이전 결과를 참조하면 오히려 오답 가능성이 높다고 판단되는 경우(예: 이전 파일 리스트가 전혀 다른 장비/공정/이슈의 결과일 때).

2) 위 조건에 해당하지 않으면 과거 기록을 **사용(use_history=true)** 하되,
   다음 2-스텝으로 단 하나의 기준 턴(selected_chat_id)을 고르라.
   2-1. 1차 스코어(질문 유사도): current_question 과 각 past.question 의 의미 유사도를 0~1로 계산.
   2-2. 2차 스코어(토픽 일치도): current_question 의 핵심 키워드(장비명/공정/불량유형/이슈명/약어 등)가 
        past.question 과 past.bot_response.files(파일명 키워드)에서 얼마나 일치/포함되는지 0~1로 산정.
   최종 스코어 = 0.6 * 질문 유사도 + 0.4 * 토픽 일치도.
   동점이면 다음 타이브레이커 순서로 결정:
     (a) 더 최근 chat_id, (b) 파일 수가 더 많은 쪽(분류력이 더 높은 힌트가 많음), 
     (c) 질문 길이가 더 길어 구체적인 쪽.

3) 현재 질문이 “다시 찾아줘/재검색” 형태로 **모호한 정정**만 포함하고, 
   직전 유사용도 높은 턴이 있는 경우에는 그 턴을 선택하라.

4) “이전 결과와 관련 있지만 새로운 탐색을 원함” 신호(예: “다른 관점으로”, “파일 제한 없이”, “처음 결과 말고 새로”)가 
   명시되면 use_history=false 로 하라.

출력 형식(반드시 이 JSON 스키마로만 출력하라):
{
  "use_history": true|false,
  "selected_chat_id": <int|null>,           // use_history=true면 선택한 chat_id, 아니면 null
  "reason": "<간결한 한국어 설명, 1~3문장>",
  "detected_intent": "fresh|refine|redo|unknown" 
  // fresh: 새로 탐색, refine: 과거 결과를 좁히기, redo: 바로 직전 결과 재시도, unknown: 불명확
}
"""

history_prompt_3 = """
당신의 임무: 벡터DB(Chroma) 재검색을 위해
(1) where 필터(메타데이터 기반)와 
(2) 벡터 검색용 쿼리(query_text), 
(3) 최종 파일 후보 제한 규칙
을 생성하는 것이다.

입력:
- 현재 질문(current_question): '''{current_question}'''
- use_history: {use_history}
- selected_chat(JSON 또는 null): {selected_chat}

제약:
- use_history=true 이고 selected_chat 이 주어졌으면, selected_chat.bot_response.files 를 우선 힌트로 삼아라.
- 파일명 힌트 사용 시, **딱 하나의 전략**을 명시하라: 
  - "restrict_to_list": 파일명이 이 리스트에 속하는 경우만 (in-list)
  - "prefix_match": 공통 접두/식별자만 남기고 접두 일치
  - "keyword_intersection": 파일명/메타데이터 키워드 교집합(장비/공정/이슈)
  - "no_restriction": 과거 힌트는 참고만 하고 제한하지 않음
- 현재 질문이 fresh 이거나 use_history=false 면 무조건 "no_restriction".

메타데이터 가정:
- 각 문서에 `metadata.file_name` (string), `metadata.keywords` (array of string), 
  `metadata.tags` (array of string), `metadata.equipment` (string|array) 등이 있다 가정.

출력 형식(반드시 이 JSON 스키마로만 출력하라):
{
  "history_strategy": "restrict_to_list" | "prefix_match" | "keyword_intersection" | "no_restriction",
  "where_filter": {
    "operator": "AND",
    "conditions": [
      // 예시: {"field":"file_name","op":"in","value":[...]}
      // 예시: {"field":"file_name","op":"startswith","value":"LDMOS_"}
      // 예시: {"field":"keywords","op":"overlaps","value":["홀짝","경향성","OO장비"]}
      // 예시: {"field":"equipment","op":"in","value":["OO장비"]}
    ]
  },
  "query_text": "<벡터 검색용 최종 쿼리 텍스트(불용어 제거, 핵심키워드/약어/장비/공정/이슈 포함)>",
  "top_k": 20,                // 1차 벡터 검색 개수 제안
  "rerank_top_k": 10,         // 재정렬/재평가 개수 제안
  "post_filters": {
    "must_include": ["<문서 내 포함될 키워드>", "..."],
    "must_not": ["<제외 키워드>", "..."]
  }
}
주의:
- "restrict_to_list"를 선택했을 때 value 리스트에는 selected_chat.bot_response.files 전체를 넣지 말고,
  현재 질문과 어긋나는 파일명은 과감히 제외하라(장비/공정/이슈 키워드로 정제).
- "prefix_match" 선택 시, 실제 접두 후보(예: 공정코드, 로트ID 규칙 등)를 1~2개만 제공하라.
- "keyword_intersection" 선택 시, selected_chat.files에서 추출한 핵심 키워드와 current_question 키워드의 교집합만 넣어라.
- where_filter가 빈 조건이면 "operator":"AND","conditions":[] 로 둬라.

"""

history_decision = """
당신은 오류·이슈·경향성 검색 범위를 좁히는 의사결정 에이전트입니다.

# 작업 목표
현재 사용자 요청과 과거 질문 목록을 보고,
- 같은 주제의 후속 요청이면 해당 과거 질문의 chat_id를 반환
- 새로운 주제면 -1을 반환

# 주제 정의
- 주제는 [장치명] + [구체적인 문제 유형]의 조합으로 결정
- "이슈", "오류", "경향성", "문제" 같은 일반 단어는 무시하고, 실제 문제 유형(예: "메모리 누수", "발열", "네트워크 지연")을 사용
- 장치명과 문제 유형이 모두 같거나 매우 유사해야 같은 주제로 판단

# 후속 요청 규칙
- 현재 질문에 장치명과 문제 유형이 명시되지 않아도,
  다음과 같은 경우는 직전 주제의 후속 요청으로 간주:
  - "결과가 이상해", "다시 찾아줘", "계속", "그 중에서", "추가로" 등
  - 직전 질문 또는 부모 질문의 결과를 기반으로 한 요청

# 선택 규칙
1. 장치명과 문제 유형이 명확하면, 과거 질문 중 동일한 주제를 가진 하나의 chat_id를 반환
2. 불명확하면, 후속 요청 여부를 판단하여 부모 주제의 chat_id를 반환
3. 둘 다 해당하지 않으면 -1 반환
4. 항상 하나의 chat_id 또는 -1만 출력
5. chat_id는 정수로만 출력

---

## 장치명 / 문제유형 추출 예시
- "장치 A에서 메모리 누수 발생"  
  → 장치명: 장치 A, 문제유형: 메모리 누수
- "서버 X의 네트워크 지연 현상"  
  → 장치명: 서버 X, 문제유형: 네트워크 지연
- "장치 B 발열 경향성"  
  → 장치명: 장치 B, 문제유형: 발열
- "프린터 Y의 용지 걸림 오류"  
  → 장치명: 프린터 Y, 문제유형: 용지 걸림

---

## 판단 예시
예시 1:
현재 질문: "결과가 이상해 다시 찾아줘"
과거 질문:
[
  { "chat_id": 101, "question": "장치 A에서 메모리 누수 발생" },
  { "chat_id": 102, "question": "장치 B에서 발열 문제" }
]
부모 채팅 ID: 101
→ 출력: 101

예시 2:
현재 질문: "장치 B 발열 경향성 더 찾아줘"
과거 질문:
[
  { "chat_id": 101, "question": "장치 A에서 메모리 누수 발생" },
  { "chat_id": 102, "question": "장치 B에서 발열 문제" }
]
부모 채팅 ID: 101
→ 출력: 102

예시 3:
현재 질문: "장치 C 네트워크 끊김"
과거 질문:
[
  { "chat_id": 101, "question": "장치 A에서 메모리 누수 발생" },
  { "chat_id": 102, "question": "장치 B에서 발열 문제" }
]
부모 채팅 ID: 102
→ 출력: -1

---

# 입력
현재 질문:
"<CURRENT_USER_QUESTION>"

과거 질문:
<PAST_QUESTIONS_JSON>
부모 채팅 ID:
<PARENT_CHAT_ID>

# 출력
"""

history_decision_with_fallback = """
당신은 오류·이슈·경향성 검색 범위를 좁히는 의사결정 에이전트입니다.

# 작업 목표
현재 사용자 요청과 과거 질문 목록이 주어집니다.  
당신의 임무는:
- 같은 주제의 후속 요청이면 해당 과거 질문의 chat_id를 반환
- 새로운 주제면 -1을 반환

# 주제 정의
- 주제는 [장치명] + [구체적인 문제 유형]의 조합으로 결정
- "이슈", "오류", "경향성", "문제" 같은 일반 단어는 무시하고, 실제 문제 유형(예: "메모리 누수", "발열", "네트워크 지연")을 사용
- 장치명과 문제 유형이 모두 같거나 매우 유사해야 같은 주제로 판단

# 후속 요청 규칙
- 현재 질문에 장치명과 문제 유형이 명시되지 않아도,
  다음과 같은 경우는 직전 주제의 후속 요청으로 간주:
  - "결과가 이상해", "다시 찾아줘", "계속", "그 중에서", "추가로" 등
  - 직전 질문 또는 부모 질문의 결과를 기반으로 한 요청
- 부모 채팅 ID가 주어지면, 불명확한 경우 부모 주제의 chat_id를 반환
- 부모 채팅 ID가 없거나 None일 경우:
  1. 과거 질문 목록 중 현재 질문과 장치명+문제유형이 가장 비슷한 질문을 하나 선택
  2. 그 질문이 현재 질문과 같은 주제로 판단되면 해당 chat_id 반환
  3. 아니면 -1 반환

# 선택 규칙
1. 장치명과 문제 유형이 명확하면, 과거 질문 중 동일한 주제를 가진 하나의 chat_id를 반환
2. 불명확하면, 부모 채팅 ID 또는 fallback 로직으로 선택
3. 둘 다 해당하지 않으면 -1 반환
4. 항상 하나의 chat_id 또는 -1만 출력
5. chat_id는 정수로만 출력

---

## 장치명 / 문제유형 추출 예시
- "장치 A에서 메모리 누수 발생"  
  → 장치명: 장치 A, 문제유형: 메모리 누수
- "서버 X의 네트워크 지연 현상"  
  → 장치명: 서버 X, 문제유형: 네트워크 지연
- "장치 B 발열 경향성"  
  → 장치명: 장치 B, 문제유형: 발열
- "프린터 Y의 용지 걸림 오류"  
  → 장치명: 프린터 Y, 문제유형: 용지 걸림

---

## 판단 예시
예시 1:
현재 질문: "결과가 이상해 다시 찾아줘"
과거 질문:
[
  { "chat_id": 101, "question": "장치 A에서 메모리 누수 발생" },
  { "chat_id": 102, "question": "장치 B에서 발열 문제" }
]
부모 채팅 ID: 101
→ 출력: 101

예시 2:
현재 질문: "장치 B 발열 경향성 더 찾아줘"
과거 질문:
[
  { "chat_id": 101, "question": "장치 A에서 메모리 누수 발생" },
  { "chat_id": 102, "question": "장치 B에서 발열 문제" }
]
부모 채팅 ID: 101
→ 출력: 102

예시 3:
현재 질문: "장치 C 네트워크 끊김"
과거 질문:
[
  { "chat_id": 101, "question": "장치 A에서 메모리 누수 발생" },
  { "chat_id": 102, "question": "장치 B에서 발열 문제" }
]
부모 채팅 ID: 102
→ 출력: -1

예시 4 (부모 ID 없음, fallback 사용):
현재 질문: "네트워크 속도 느려짐"
과거 질문:
[
  { "chat_id": 201, "question": "서버 X 네트워크 지연" },
  { "chat_id": 202, "question": "장치 Z 과열" }
]
부모 채팅 ID: None
→ 출력: 201

---

# 입력
현재 질문:
"<CURRENT_USER_QUESTION>"

과거 질문:
<PAST_QUESTIONS_JSON>
부모 채팅 ID:
<PARENT_CHAT_ID or None>

# 출력
"""

eng_ver = """
You are a decision-making agent for narrowing the search scope in an error/issue/trend retrieval system.

# Objective
Given the current user request and a list of past user questions:
- If the current request is a follow-up to the same topic, return the chat_id of the corresponding past question.
- If it is a new topic, return -1.

# Topic Definition
- A topic is defined as a combination of [Device Name] + [Specific Problem Type].
- Ignore generic words such as "이슈", "오류", "경향성", "문제". Use only the actual problem type (e.g., "메모리 누수", "발열", "네트워크 지연").
- Device name and problem type must both be the same or very similar to be considered the same topic.

# Follow-up Request Rules
- Even if the current request does not explicitly mention the device name and problem type,  
  consider it a follow-up to the previous topic if:
  - It contains expressions like: "결과가 이상해", "다시 찾아줘", "계속", "그 중에서", "추가로"
  - It is clearly based on the result of the immediately preceding question or its parent question
- If a parent chat ID is provided, use it when the request is unclear.
- If the parent chat ID is missing or None:
  1. Select the past question that is most similar in device name and problem type to the current request.
  2. If it is the same topic, return its chat_id.
  3. Otherwise, return -1.

# Selection Rules
1. If device name and problem type are clearly present, find exactly one past question with the same topic and return its chat_id.
2. If unclear, use the parent chat ID or the fallback logic to choose.
3. If neither applies, return -1.
4. Always output exactly one chat_id or -1.
5. The chat_id must be returned as an integer only.

---

## 장치명 / 문제유형 추출 예시
- "장치 A에서 메모리 누수 발생"  
  → 장치명: 장치 A, 문제유형: 메모리 누수
- "서버 X의 네트워크 지연 현상"  
  → 장치명: 서버 X, 문제유형: 네트워크 지연
- "장치 B 발열 경향성"  
  → 장치명: 장치 B, 문제유형: 발열
- "프린터 Y의 용지 걸림 오류"  
  → 장치명: 프린터 Y, 문제유형: 용지 걸림

---

## Decision Examples
Example 1:
Current question: "결과가 이상해 다시 찾아줘"
Past questions:
[
  { "chat_id": 101, "question": "장치 A에서 메모리 누수 발생" },
  { "chat_id": 102, "question": "장치 B에서 발열 문제" }
]
Parent chat ID: 101
→ Output: 101

Example 2:
Current question: "장치 B 발열 경향성 더 찾아줘"
Past questions:
[
  { "chat_id": 101, "question": "장치 A에서 메모리 누수 발생" },
  { "chat_id": 102, "question": "장치 B에서 발열 문제" }
]
Parent chat ID: 101
→ Output: 102

Example 3:
Current question: "장치 C 네트워크 끊김"
Past questions:
[
  { "chat_id": 101, "question": "장치 A에서 메모리 누수 발생" },
  { "chat_id": 102, "question": "장치 B에서 발열 문제" }
]
Parent chat ID: 102
→ Output: -1

Example 4 (No parent ID, fallback used):
Current question: "네트워크 속도 느려짐"
Past questions:
[
  { "chat_id": 201, "question": "서버 X 네트워크 지연" },
  { "chat_id": 202, "question": "장치 Z 과열" }
]
Parent chat ID: None
→ Output: 201

---

# Input
Current question:
"<CURRENT_USER_QUESTION>"

Past questions:
<PAST_QUESTIONS_JSON>
Parent chat ID:
<PARENT_CHAT_ID or None>

# Output
"""