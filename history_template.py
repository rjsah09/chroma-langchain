prompt_1 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 chat_id"를 고르거나, 새 주제면 -1을 반환하세요.

규칙:
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}
- 절대 설명/사유/추론을 출력하지 마세요.
- 내부적으로는 조용히 단계별로 사고해도 되지만, 바깥으로는 JSON만 출력하세요.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
  {{
    "chat_id": <int>,
    "user_message": <string>,
    "created_at": "YYYY-MM-DD HH:MM:SS",
    "bot_response": {{...}}
  }}
  형태입니다. 죽은(더 이상 이어가면 안 되는) 대화도 섞여 있을 수 있습니다.
- current_question: 현재 사용자의 질문 문자열.

목표:
- 아래 절차로 "이어갈 chat_id" 또는 -1을 결정하세요.

용어 정의:
- [토픽] = 사용자 요청에서 추출한 의미적 속성의 묶음.
  - 공정/라인(예: "공정 A", "A 공정")
  - 이슈/불량(예: "B 이슈", "홀짝 경향성", "갈매기 이슈")
  - 장치/설비(예: "G 장치", "A 장치")
  - 기타 필터(날짜, 모델, 사이트 등)
- 두 문장이 위 속성 조합이 의미적으로 동등하면 같은 토픽입니다. 동의어/표현 순서/조사가 달라도 같을 수 있습니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아", "잘못 나온 것 같아", "아직도 이상해", "정확히 다시", "재검색", "결과 이상" 등(유사 표현 포함).
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상 누적되거나, 의미적으로 같은 요청이 2회 이상 반복되어 이전 결과에 지속적 불만이 드러난 상태.
- [죽은 토픽] = 더 뒤(나중)에 전혀 다른 토픽이 등장하여 과거 토픽을 덮어버린 경우. 죽은 토픽은 절대 선택하지 않습니다.

판정 절차(반드시 이 순서로 내부 판단):
1) history를 "가장 최근 항목부터 과거로" 순회하며, 연속한 같은 토픽들의 꼬리 구간을 하나의 [마지막 연속 구간]으로 정의합니다.
   - 현재와 의미적으로 다른 토픽이 나타나는 순간, 그 지점 이전(더 과거)의 토픽들은 [죽은 토픽]으로 간주하고 탐색을 중단합니다. (이전 토픽들은 절대 재사용 금지)
2) current_question의 토픽을 추출합니다.
3) 만약 current_question의 토픽이 [마지막 연속 구간]의 토픽과 다르면: {{"decision": -1}}
4) 같다면, [마지막 연속 구간] 내 사용자 메시지들에서 재시도 신호/동일요청 반복을 센 후
   - 소진 조건(재시도 ≥ 2 또는 의미 동일 요청 ≥ 3)이 충족되면: {{"decision": -1}}
   - 아니면: 같은 토픽의 **가장 처음 chat_id**를 {{"decision": <그 chat_id>}}로 반환합니다.
5) 예외:
   - history가 실질적으로 토픽 정보를 제공하지 못하고, "다시 찾아줘" 같은 재시도성 문장만 연속되어 있으며 현재도 유사하다면: {{"decision": -1}}

판정 시 유의사항:
- "세부 필터로 좁혔다가 다시 찾아줘"는 같은 토픽으로 본다. 이때는 최초 질의의 chat_id로 되돌린다.
- "갈매기 이슈"처럼 전혀 다른 이슈/공정/장치를 언급하면 새로운 토픽이다.
- 표현만 바뀐 완전 동등 질의가 3회 이상 연속이면 그 토픽은 소진으로 본다.
- bot_response 내용은 보조 신호일 뿐, 결정은 사용자 메시지를 최우선으로 한다.

입출력 형식:
- 입력은 다음 두 필드로 제공됨:
  - history: JSON 배열(문자열이 아님, 실제 JSON 구조체)
  - current_question: 문자열
- 출력은 딱 한 줄: {{"decision": -1}} 또는 {{"decision": <chat_id 정수>}}

예시 검증(내부 판단만, 출력은 JSON만 하라):
- 예시1:
  history: 
    0: "공정 A에서 발생한 B 이슈 찾아줘"
    1: "이중에서 C 이슈도 같이 발생한 자료를 찾아줘" (같은 토픽)
    2: "갈매기 이슈 찾아줘" (새 토픽 → 과거 토픽은 죽음)
  current_question: "공정 A에서 B이슈가 발생한 이력을 찾아줘"
  → 마지막 연속 구간은 "갈매기 이슈". 현재는 다른 토픽. 출력: {{"decision": -1}}
- 예시2:
  history:
    0: "D 이슈가 발생한 이력 찾아줘"
    1: "저기서 G 장치와 관련된 이력을 찾아줘" (같은 토픽, 세부 필터)
    2: "아직도 이상해. 다시 찾아줘" (재시도 1회)
  current_question: "결과가 잘못 나온 것 같아. 다시 찾아줘." (재시도 2회 누적 직전)
  → 같은 토픽이며 소진 임계 직전이므로 최초 chat_id(0)로 롤백. 출력: {{"decision": 0}}
- 예시3:
  history:
    0: "다시 찾아줘"
    1: "다시 찾아줘"
    2: "다시 찾아줘"
  current_question: "다시 찾아줘"
  → 토픽 정보 없음 + 재시도만 존재. 출력: {{"decision": -1}}
- 예시4:
  history:
    0: "A장치에서 B 이슈 찾아줘"
    1: "B 이슈가 A 장치에서 발견된 자료 찾아줘" (동일 토픽)
    2: "A에서 B가 발생한 자료" (동일 토픽)
    3: "A에서 B가 발생한 자료" (동일 토픽, 반복)
  current_question: "A에서 B가 발생했던 이력을 보여줘" (동일 토픽, 반복 증가)
  → 동일/동등 요청이 과도하게 반복되어 소진. 출력: {{"decision": -1}}

이제 아래 JSON 입력을 처리하고, 최종 결정 JSON 한 줄만 출력하세요.

history = {history}
current_question = "{question}"

답변: 
"""

prompt_2 = """
You are a decision-making system that determines whether the current user query continues a past conversation topic or starts a new one.

Rules:
- Output must be exactly one line of JSON: {{"decision": <number>}}
- No explanation, reasoning, or extra text in output.
- Internal step-by-step reasoning (chain-of-thought) is allowed but never exposed.

Input:
- history: a JSON list of objects like:
  {{
    "chat_id": <int>,
    "user_message": <string>,
    "created_at": "YYYY-MM-DD HH:MM:SS",
    "bot_response": {{...}}
  }}
  Note: history may include dead topics (conversations that must not be reused).
- current_question: the latest user query (string).

Definitions:
- [Topic] = semantic cluster of attributes extracted from user requests:
  - Process/line (e.g., "공정 A")
  - Issue/failure type (e.g., "B 이슈", "홀짝 경향성")
  - Equipment/device (e.g., "G 장치")
  - Additional filters (date, site, model, etc.)
- Two queries with equivalent facets are the same topic.
- [Retry signal] = phrases such as "다시 찾아줘", "틀린 것 같아", "잘못 나온 것 같아", "아직도 이상해", "정확히 다시", "재검색", "결과 이상" (or close variants).
- [Exhausted] = within the same topic, retry signals appear ≥ 2 times OR identical/near-identical queries appear ≥ 3 times.
- [Dead Topic] = when a new topic appears later, all previous topics are considered dead and must never be selected.

Decision procedure:
1) Traverse history backwards and identify the [last continuous run] of semantically same-topic messages.
   - When a different topic is found, stop: all earlier topics become [dead].
2) Extract current_question’s topic.
3) If current_question topic ≠ last continuous run topic → {{"decision": -1}}
4) If equal:
   - If last continuous run is exhausted → {{"decision": -1}}
   - Else → return {{"decision": <first chat_id of this run>}}
5) Special case: if history has no identifiable topic (only retries) and current_question is also a retry → {{"decision": -1}}

Important:
- Narrowing queries (e.g., "저기서 G 장치 관련만") are considered same topic. Always roll back to the first chat_id of the run.
- Completely different issue/equipment/process = new topic.
- Excessive identical queries mark topic as exhausted.

Input format:
history = {history}
current_question = "{question}"

Output:
"""

prompt_3 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 chat_id"를 고르거나, 새 주제면 -1을 반환하세요.

규칙(출력 형식):
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}
- 절대 설명/사유/추론을 출력하지 마세요.
- 내부적으로 어떤 사고 과정을 거치든 공개 출력은 JSON 한 줄만.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
  {{
    "chat_id": <int>,
    "user_message": <string>,
    "created_at": "YYYY-MM-DD HH:MM:SS",
    "bot_response": {{...}}
  }}
  형태입니다. 죽은(더 이상 이어가면 안 되는) 대화도 섞여 있을 수 있습니다.
- current_question: 현재 사용자의 질문 문자열.

정렬과 스캔(반드시 준수):
- history를 created_at 오름차순으로 정렬한 뒤, **가장 최근 항목부터 과거로** 스캔합니다.
- 연속해서 **같은 토픽**(아래 정의)이 이어진 꼬리 구간을 **[마지막 연속 구간(Last Run)]**이라 부릅니다.
- **Last Run보다 과거의 토픽은 모두 [죽은 토픽]**이며 절대 선택할 수 없습니다.

용어 정의:
- [토픽] = 사용자 요청에서 추출한 의미적 속성의 묶음:
  - 공정/라인(예: "공정 A", "A 공정")
  - 이슈/불량(예: "B 이슈", "홀짝 경향성", "갈매기 이슈")
  - 장치/설비(예: "G 장치", "A 장치")
  - 추가 필터(날짜, 모델, 사이트 등)
- 두 문장이 위 속성 조합이 의미적으로 동등하면 같은 토픽입니다. 동의어/어순/조사 차이는 허용.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아", "잘못 나온 것 같아", "아직도 이상해", "정확히 다시", "재검색", "결과 이상" 등(유사 표현 포함).
- [소진] = 같은 토픽에서 재시도 신호 ≥ 2회 또는 의미적으로 동일/거의 동일 요청 ≥ 3회.
- [죽은 토픽] = **Last Run보다 과거의 모든 토픽**.

지시사/대용표현 처리(강제):
- current_question에 아래 표현이 하나라도 포함되면, **주제 단서가 명시되지 않아도** current_question은 **반드시 Last Run**으로 귀속합니다:
  - "저기서", "거기서", "위(의) 결과", "방금 결과", "방금 것", "그 파일(들)", "위 목록", "앞서(의) 결과", "이거/그거"
- 이 규칙은 텍스트 유사도와 충돌하더라도 **지시사가 우선**입니다.

판정 절차(반드시 이 순서):
1) Last Run을 정합니다(정렬 후, 최신에서 과거로 같은 토픽이 끊기기 전까지의 구간).
2) current_question의 토픽 파셋을 추출합니다.
   - 만약 지시사/대용표현이 존재하고, current_question에 새로운 토픽 단서가 없다면 → current_question은 Last Run으로 간주합니다.
3) 만약 current_question의 토픽이 **Last Run의 토픽과 다르면**: {{"decision": -1}}
4) 같다면, Last Run 내 사용자 메시지에서 재시도/동일요청 반복을 계산:
   - 소진(재시도 ≥ 2 또는 동일/유사 요청 ≥ 3)이라면: {{"decision": -1}}
   - 아니면: **Last Run의 최초 chat_id**를 {{"decision": <그 chat_id>}}로 반환합니다.
5) 예외:
   - history가 실질적인 토픽 정보 없이 재시도성 문장만 있고 current_question도 재시도성 문장뿐이면: {{"decision": -1}}

판정 시 유의:
- 세부 필터(예: "G 장치만")는 같은 토픽입니다. 이 경우 **최초 chat_id**로 롤백합니다.
- bot_response는 보조 신호일 뿐, 주제 판정은 user_message를 우선합니다. 다만 지시사가 있으면 바로 직전 맥락(Last Run)을 우선합니다.
- **Last Run 이전의 토픽은 어떤 이유로도 선택할 수 없습니다.**

입력:
history = {history}
current_question = {question}

답변:
"""

prompt_4 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 chat_id"를 고르거나, 새 주제면 -1을 반환하세요.

규칙(출력 형식):
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}
- 절대 설명/사유/추론을 출력하지 마세요.
- 내부적으로 어떤 사고 과정을 거치든 공개 출력은 JSON 한 줄만.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다. 죽은(더 이상 이어가면 안 되는) 대화도 섞여 있을 수 있습니다.
- current_question: 현재 사용자의 질문 문자열.

정렬과 스캔(반드시 준수):
- history를 created_at 오름차순으로 정렬한 뒤, **가장 최근 항목부터 과거로** 스캔합니다.
- 연속해서 **같은 토픽**(아래 정의)이 이어진 꼬리 구간을 **[마지막 연속 구간(Last Run)]**이라 부릅니다.
- **Last Run보다 과거의 토픽은 모두 [죽은 토픽]**이며 절대 선택할 수 없습니다.

용어 정의:
- [토픽] = 사용자 요청에서 추출한 의미적 속성의 묶음:
- 공정/라인(예: "공정 A", "A 공정")
- 이슈/불량(예: "B 이슈", "홀짝 경향성", "갈매기 이슈")
- 장치/설비(예: "G 장치", "A 장치")
- 추가 필터(날짜, 모델, 사이트 등)
- 두 문장이 위 속성 조합이 의미적으로 동등하면 같은 토픽입니다. 동의어/어순/조사 차이는 허용.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아", "잘못 나온 것 같아", "아직도 이상해", "정확히 다시", "재검색", "결과 이상" 등(유사 표현 포함).
- [소진] = 같은 토픽에서 재시도 신호 ≥ 2회 또는 의미적으로 동일/거의 동일 요청 ≥ 3회.
- [죽은 토픽] = **Last Run보다 과거의 모든 토픽**.

지시사/대용표현 처리(강제):
- current_question에 아래 표현이 하나라도 포함되면, **주제 단서가 명시되지 않아도** current_question은 **반드시 Last Run**으로 귀속합니다:
- "저기서", "거기서", "위(의) 결과", "방금 결과", "방금 것", "그 파일(들)", "위 목록", "앞서(의) 결과", "이거/그거"
- 이 규칙은 텍스트 유사도와 충돌하더라도 **지시사가 우선**입니다.

판정 절차(반드시 이 순서):
1) Last Run을 정합니다(정렬 후, 최신에서 과거로 같은 토픽이 끊기기 전까지의 구간).
2) current_question의 토픽 파셋을 추출합니다.
- 만약 지시사/대용표현이 존재하고, current_question에 새로운 토픽 단서가 없다면 → current_question은 Last Run으로 간주합니다.
3) 만약 current_question의 토픽이 **Last Run의 토픽과 다르면**: {{"decision": -1}}
4) 같다면, Last Run 내 사용자 메시지에서 재시도/동일요청 반복을 계산:
- 소진(재시도 ≥ 2 또는 동일/유사 요청 ≥ 3)이라면: {{"decision": -1}}
- 아니면: **Last Run의 최초 chat_id**를 {{"decision": <그 chat_id>}}로 반환합니다.
5) 예외:
- history가 실질적인 토픽 정보 없이 재시도성 문장만 있고 current_question도 재시도성 문장뿐이면: {{"decision": -1}}

판정 시 유의:
- 세부 필터(예: "G 장치만")는 같은 토픽입니다. 이 경우 **최초 chat_id**로 롤백합니다.
- bot_response는 보조 신호일 뿐, 주제 판정은 user_message를 우선합니다. 다만 지시사가 있으면 바로 직전 맥락(Last Run)을 우선합니다.
- **Last Run 이전의 토픽은 어떤 이유로도 선택할 수 없습니다.**

# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [12313223, 1234567890, 1234567892, 1234567894].
2. 가장 최근 항목부터 거꾸로 스캔하며 Last Run을 찾는다.
- chat_id: 1234567894, user_message: "갈매기성 현상이 있는 파일 찾아줘". 토픽은 '갈매기성 현상'.
- chat_id: 1234567892, user_message: "각 파일마다 무엇이 오류였는지 알려줘". '각 파일마다' 지시사 존재. 이전 항목(1234567890)의 토픽('공정 A, B 이슈')과 동일한 토픽으로 간주.
- 1234567894의 토픽('갈매기성 현상')과 1234567892의 토픽('공정 A, B 이슈')은 다르므로 연속성이 끊긴다.
- 따라서 Last Run은 [1234567894] 하나뿐이며, Last Run의 최초 chat_id는 1234567894이다. 1234567892는 Last Run보다 과거이므로 죽은 토픽이다.
3. current_question의 토픽을 파악한다.
- current_question: "저기서 각 파일마다 어떤 오류가 발생했는지 설명해줘". '저기서' 지시사 포함.
4. 규칙에 따라 지시사 포함 시 current_question은 Last Run으로 귀속된다.
5. current_question과 Last Run의 토픽을 비교한다.
- Last Run은 '갈매기성 현상'을 다룬 1234567894이고, current_question은 '저기서'라는 지시사를 통해 바로 그 맥락을 이어가고 있다. 토픽이 같다.
6. Last Run 내 소진 여부를 확인한다.
- Last Run은 1234567894 한 건뿐이다. 재시도/동일요청이 없으므로 소진되지 않았다.
7. 최종 결정.
- 토픽이 같고 소진되지 않았으므로, Last Run의 최초 chat_id인 1234567894를 반환한다.

입력:
history = {history}
current_question = {question}

답변:
"""

prompt_5 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 chat_id"를 고르거나, 새 주제면 -1을 반환하세요.

규칙(출력 형식):
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}
- 절대 설명/사유/추론을 출력하지 마세요.
- 내부적으로 어떤 사고 과정을 거치든 공개 출력은 JSON 한 줄만.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. 이 때 '불량', '이슈', '문제' 등 일반 단어는 토픽에 포함되지 않으며 예를 들어 '갈매기 이슈'는 토픽이 아니라 '갈매기'가 토픽이다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거" 등.

판정 절차(**반드시 이 순서로만 판정**):
1.  history를 created_at 오름차순으로 정렬한 뒤, **가장 과거 대화부터 최신 대화순으로** 스캔합니다.
2.  토픽이 이어진 구간을 **[Run]**으로 정의합니다. 이 때, 가장 최신의 Run을 **[Last Run]**으로 정의합니다. Last Run에 소속하지 않는 대화는 모두 **[죽은 토픽]**입니다.
3.  죽은 토픽은 절대로 판단의 대상이 되어서는 안되며 내용과 문맥, 토픽 등 모든 정보는 무시합니다.
4.  **current_question에 지시사/대용표현이 포함되면**:
    -   current_question은 **Last Run의 토픽을 이어가는 것으로 간주합니다.**
    -   이 경우, Last Run이 소진되었는지 판단하여 소진되었으면 -1, 아니면 Last Run의 최초 chat_id를 반환합니다.
    -   **만약 Last Run이 비어있다면, -1을 반환합니다.**
5.  **current_question에 지시사/대용표현이 포함되지 않으면**:
    -   current_question에서 새로운 토픽을 추출합니다.
    -   이 토픽이 **Last Run의 토픽과 같으면**: Last Run의 소진 여부를 판단합니다. 소진되었으면 -1, 아니면 Last Run의 최초 chat_id를 반환합니다.
    -   이 토픽이 **Last Run의 토픽과 다르면**: -1을 반환합니다.
    
Last Run 판단 예시:
-현재 질문: "공정 B에서 발생한 이슈 찾아줘"
-과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
-사고 과정: 
  1. chat_id 1234567806 ~ 1234567808이 하나의 Run이다 (라인B 설비 이력 점검 내역 및 해당 질문으로 부터 파생된 질문)
  2. 1234567800 ~ 1234567804이 하나의 Run이다. (오염 불량 관련 보고서 및 해당 질문으로 부터 파생된 질문)
  3. chat_id 1234567800 ~ 1234567804이 더 오래된 주제이므로 이는 죽은 토픽이며, Last Run은 1234567806 ~ 1234567808이다.
  4. 현재 질문인 "B 이슈 이력 찾아줘"에서 지시서는 포함되어 있지 않으므로 Last Run의 소진 여부 혹은 다른 토픽 여부를 판단한다.
  5. 현재 질문은 Last Run인 오염 불량 관련 보고서와 관련 없는 새로운 이슈를 다루고 있으므로 다른 주제(토픽)이다.
  7. 다른 주제이므로 -1을 반환한다.
  8. 최종 답변: {{"decision": -1}}

    
입력:
history = {history}
current_question = {question}

답변:
"""

prompt_6 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 chat_id"를 고르거나, 새 주제면 -1을 반환하세요.

규칙(출력 형식):
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}
- 절대 설명/사유/추론을 출력하지 마세요.
- 내부적으로 어떤 사고 과정을 거치든 공개 출력은 JSON 한 줄만.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. '불량', '이슈', '문제' 같은 일반 단어는 토픽에 포함되지 않으며, '갈매기 이슈'는 '갈매기'가 토픽입니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거" 등.

판정 절차(**무조건 이 순서대로만 판단하고, 단계를 건너뛰지 마세요**):
1.  history를 created_at 오름차순으로 정렬한 뒤, 가장 **최신 항목부터 과거로** 스캔합니다.
2.  연속해서 같은 토픽이 이어진 가장 최근의 구간을 **[Last Run]**으로 정의합니다.
3.  **Last Run에 포함되지 않는 모든 항목은 [죽은 토픽]이며, 그 정보는 완전히 무시합니다.** 어떤 경우에도 죽은 토픽은 선택될 수 없습니다.
4.  **current_question에 지시사/대용표현이 포함되면**:
    -   current_question은 **Last Run의 토픽을 이어가는 것으로 간주합니다.**
    -   이 경우, Last Run이 소진되었는지 판단하여 소진되었으면 -1, 아니면 Last Run의 최초 chat_id를 반환합니다.
    -   만약 Last Run이 비어있다면, -1을 반환합니다.
5.  **current_question에 지시사/대용표현이 포함되지 않으면**:
    -   current_question에서 새로운 토픽을 추출합니다.
    -   이 토픽이 **Last Run의 토픽과 같으면**: Last Run의 소진 여부를 판단합니다. 소진되었으면 -1, 아니면 Last Run의 최초 chat_id를 반환합니다.
    -   이 토픽이 **Last Run의 토픽과 다르면**: -1을 반환합니다.
---
판단 예시:
# 현재 질문: "공정 K에서 발생한 이슈 찾아줘"
# 과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [1234567800, 1234567802, 1234567804, 1234567806, 1234567808].
2. 가장 최신 항목인 chat_id 1234567808부터 과거로 스캔하며 Last Run을 찾는다.
3. chat_id 1234567808의 user_message("저기서 작년 11월 기록만 보여줄 수 있어?")에는 '저기서'라는 지시사가 있으므로, 이전 대화(1234567806)와 같은 토픽으로 간주한다. 1234567806의 토픽은 '라인B 설비'이다.
4. chat_id 1234567806의 토픽('라인B 설비')과 그 이전 대화(1234567804)의 토픽('오염 불량')은 다르므로, 토픽의 연속성이 끊긴다.
5. 따라서 **Last Run은 [1234567806, 1234567808]**이며, 그 외 모든 항목([1234567800, 1234567802, 1234567804])은 죽은 토픽이다.
6. 현재 질문("공정 K에서 발생한 이슈 찾아줘")에는 지시사가 포함되지 않았다.
7. 현재 질문의 토픽('공정 K')과 Last Run의 토픽('라인B 설비')은 다르다.
8. 규칙에 따라, 토픽이 다르므로 -1을 반환한다.
9. 최종 답변: {{"decision": -1}}

입력:
history = {history}
current_question = "{question}"

답변:
"""

prompt_7 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 chat_id"를 고르거나, 새 주제면 -1을 반환하세요.

규칙(출력 형식):
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}
- 절대 설명/사유/추론을 출력하지 마세요.
- 내부적으로 어떤 사고 과정을 거치든 공개 출력은 JSON 한 줄만.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. '불량', '이슈', '문제' 같은 일반 단어는 토픽에 포함되지 않으며, '갈매기 이슈'는 '갈매기'가 토픽입니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거" 등.

판정 절차(**무조건 이 순서대로만 판단하고, 단계를 건너뛰지 마세요**):
1.  history를 created_at 오름차순으로 정렬한 뒤, 가장 **최신 항목부터 과거로** 스캔합니다.
2.  연속해서 같은 토픽이 이어진 가장 최근의 구간을 **[Last Run]**으로 정의합니다.
3.  **Last Run에 포함되지 않는 모든 항목은 [죽은 토픽]이며, 그 정보는 완전히 무시합니다.** 어떤 경우에도 죽은 토픽은 선택될 수 없습니다.
4.  **current_question에 지시사/대용표현이 포함되면**:
    -   current_question은 **Last Run의 토픽을 이어가는 것으로 간주합니다.**
    -   이 경우, Last Run이 소진되었는지 판단하여 소진되었으면 -1, 아니면 Last Run에 속하는 대화 중 지시사/대용표현이 가리키는 chat_id를 반환합니다.
    -   만약 Last Run이 비어있다면, -1을 반환합니다.
5.  **current_question에 지시사/대용표현이 포함되지 않으면**:
    -   current_question에서 새로운 토픽을 추출합니다.
    -   이 토픽이 **Last Run의 토픽과 같으면**: Last Run의 소진 여부를 판단합니다. 소진되었으면 -1, 아니면 Last Run의 최초 chat_id를 반환합니다.
    -   이 토픽이 **Last Run의 토픽과 다르면**: -1을 반환합니다.
---
판단 예시:
# 현재 질문: "공정 K에서 발생한 이슈 찾아줘"
# 과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [1234567800, 1234567802, 1234567804, 1234567806, 1234567808].
2. 가장 최신 항목인 chat_id 1234567808부터 과거로 스캔하며 Last Run을 찾는다.
3. chat_id 1234567808의 user_message("저기서 작년 11월 기록만 보여줄 수 있어?")에는 '저기서'라는 지시사가 있으므로, 이전 대화(1234567806)와 같은 토픽으로 간주한다. 1234567806의 토픽은 '라인B 설비'이다.
4. chat_id 1234567806의 토픽('라인B 설비')과 그 이전 대화(1234567804)의 토픽('오염 불량')은 다르므로, 토픽의 연속성이 끊긴다.
5. 따라서 **Last Run은 [1234567806, 1234567808]**이며, 그 외 모든 항목([1234567800, 1234567802, 1234567804])은 죽은 토픽이다.
6. 현재 질문("공정 K에서 발생한 이슈 찾아줘")에는 지시사가 포함되지 않았다.
7. 현재 질문의 토픽('공정 K')과 Last Run의 토픽('라인B 설비')은 다르다.
8. 규칙에 따라, 토픽이 다르므로 -1을 반환한다.
9. 최종 답변: {{"decision": -1}}

입력:
history = {history}
current_question = "{question}"

답변:
"""

prompt_8 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 chat_id"를 고르거나, 새 주제면 -1을 반환하세요.

규칙(출력 형식):
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}
- 절대 설명/사유/추론을 출력하지 마세요.
- 내부적으로 어떤 사고 과정을 거치든 공개 출력은 JSON 한 줄만.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. '불량', '이슈', '문제' 같은 일반 단어는 토픽에 포함되지 않으며, '갈매기 이슈'는 '갈매기'가 토픽입니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거" 등.

판정 절차(**무조건 이 순서대로만 판단하고, 단계를 건너뛰지 마세요**):
1.  history를 created_at 오름차순으로 정렬한 뒤, 가장 **최신 항목부터 과거로** 스캔합니다.
2.  연속해서 같은 토픽이 이어진 가장 최근의 구간을 **[Last Run]**으로 정의합니다.
3.  **Last Run에 포함되지 않는 모든 항목은 [죽은 토픽]이며, 그 정보는 완전히 무시합니다.** 어떤 경우에도 죽은 토픽은 선택될 수 없습니다.
4.  **current_question에 지시사/대용표현이 포함되면**:
    -   current_question은 **Last Run의 토픽을 이어가는 것으로 간주합니다.**
    -   이 경우, Last Run이 소진되었는지 판단하여 소진되었으면 -1, 아니면 Last Run에 속하는 대화 중 지시사/대용표현이 가리키는 chat_id를 반환합니다.
      -  지시사/대용 표현이 '여기서', '저기서', '거기서', '이거' 등의 단어라면 Last Run의 가장 최신 chat_id를 반환합니다.
      -  지시사/대용 표현이 '전 결과에서', '전전 결과에서', '3번째 전에서' 등 몇 번째 전에서 라는 표현이 있으면 그 번째 전의 chat_id를 반환합니다.
    -   만약 Last Run이 비어있다면, -1을 반환합니다.
5.  **current_question에 지시사/대용표현이 포함되지 않으면**:
    -   current_question에서 새로운 토픽을 추출합니다.
    -   이 토픽이 **Last Run의 토픽과 같으면**: Last Run의 소진 여부를 판단합니다. 소진되었으면 -1, 아니면 Last Run의 최초 chat_id를 반환합니다.
    -   이 토픽이 **Last Run의 토픽과 다르면**: -1을 반환합니다.
---
판단 예시:
# 현재 질문: "공정 K에서 발생한 이슈 찾아줘"
# 과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [1234567800, 1234567802, 1234567804, 1234567806, 1234567808].
2. 가장 최신 항목인 chat_id 1234567808부터 과거로 스캔하며 Last Run을 찾는다.
3. chat_id 1234567808의 user_message("저기서 작년 11월 기록만 보여줄 수 있어?")에는 '저기서'라는 지시사가 있으므로, 이전 대화(1234567806)와 같은 토픽으로 간주한다. 1234567806의 토픽은 '라인B 설비'이다.
4. chat_id 1234567806의 토픽('라인B 설비')과 그 이전 대화(1234567804)의 토픽('오염 불량')은 다르므로, 토픽의 연속성이 끊긴다.
5. 따라서 **Last Run은 [1234567806, 1234567808]**이며, 그 외 모든 항목([1234567800, 1234567802, 1234567804])은 죽은 토픽이다.
6. 현재 질문("공정 K에서 발생한 이슈 찾아줘")에는 지시사가 포함되지 않았다.
7. 현재 질문의 토픽('공정 K')과 Last Run의 토픽('라인B 설비')은 다르다.
8. 규칙에 따라, 토픽이 다르므로 -1을 반환한다.
9. 최종 답변: {{"decision": -1}}

입력:
history = {history}
current_question = "{question}"

답변:
"""

prompt_9 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 chat_id"를 고르거나, 새 주제면 -1을 반환하세요.

규칙(출력 형식):
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}
- 절대 설명/사유/추론을 출력하지 마세요.
- 내부적으로 어떤 사고 과정을 거치든 공개 출력은 JSON 한 줄만.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. '불량', '이슈', '문제' 같은 일반 단어는 토픽에 포함되지 않으며, '갈매기 이슈'는 '갈매기'가 토픽입니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거" 등.

판정 절차(**무조건 이 순서대로만 판단하고, 단계를 건너뛰지 마세요**):
1.  history를 created_at 오름차순으로 정렬한 뒤, 가장 **최신 항목부터 과거로** 스캔합니다.
2.  연속해서 같은 토픽이 이어진 가장 최근의 구간을 **[Last Run]**으로 정의합니다.
3.  **Last Run에 포함되지 않는 모든 항목은 [죽은 토픽]이며, 그 정보는 완전히 무시합니다.** 어떤 경우에도 죽은 토픽은 선택될 수 없습니다.
4.  **current_question에 지시사/대용표현이 포함되면**:
    -  **모든 대화와 현재 질문에서 등장하는 문맥과 주제 등 모든 것을 제외하고 지시사/대용 표현만을 참고합니다.**
    -  current_question은 **Last Run의 토픽에 관계없이 모든 대화 이력을 활용하여 판단하는 것으로 간주합니다.**
    -  지시사/대용 표현이 '여기서', '저기서', '거기서', '이거' 등의 단어라면 토픽이나 Last Run과 관계 없이 가장 최신 chat_id를 반환합니다.
    -  지시사/대용 표현이 '전 결과에서', '전전 결과에서', '3번째 전에서', '전전에서' 등 몇 번째 전을 가리키는 표현이 있으면 그 번째 전의 chat_id를 반환합니다.
      -  이 때, 전은 현재 질문의 직전 대화, 즉 이전 대화 이력에서 가장 최신 대화를 가리킨다. 따라서 전은 가장 최신 chat_id, 전전은 그 직전의 chat_id를 기리킨다.
5.  **current_question에 지시사/대용표현이 포함되지 않으면**:
    -   current_question에서 새로운 토픽을 추출합니다.
    -   이 토픽이 **Last Run의 토픽과 같으면**: Last Run의 소진 여부를 판단합니다. 소진되었으면 -1, 아니면 Last Run의 최초 chat_id를 반환합니다.
    -   이 토픽이 **Last Run의 토픽과 다르면**: -1을 반환합니다.
---
판단 예시:
# 현재 질문: "전전 결과에서 작년 12월에 발생한 기록만 찾아"
# 과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [1234567800, 1234567802, 1234567804, 1234567806, 1234567808].
2. 현재 질문("전전 파일들의 내용에 대해 설명해줘")에는 '전전'이라는 지시사/대용표현이 포함되어 있으므로, Last Run 판단을 건너뛰고 규칙 4를 적용한다.
3. 규칙 4의 '몇 번째 전' 표현에 따라 '전전'이 가리키는 chat_id를 찾는다.
4. '전'은 가장 최신 대화(1234567808)의 바로 이전 대화인 1234567806를 가리킨다.
5. '전전'은 '전'의 이전 대화를 가리키므로, 1234567806의의 바로 이전 대화인 1234567804를를 가리킨다.
6. 하지만, 사용자의 의도상 '전전'은 보통 '가장 최근 대화'와 '그 전 대화'를 건너뛰고 **세 번째 대화**를 가리키는 경우가 아니라, '가장 최근 대화'를 '현재'로 보고 '전'과 '전전'을 차례로 세는 경우가 많다. 따라서 '전전'은 현재 질문의 2번째 전 대화인 1234567806를 의미하는 것으로 해석하는 것이 더 자연스럽다.
7. 따라서 1234567806의의 chat_id를 반환한다.
8. 최종 답변: {{"decision": 1234567806}}

입력:
history = {history}
current_question = "{question}"

답변:
"""

prompt_10 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 chat_id"를 고르거나, 새 주제면 -1, 오류면 -2를 반환하세요.

규칙(출력 형식):
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}
- 절대 설명/사유/추론을 출력하지 마세요.
- 내부적으로 어떤 사고 과정을 거치든 공개 출력은 JSON 한 줄만.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. '불량', '이슈', '문제' 같은 일반 단어는 토픽에 포함되지 않으며, '갈매기 이슈'는 '갈매기'가 토픽입니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거" 등.

판정 절차(**무조건 이 순서대로만 판단하고, 단계를 건너뛰지 마세요**):
1. history를 created_at 오름차순으로 정렬합니다.
2. **current_question에 지시사/대용표현이 포함되면**:
    - **모든 대화와 현재 질문에서 등장하는 문맥과 주제 등 모든 것을 제외하고 지시사/대용표현만을 참고합니다.**
    - 지시사/대용표현이 '여기서', '저기서', '거기서', '이거', '이 중에서' 등의 단어라면 가장 최신 chat_id를 반환합니다.
    - 지시사/대용표현이 '전 결과에서', '전전 결과에서', '3번째 전에서', '전전에서' 등 **몇 번째 전**을 가리키는 표현이 있으면 history에 current_question이 추가되었다고 가정하고 그 번째 전의 chat_id를 반환합니다.
        - 이 때, 대화는 최신순으로 1번째, 2번째, 3번째...로 순서를 매깁니다. **'전'은 1번째 전, 즉 history의 가장 최신 chat_id를 가리킵니다.** **'전전'은 2번째 전, 즉 history에서 가장 최신에서 두 번째 이전 chat_id를 가리킵니다.**
        - 따라서, '전'이라는 표현은 history에서만 참고하는 것이 아닌 current_question을 포함한 목록에서 판단해야 합니다.
4. **current_question에 지시사/대용표현이 포함되지 않으면**:
    - 토픽이 포함된 경우 -1을 반환하세요.
    - 토픽이 포함되지 않고 재시도 신호가 포함된 경우 -2를 반환하세요.
---
판단 예시:
# 현재 질문: "전전 결과에서 두번째 파일의 내용을 알려줘"
# 과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }},
                {{
                    "file_name": "라인B 설비 점검 이력_수정본.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력_수정본.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [1234567800, 1234567801, 1234567802, 1234567804, 1234567806, 1234567808].
2. 지시사/대용 표현이 포함되어 있는지 확인한다: 현재 질문("전전 결과에서 두번째 파일의 내용을 알려줘")에는 '전전'이라는 지시사/대용표현이 포함되어 있으므로, 규칙 2를 적용한다.
  -'두번째 파일'이라는 표현은 history에서 전전 결과로 생성된 파일 목록 중 두 번째 파일을 가리키는 것이기 때문에 '두번째 파일' 표현은 무시한다.
3. 규칙 2의 '몇 번째 전' 표현에 따라 '전전'이 가리키는 chat_id를 찾는다.
4. '전전'은 history에서 두 번째 최신 chat_id를 가리킨다.
5. history를 최신순으로 보면, 1번째는 1234567808, 2번째는 1234567806이다.
6. 따라서 '전전'이 가리키는 chat_id는 1234567806이다.
7. 최종 답변: {{"decision": 1234567806}}

입력:
history = {history}
current_question = "{question}"

답변:
"""

prompt_11 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 chat_id"를 고르거나, 새 주제면 -1, 오류면 -2를 반환하세요.

규칙(출력 형식):
- 판정 절차와 사고 과정을 따른 후, JSON 스키마를 생성해야 합니다. 출력은 반드시 사고 과정을 마친 후 생성되어야 합니다.
- 절대 설명/사유/추론을 출력하지 마세요.
- 내부적으로 어떤 사고 과정을 거치든 공개 출력은 JSON 한 줄만.
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. '불량', '이슈', '문제' 같은 일반 단어는 토픽에 포함되지 않으며, '갈매기 이슈'는 '갈매기'가 토픽입니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거" 등.

판정 절차(**무조건 이 순서대로만 판단하고, 단계를 건너뛰지 마세요**):
1. history를 created_at 오름차순으로 정렬합니다.
2. **current_question에 지시사/대용표현이 포함되면**:
    - **모든 대화와 현재 질문에서 등장하는 문맥과 주제 등 모든 것을 제외하고 지시사/대용표현만을 참고합니다.**
    - 지시사/대용표현이 '여기서', '저기서', '거기서', '이거', '이 중에서' 등의 단어라면 가장 최신 chat_id를 반환합니다.
    - 지시사/대용표현이 '전 결과에서', '전전 결과에서', '3번째 전에서', '전전에서' 등 **몇 번째 전**을 가리키는 표현이 있으면 그 번째의 chat_id를 반환합니다.
        - 이 때, 대화는 history의 마지막 항목부터 역순으로 1번째, 2번째, 3번째...로 순서를 매깁니다. **'전'은 가장 최신 chat_id, '전전'은 2번째 최신 chat_id를 의미합니다.**
        - 따라서, '전'이라는 표현은 history에서만 참고하는 것이 아닌 current_question을 포함한 목록에서 판단해야 합니다.
3.  **current_question에 지시사/대용표현이 포함되지 않으면**:
    - history를 created_at 오름차순으로 정렬한 뒤, 가장 **최신 항목부터 과거로** 스캔하여 연속해서 같은 토픽이 이어진 가장 최근의 구간을 **[Last Run]**으로 정의합니다.
    - Last Run에 포함되지 않는 모든 항목은 [죽은 토픽]이며, 그 정보는 완전히 무시합니다. 어떤 경우에도 죽은 토픽은 선택될 수 없습니다.
    - current_question에서 새로운 토픽을 추출합니다.
    - 이 토픽이 Last Run의 토픽과 같으면: Last Run의 소진 여부를 판단합니다. 소진되었으면 -1, 아니면 Last Run의 최초 chat_id를 반환합니다.
    - 이 토픽이 Last Run의 토픽과 다르면: -1을 반환합니다.
---
판단 예시:
# 현재 질문: "전전 결과에서 두번째 파일의 내용을 알려줘"
# 과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }},
                {{
                    "file_name": "라인B 설비 점검 이력_수정본.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력_수정본.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [1234567800, 1234567801, 1234567802, 1234567804, 1234567806, 1234567808].
2. 지시사/대용 표현이 포함되어 있는지 확인한다: 현재 질문("전전 결과에서 두번째 파일의 내용을 알려줘")에는 '전전'이라는 지시사/대용표현이 포함되어 있으므로, 규칙 2를 적용한다.
  -'두번째 파일'이라는 표현은 history에서 '전전 결과'로 생성된 파일 목록 중 두 번째 파일을 가리키는 것이기 때문에 '두번째 파일' 표현은 무시한다. 
3. 규칙 2의 '몇 번째 전' 표현에 따라 '전전'이 가리키는 chat_id를 찾는다.
  -'전'이라는 키워드는 history에서 최신을 의미하므로,
4. history를 최신순으로 보면, 1번째는 1234567808, 2번째는 1234567806이다.
5. '전전'은 2번째 최신 대화를 가리키므로, 1234567806을 반환한다.
6. 최종 답변: {{"decision": 1234567806}}

입력:
history = {history}
current_question = "{question}"

답변:
"""

prompt_12 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 chat_id"를 고르거나, 새 주제면 -1, 오류면 -2를 반환하세요.

규칙(출력 형식):
- 절대 설명/사유/추론을 출력하지 마세요.
- 내부적으로 어떤 사고 과정을 거치든 공개 출력은 JSON 한 줄만.
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. '불량', '이슈', '문제' 같은 일반 단어는 토픽에 포함되지 않으며, '갈매기 이슈'는 '갈매기'가 토픽입니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거" 등.

판정 절차(**무조건 이 순서대로만 판단하고, 단계를 건너뛰지 마세요**):
1. history를 created_at 오름차순으로 정렬합니다.
2. **current_question에 지시사/대용표현이 포함되면**:
    - **모든 대화와 현재 질문에서 등장하는 문맥과 주제 등 모든 것을 제외하고 지시사/대용표현만을 참고합니다.**
    - 지시사/대용표현이 '여기서', '저기서', '거기서', '이거', '이 중에서' 등의 단어라면 가장 최신 chat_id를 반환합니다.
    - 지시사/대용표현이 '전 결과에서', '전전 결과에서', '3번째 전에서', '전전에서' 등 **몇 번째 전**을 가리키는 표현이 있으면 **current_question을 가장 최신 대화 이력으로 가정**하고, 그 번째 전의 chat_id를 반환합니다.
      - 예를 들어, '전 결과에서'라는 표현이 있으면, current_question을 가장 최신 대화 이력으로 가정하고, 그 전의 결과인 history의 가장 최신 chat_id를 반환합니다.
3.  **current_question에 지시사/대용표현이 포함되지 않으면**:
    - history를 created_at 오름차순으로 정렬한 뒤, 가장 **최신 항목부터 과거로** 스캔하여 연속해서 같은 토픽이 이어진 가장 최근의 구간을 **[Last Run]**으로 정의합니다.
    - Last Run에 포함되지 않는 모든 항목은 [죽은 토픽]이며, 그 정보는 완전히 무시합니다. 어떤 경우에도 죽은 토픽은 선택될 수 없습니다.
    - current_question에서 새로운 토픽을 추출합니다.
    - 이 토픽이 Last Run의 토픽과 같으면: Last Run의 소진 여부를 판단합니다. 소진되었으면 -1, 아니면 Last Run의 최초 chat_id를 반환합니다.
    - 이 토픽이 Last Run의 토픽과 다르면: -1을 반환합니다.
---
판단 예시:
# 현재 질문: "전전 결과에서 두번째 파일의 내용을 알려줘"
# 과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }},
                {{
                    "file_name": "라인B 설비 점검 이력_수정본.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력_수정본.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [1234567800, 1234567801, 1234567802, 1234567804, 1234567806, 1234567808].
2. 지시사/대용 표현이 포함되어 있는지 확인한다: 현재 질문("전전 결과에서 두번째 파일의 내용을 알려줘")에는 '전전'이라는 지시사/대용표현이 포함되어 있으므로, 규칙 2를 적용한다.
  -'두번째 파일'이라는 표현은 history에서 '전전 결과'로 생성된 파일 목록 중 두 번째 파일을 가리키는 것이기 때문에 '두번째 파일' 표현은 무시한다. 
3. 규칙 2의 '몇 번째 전' 표현에 따라 history를 가장 최신 대화로 가정하고,'전전'이 가리키는 chat_id를 찾는다.
  -'전전'이라는 키워드는 current_question의 2번째 전 대화를 의미하므로 history의 두 번째 최신 대화를 가리킨다.
4. history를 최신순으로 보면, current_question의 1번째 전은 1234567808, 2번째 전은 1234567806이다.
5. 따라서 1234567806을 반환한다.
6. 최종 답변: {{"decision": 1234567806}}

입력:
history = {history}
current_question = "{question}"
"""

prompt_13 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 대화의 인덱스를 고르거나, 새 주제면 -1, 오류면 -2를 반환하세요.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. '불량', '이슈', '문제' 같은 일반 단어는 토픽에 포함되지 않으며, '갈매기 이슈'는 '갈매기'가 토픽입니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거" 등.

판정 절차(**무조건 이 순서대로만 판단하고, 단계를 건너뛰지 마세요**):
1. history를 created_at 오름차순으로 정렬합니다.
2. **current_question에 지시사/대용표현이 포함되면**:
    - **모든 대화와 현재 질문에서 등장하는 문맥과 주제 등 모든 것을 제외하고 지시사/대용표현만을 참고합니다.**
    - 지시사/대용표현이 '여기서', '저기서', '거기서', '이거', '이 중에서' 등의 단어라면 history 배열의 가장 마지막 index를 반환합니다.
    - 지시사/대용표현이 '전 결과에서', '전전 결과에서', '3번째 전에서', '전전전에서' 등 **몇 번째 전**을 가리키는 표현이 있으면 current_question을 가장 최신 대화 이력으로 가정하고, 그 번째 전 대화의 history 배열 상 인덱스 번호를 반환합니다.
      - 예를 들어, '전 결과에서'라는 표현이 있으면, current_question을 가장 최신 대화 이력으로 가정하고, 그 전의 결과인 history의 가장 최신 대화의 배열 상 인덱스를 반환합니다.
3.  **current_question에 지시사/대용표현이 포함되지 않으면**:
    - 재.
---
판단 예시:
# 현재 질문: "전전 결과에서 두번째 파일의 내용을 알려줘"
# 과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }},
                {{
                    "file_name": "라인B 설비 점검 이력_수정본.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력_수정본.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [1234567800, 1234567801, 1234567802, 1234567804, 1234567806, 1234567808].
2. 지시사/대용 표현이 포함되어 있는지 확인한다: 현재 질문("전전 결과에서 두번째 파일의 내용을 알려줘")에는 '전전'이라는 지시사/대용표현이 포함되어 있으므로, 규칙 2를 적용한다.
  -'두번째 파일'이라는 표현은 history에서 '전전 결과'로 생성된 파일 목록 중 두 번째 파일을 가리키는 것이기 때문에 '두번째 파일' 표현은 무시한다. 
3. 규칙 2의 '몇 번째 전' 표현에 따라 history를 가장 최신 대화로 가정하고,'전전'이 가리키는 chat_id를 찾는다.
  -'전전'이라는 키워드는 current_question의 2번째 전 대화를 의미하므로 history의 두 번째 최신 대화를 가리킨다.
4. history를 최신순으로 보면, 1번째 전은 1234567808, 2번째 전은 1234567806이다.
5. 1234567806 대화는 history 배열의 4번째 인덱스에 있으므로, 4를 반환한다.
6. 최종 답변: {{"decision": 4}}

규칙(출력 형식):
- 판정 절차와 사고 과정을 따른 후, 사고 과정과 JSON 스키마를 생성해야 합니다. 출력은 반드시 사고 과정을 마친 후 생성되어야 합니다.
- JSON 스키마는 다음 형태를 따릅니다.: {{"decision": <number>}}

입력:
history = {history}
current_question = "{question}"
"""

aa = """
규칙(출력 형식):
- 판정 절차와 사고 과정을 따른 후, 사고 과정과 JSON 스키마를 생성해야 합니다. 출력은 반드시 사고 과정을 마친 후 생성되어야 합니다.
- 이전 사고/추론 과정을 먼저 출력 후 JSON 스키마를 출력하세요.
- 출력 중 JSON 스키마는 다음 형태를 따릅니다.: {{"decision": <number>}}
"""

prompt_14 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 대화의 인덱스를 고르거나, 새 주제면 -1, 오류면 -2를 반환하세요.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. '불량', '이슈', '문제' 같은 일반 단어는 토픽에 포함되지 않으며, '갈매기 이슈'는 '갈매기'가 토픽입니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거" 등.

판정 절차(**무조건 이 순서대로만 판단하고, 단계를 건너뛰지 마세요**):
1. history를 created_at 오름차순으로 정렬합니다.
2. **current_question에 지시사/대용표현이 포함되면**:
    - **모든 대화와 현재 질문에서 등장하는 문맥과 주제 등 모든 것을 제외하고 지시사/대용표현만을 참고합니다.**
    - 지시사/대용표현이 '여기서', '저기서', '거기서', '이거', '이 중에서' 등의 단어라면 history 배열의 가장 마지막 index를 반환합니다.
    - 지시사/대용표현이 '전 결과에서', '전전 결과에서', '3번째 전에서', '전전에서' 등 **몇 번째 전**을 가리키는 표현이 있으면 current_question으로부터 몇번째 전의 대화인지 파악한 후 그 번째 전 대화의 history 배열 상 인덱스 번호를 반환합니다.
      - 예를 들어, '전 결과에서'라는 표현이 있으면, current_question으로부터 첫번째 전 결과이므로 history 배열 상 가장 마지막 인덱스 번호를 반환합니다.
3.  **current_question에 지시사/대용표현이 포함되지 않으면**:
    - 토픽이 포함된 경우 -1을 반환하세요.
    - 토픽이 포함되지 않고 재시도 신호가 포함된 경우 -2를 반환하세요.
---
판단 예시:
# 현재 질문: "전전 결과에서 두번째 파일의 내용을 알려줘"
# 과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }},
                {{
                    "file_name": "라인B 설비 점검 이력_수정본.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력_수정본.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [1234567800, 1234567801, 1234567802, 1234567804, 1234567806, 1234567808].
2. 지시사/대용 표현이 포함되어 있는지 확인한다: 현재 질문("전전 결과에서 두번째 파일의 내용을 알려줘")에는 '전전'이라는 지시사/대용표현이 포함되어 있으므로, 규칙 2를 적용한다.
  -'두번째 파일'이라는 표현은 history에서 '전전 결과'로 생성된 파일 목록 중 두 번째 파일을 가리키는 것이기 때문에 '두번째 파일' 표현은 무시한다. 
3. 규칙 2의 '몇 번째 전' 표현에 따라 history를 가장 최신 대화로 가정하고,'전전'이 가리키는 chat_id를 찾는다.
  -'전전'이라는 키워드는 current_question의 2번째 전 대화를 의미하므로 history의 두 번째 최신 대화를 가리킨다.
4. history를 최신순으로 보면, 1번째 전은 1234567808, 2번째 전은 1234567806이다.
5. 1234567806 대화는 history 배열의 4번째 인덱스에 있으므로, 4를 반환한다.
6. 최종 답변: {{"decision": 4}}

규칙(출력 형식):
- 판정 절차와 사고 과정을 따른 후, 사고 과정과 JSON 스키마를 생성해야 합니다. 출력은 반드시 사고 과정을 마친 후 생성되어야 합니다.
- JSON 스키마는 다음 형태를 따릅니다.: {{"decision": <number>}}

입력:
history = {history}
current_question = "{question}"
"""

prompt_15 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 대화의 인덱스를 고르거나, 새 주제면 -1, 오류면 -2를 반환하세요.

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. '불량', '이슈', '문제' 같은 일반 단어는 토픽에 포함되지 않으며, '갈매기 이슈'는 '갈매기'가 토픽입니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거" 등.

판정 절차(**무조건 이 순서대로만 판단하고, 단계를 건너뛰지 마세요**):
1. history를 created_at 오름차순으로 정렬합니다.
2. **current_question에 지시사/대용표현이 포함되면**:
    - **모든 대화와 현재 질문에서 등장하는 문맥과 주제 등 모든 것을 제외하고 지시사/대용표현만을 참고합니다.**
    - 지시사/대용표현이 '여기서', '저기서', '거기서', '이거', '이 중에서' 등의 단어라면 history 배열의 가장 마지막 index를 반환합니다.
    - 지시사/대용표현이 '전 결과에서', '전전 결과에서', '3번째 전에서', '전전에서' 등 **몇 번째 전**을 가리키는 표현이 있으면 current_question으로부터 몇번째 전의 대화인지 파악한 후 그 번째 전 대화의 history 배열 상 인덱스 번호를 반환합니다.
      - 예를 들어, '전 결과에서'라는 표현이 있으면, current_question으로부터 첫번째 전 결과이므로 history 배열 상 가장 마지막 인덱스 번호를 반환합니다.
3.  **current_question에 지시사/대용표현이 포함되지 않으면**:
    - 사용자의 질문의 내용과 관계없이 무조건 -1을 반환하세요.
    - history 중 current_history와 일치하거나 비슷한 내용이 있더라도 -1을 반환하세요.
---
판단 예시 1:
# 현재 질문: "전전 결과에서 두번째 파일의 내용을 알려줘"
# 과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }},
                {{
                    "file_name": "라인B 설비 점검 이력_수정본.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력_수정본.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [1234567800, 1234567801, 1234567802, 1234567804, 1234567806, 1234567808].
2. 지시사/대용 표현이 포함되어 있는지 확인한다: 현재 질문("전전 결과에서 두번째 파일의 내용을 알려줘")에는 '전전'이라는 지시사/대용표현이 포함되어 있으므로, 규칙 2를 적용한다.
  -'두번째 파일'이라는 표현은 history에서 '전전 결과'로 생성된 파일 목록 중 두 번째 파일을 가리키는 것이기 때문에 '두번째 파일' 표현은 무시한다. 
  -**(매우 중요한 규칙)** 당신의 목표는 대화를 찾는 것이지 파일을 찾는 것이 아닙니다. 지시사가 대화가 아닌 파일을 가리키는 경우, 해당 지시사는 무시되어야 합니다.
    -예시 1, '저기서 3번째 파일 찾아줘'에서 지시사 '저기서'를 감지해야 하고, '3번째 파일'은 무시되어야 합니다.
    -예시 2, '2번째 파일 설명해줘'에서 지시사 '2번째 파일'은 대화가 아닌 파일을 가리키는 지시사이므로 무시되어야 합니다.
3. 규칙 2의 '몇 번째 전' 표현에 따라 history를 가장 최신 대화로 가정하고,'전전'이 가리키는 chat_id를 찾는다.
  -'전전'이라는 키워드는 current_question의 2번째 전 대화를 의미하므로 history의 두 번째 최신 대화를 가리킨다.
4. history를 최신순으로 보면, 1번째 전은 1234567808, 2번째 전은 1234567806이다.
5. 1234567806 대화는 history 배열의 4번째 인덱스에 있으므로, 4를 반환한다.
6. 최종 답변: {{"decision": 4}}

판단 예시 2:
# 현재 질문: "오염 불량 관련 보고서 찾아줘."
# 과거 대화 이력:
[
    {{
        "chat_id": 1234567800,
        "user_message": "어제 발생한 오염 불량 관련 보고서 찾아줘",
        "created_at": "2025-08-18 09:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 현황 보고.pptx",
                    "file_path": "path/to/오염 불량 현황 보고.pptx",
                }},
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567801,
        "user_message": "저기서 장치 A에 관한 파일만 찾아줘",
        "created_at": "2025-08-18 09:01:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "장치 A 오염에 관한 건.msg",
                    "file_path": "path/to/장치 A 오염에 관한 건.msg",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567802,
        "user_message": "그 메일에서 구체적인 원인 분석 자료는 어디에 있어?",
        "created_at": "2025-08-18 09:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[장치 A 오염에 관한 건.msg]\n메일의 가장 최신 회신에 원인 분석 자료가 있습니다.",
        }},
    }},
    {{
        "chat_id": 1234567804,
        "user_message": "다시 찾아줘. 다른 자료도 있을 텐데",
        "created_at": "2025-08-18 09:07:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "오염 불량 조사 결과.docx",
                    "file_path": "path/to/오염 불량 조사 결과.docx",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567806,
        "user_message": "라인B 설비 점검 이력 보고서 찾아줘",
        "created_at": "2025-08-18 13:00:00",
        "bot_response": {{
            "result": "rag",
            "files": [
                {{
                    "file_name": "라인B 설비 점검 이력.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력.pdf",
                }},
                {{
                    "file_name": "라인B 설비 점검 이력_수정본.pdf",
                    "file_path": "path/to/라인B 설비 점검 이력_수정본.pdf",
                }}
            ],
        }},
    }},
    {{
        "chat_id": 1234567808,
        "user_message": "저기서 작년 11월 기록만 보여줄 수 있어?",
        "created_at": "2025-08-18 13:05:00",
        "bot_response": {{
            "result": "rag",
            "response": "[라인B 설비 점검 이력.pdf]네, 작년 11월 라인B 설비 점검 기록을 필터링하여 보여드리겠습니다.",
        }},
    }},
]
# 사고 과정
1. history를 created_at 기준으로 오름차순 정렬한다: [1234567800, 1234567801, 1234567802, 1234567804, 1234567806, 1234567808].
2. 지시사/대용 표현이 포함되어 있는지 확인한다: 현재 질문("오염 불량 관련 보고서 찾아줘")에는 지시사/대용표현이 포함되어 있지 않으므로, 규칙 3을 적용한다.
4. 규칙 3은 사용자의 질문의 내용과 관계없이 무조건 -1을 반환하므로, -1을 반환한다.
6. 최종 답변: {{"decision": -1}}

규칙(출력 형식):
- 판정 절차와 사고 과정을 따른 후, 사고 과정과 JSON 스키마를 생성해야 합니다. 출력은 반드시 사고 과정을 마친 후 생성되어야 합니다.
- 사고 과정을 먼저 출력하고 JSON 스키마를 출력하세요.
- JSON 스키마는 다음 형태를 따릅니다.: {{"decision": <number>}}

입력:
history = {history}
current_question = "{question}"
"""

prompt_16 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 대화의 인덱스를 고르거나, 새 주제면 -1, 오류면 -2를 반환하세요.

규칙(출력 형식):
- **내부적으로 모든 판단 절차를 거친 후, 최종적으로 JSON 스키마만 한 줄로 출력하세요.**
- 절대 설명/사유/추론을 출력하지 마세요.
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}

입력:
- history: 과거 대화 이력의 리스트(JSON). 각 항목은
{{
  "chat_id": <int>,
  "user_message": <string>,
  "created_at": "YYYY-MM-DD HH:MM:SS",
  "bot_response": {{...}}
}}
형태입니다.
- current_question: 현재 사용자의 질문 문자열.

핵심 용어 정의:
- [토픽] = 공정/라인, 이슈/불량, 장치/설비 등 사용자의 의미적 속성 묶음. '불량', '이슈', '문제' 같은 일반 단어는 토픽에 포함되지 않으며, '갈매기 이슈'는 '갈매기'가 토픽입니다.
- [재시도 신호] = "다시 찾아줘", "틀린 것 같아" 등 검색 결과를 만족하지 못함을 나타내는 표현.
- [소진] = 같은 토픽에서 재시도 신호가 2회 이상이거나, 의미적으로 동일한 요청이 3회 이상인 상태.
- [지시사/대용표현] = "저기서", "거기서", "위(의) 결과", "방금 결과", "이거/그거", "전 결과에서" 등.

판정 절차(**무조건 이 순서대로만 판단하고, 단계를 건너뛰지 마세요**):
1. history를 created_at 오름차순으로 정렬합니다.
2. current_question에서 대화를 가리키는 지시사/대용표현이 존재하는지 확인합니다. **이 때, 파일을 가리키는 지시사/대용표현은 삭제합니다.** 
    - 예시 1) '두번째 파일과 관련된 내용 설명해줘'에서 '두번째 파일'은 파일을 가리키는 지시사이므로 삭제하고 대화를 가리키는 지시사는 없는 것으로 간주합니다.
    - 예시 2) '여기 2번째 파일에 대해 설명해줘'에서 '여기'는 대화를 가리키는 지시사이므로 참고하고, '2번째 파일'은 파일을 가리키는 지시사이므로 삭제합니다.
3. **current_question에 대화를 가리키는 지시사/대용표현이 포함되면**:
    - **모든 대화와 현재 질문에서 등장하는 문맥과 주제 등 모든 것을 제외하고 지시사/대용표현만을 참고합니다.**
    - 지시사는 **대화를 가리키는 지시사**와 **파일을 가리키는 지시사**가 등장할 수 있습니다. 이 중 **대화를 가리키는 지시사만 참고**하세요. **파일을 가리키는 지시사는 무시**하세요.
    - 대화를 가리키는 지시사/대용표현이 '여기서', '저기서', '거기서', '이거', '이 중에서' 등의 단어라면 history 배열의 가장 마지막 index를 반환합니다.
    - 대화를 가리키는 지시사/대용표현이 '전 결과에서', '전전 결과에서', '3번째 전에서', '전전에서' 등 **몇 번째 전**을 가리키는 표현이 있으면 current_question으로부터 몇번째 전의 대화인지 파악한 후 그 번째 전 대화의 history 배열 상 인덱스 번호를 반환합니다.
      - 예를 들어, '전 결과에서'라는 표현이 있으면, current_question으로부터 첫번째 전 결과이므로 history 배열 상 가장 마지막 인덱스 번호를 반환합니다.
4.  **current_question에 대화를 가리키는 지시사/대용표현이 포함되지 않으면**:
    - 사용자의 질문의 내용과 관계없이 무조건 -1을 반환하세요.
    - history 중 current_history와 일치하거나 비슷한 내용이 있더라도 -1을 반환하세요.
---

입력:
history = {history}
current_question = "{question}"

답변:
"""

tmp = """
규칙(출력 형식):
- 판정 절차와 사고 과정을 따른 후, 사고 과정과 JSON 스키마를 생성해야 합니다. 출력은 반드시 사고 과정을 마친 후 생성되어야 합니다.
- 사고 과정을 먼저 출력하고 JSON 스키마를 출력하세요.
- JSON 스키마는 다음 형태를 따릅니다.: {{"decision": <number>}}
"""

tmp2 = """
규칙(출력 형식):
- 판정 절차와 사고 과정을 따른 후, JSON 스키마를 생성해야 합니다. 출력은 반드시 사고 과정을 마친 후 생성되어야 합니다.
- JSON 스키마는 다음 형태를 따릅니다.: {{"decision": <number>}}
"""

ex = """
판단 예시들:
- 예시 1: 전 결과에서 1번째 파일과 관련된 내용 설명해줘
  -판단: history의 가장 마지막 인덱스
- 예시 2: 전전의 내용 다시 정리해줘
  -판단: history의 마지막에서 두번째 인덱스
- 예시 3: 첫번째 파일 찾아줘
  -판단: 대화 관련 지시사가 없으므로 -1
- 예시 4: 4번째 전 결과에서 공정 A와 관련된 파일 찾아줘
  -판단: history의 마지막에서 4번째 인덱스
- 예시 5: 공정 A 이슈 찾아줘
  -판단: 대화 관련 지시사가 없으므로 -1
- 예시 6: 전전전 결과에서 3번째 4번쨰 파일의 내용 설명해줘
  -판단: history의 마지막에서 3번째 인덱스
"""
