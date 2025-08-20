prompt_1 = """
You are a decision making assistant.  
Your goal is to determine whether the user's current question refers to a past conversation in the dialogue history.  
You must output ONLY one JSON object in the format: {{"decision": number}}.  

---

## Step-by-step reasoning rules (CoT):
1. **Sort history by created_at in ascending order.**  
   Each history item has an index based on this order. (0 = oldest, N = latest).  

2. **Check if the current_question contains any "referential expressions" (지시사/대용 표현).**  
   Examples of referential expressions pointing to **dialogue** (NOT files):  
   - "여기서", "저기서", "그 결과에서", "전 결과에서", "전전 결과에서", "방금 결과에서", "2번째 전 결과에서", "3번째 전 결과에서"  

3. **Ignore expressions that refer to files, not conversations.**  
   - If user says "첫번째 파일", "두번째 파일", "파일에서", this is a file reference → IGNORE.  
   - Only detect expressions that explicitly refer to the *dialogue itself*.  

4. **If a valid dialogue referential expression exists:**  
   - "여기서", "저기서", "그 결과에서", "방금 결과에서" → refers to the most recent dialogue (latest index).  
   - "전 결과에서" → 1 step back (1st previous dialogue).  
   - "전전 결과에서" or "2번째 전 결과에서" → 2 steps back (2nd previous dialogue).  
   - "3번째 전 결과에서" → 3 steps back, etc.  

   Count backwards from the most recent dialogue.  
   Example: if history has indices [0,1,2,3,4,5], the latest dialogue is index 5.  
   "전전 결과" means index 3.  

5. **If NO valid dialogue referential expression exists:**  
   Always return {{"decision": -1}}.  
   (Do not consider question content or topic at all.)  

---

## Output constraints:
- Only output one JSON object: {{"decision": integer}}  
- Never output explanations or extra text.  
- If multiple rules seem possible, strictly follow the referential-expression rule.  

---

## Examples:

### Example 1
current_question: "전전 결과에서 두번째 파일의 내용을 알려줘"  
history: [ ... ]  
Reasoning: "전전 결과에서" → refers to 2nd previous dialogue. Ignore "두번째 파일".  
Output: {{"decision": 4}}

### Example 2
current_question: "오염 불량 관련 보고서 찾아줘"  
history: [ ... ]  
Reasoning: No dialogue referential expression.  
Output: {{"decision": -1}}

---

Now, follow the above reasoning step by step and output ONLY the JSON result.

Input:
history: {history}
current_question: {question}
"""


prompt_2 = """
You are a decision making assistant in STRICT MODE.

Your single job:
- Decide whether the user's current question literally refers to a past DIALOGUE in the given history.
- You must output ONLY one JSON object: {{\"decision\": number}}

ABSOLUTE CONSTRAINTS (STRICT MODE):
- You MUST look ONLY at literal tokens present in current_question to detect dialogue-referential expressions.
- You MUST NOT infer intent from topic, context, history contents, or prior patterns.
- If current_question does NOT contain any of the DIALOGUE markers listed below (exact or pattern-matched), you MUST output {{\"decision\": -1}}.
- File-referential phrases MUST be ignored and MUST NOT cause a decision other than -1 unless a valid dialogue marker ALSO appears.

DIALOGUE markers (Korean):
A) Latest dialogue (offset = 0):
   - "여기서", "저기서", "그 결과에서", "그 결과", "방금 결과에서", "방금 결과"
B) Previous dialogues:
   - offset = 1: "전 결과에서", "전 결과"
   - offset = 2: "전전 결과에서", "전전 결과", "2번째 전 결과에서", "2번째 전 결과", "두번째 전 결과에서", "두번째 전 결과", "2번 전", "두 번 전"
   - offset = n (n>=3): "<n>번째 전 (결과|대화)(에서)?", "<한글서수>번째 전 (결과|대화)(에서)?", "<n> 번 전"
     - Allowed numerals: 3,4,5,6,7,8,9
     - Allowed Korean ordinals: 세, 셋, 네, 넷, 다섯, 여섯, 일곱, 여덟, 아홉  (예: "세 번째 전 결과", "네번째 전 대화")
C) If BOTH a dialogue marker and a file marker appear, IGNORE the file marker and use ONLY the dialogue marker.

FILE markers to IGNORE (do NOT treat as dialogue markers):
- "첫번째 파일", "두번째 파일", "세번째 파일", "<숫자>번째 파일", "파일에서", "파일 자체", "파일 목록"

INDEXING RULES:
1) Sort history by created_at ASC. Its indices are 0..N (0=oldest, N=latest).
2) If a dialogue marker is present:
   - offset=0 → target_index = N (latest)
   - offset=k → target_index = N - k
   - If target_index is out of range (<0 or >N), output {{\"decision\": -1}}.
3) If NO dialogue marker is present, output {{\"decision\": -1}}.
4) **current_question에 지시사/대용표현이 포함되지 않으면**:
   - **(강조)** 이 경우, history 내용과 관계없이 무조건 -1을 반환하세요.
   - **(강조)** 현재 질문에 새로운 토픽이 명시적으로 포함되어 있더라도, 지시사가 없으면 무조건 -1을 반환하세요.

PROCESS (CoT - keep it internal; do NOT reveal):
1) Extract literal dialogue markers from current_question using ONLY the list/patterns above.
2) If none found → return {{\"decision\": -1}} immediately.
3) Resolve offset as defined.
4) Compute target_index with history length.
5) If out of range → {{\"decision\": -1}}; else → {{\"decision\": target_index}}.

OUTPUT:
- Only one JSON object. No prose, no markdown, no code fences.
- Format exactly: {{\"decision\": INTEGER}}

NEGATIVE EXAMPLES (these MUST yield -1):
- "장치 A와 관련된 파일 찾아줘"
- "2번째 파일 내용만 알려줘"
- "파일에서 전 결과 정리해줘"  (file marker only, no dialogue marker)

POSITIVE EXAMPLES (dialogue markers drive the index; file phrases ignored):
- "전 결과에서 두번째 파일 내용 알려줘" → offset=1
- "전전 결과에서 3번째 파일과 관련된 내용" → offset=2
- "세 번째 전 결과에서 확인한 결론 다시 보여줘" → offset=3

Now, follow the rules above and output ONLY the JSON.

Input:
history: {history}
current_question: {question}
"""

prompt_3 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 아래 입력으로부터 "현재 질문이 이어가야 할 과거 대화의 인덱스"를 고르거나, 새 주제면 -1을 반환하세요.

규칙(출력 형식):
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <number>}}
- 절대 설명/사유/추론을 출력하지 마세요.

---
### 최우선 규칙: 지시사 유무에 따른 판단 (엄격 모드)

1.  **지시사가 있는 경우**:
    -   `current_question`에 아래 리스트의 **어떤 지시사라도 포함되면**, **다른 모든 문맥과 토픽은 무시하고 오직 지시사만을 기준으로 판단합니다.**
    -   **다른 모든 규칙(토픽, 소진 여부 등)은 무시됩니다.**

2.  **지시사가 없는 경우**:
    -   `current_question`에 아래 리스트의 지시사가 **전혀 없다면**, **history의 내용과 관계없이 무조건 -1을 반환합니다.**

---
### 지시사 목록 및 인덱싱 규칙

history는 `created_at` 순으로 오름차순 정렬되어 있으며, 인덱스는 `0`부터 시작합니다.

* **가장 최근 대화 (index = history.length - 1)**
    * "여기서", "저기서", "방금 전", "그 결과에서", "이거", "그거"

* **직전 대화 (index = history.length - 2)**
    * "전 결과에서", "전 결과", "전 대화"

* **2번째 직전 대화 (index = history.length - 3)**
    * "전전 결과에서", "전전 결과", "2번째 전", "두 번 전"

* **`n`번째 전 대화 (index = history.length - 1 - n)**
    * `<숫자>번째 전` (예: "3번째 전", "5번째 전")

---
### 예시

* **현재 질문**: "전 결과에서 장치 A와 관련된 파일 찾아줘"
    * **판단**: "전 결과에서" 지시사 발견. 이는 직전 대화를 의미(인덱스 = `history.length - 2`).
* **현재 질문**: "파일에서 전 결과를 정리해줘"
    * **판단**: "파일에서"는 지시사가 아님. "전 결과"가 포함되어 있지만, 문장 구조가 지시사 목록과 일치하지 않으므로 무시. -> -1 반환.
* **현재 질문**: "이슈 B에 대해 설명해줘"
    * **판단**: 지시사 없음. 토픽과 관계없이 무조건 -1 반환.

---
입력:
history: {history}
current_question: {question}

답변:
"""

prompt_4 = """
당신은 질의 라우팅을 결정하는 시스템입니다. 현재 질문이 **직전 대화**를 가리키면 `true`, 아니면 `false`를 반환하세요.

규칙(출력 형식):
- 출력은 반드시 아래 JSON 스키마 "한 줄"만: {{"decision": <boolean>}}
- 절대 설명/사유/추론을 출력하지 마세요.
- 출력은 반드시 `true` 또는 `false`여야 합니다.

---
### 판단 규칙 (엄격 모드)

1.  **최우선 규칙**: `current_question`에 **대화 지시사가 포함되어 있다면, 파일 지시사를 포함한 다른 모든 문구는 무시하고 오직 대화 지시사만을 기준으로 판단합니다.**

2.  **대화 지시사**:
    -   `current_question`에 아래 지시사 중 하나라도 포함되어 있다면 무조건 `true`를 반환합니다.
        -   "여기서", "저기서", "그 결과에서", "방금 전 결과에서", "이전 결과에서"
        -   "이거", "그거"

3.  **대화 지시사 외의 경우**:
    -   `current_question`에 위 목록의 대화 지시사가 **전혀 없다면** 무조건 `false`를 반환합니다.
    -   아래 파일 지시사는 **절대 대화 지시사로 간주하지 않습니다.**
        -   "첫번째 파일", "두번째 파일", "세번째 파일", "<숫자>번째 파일"
        -   "파일에서", "파일 자체", "파일 목록"

4.  **예외 처리**:
    -   질문 내용이 과거 대화의 토픽과 유사하더라도, 대화 지시사가 없으면 무조건 `false`를 반환합니다.
    -   "전전", "3번째 전"과 같은 **직전이 아닌 지시사는 모두 무시하고** `false`를 반환합니다.

---
### 예시

* **TRUE 반환 예시 (대화 지시사 우선)**:
    -   "여기서 두 번째 파일의 내용을 알려줘" -> **"여기서"** 지시사가 있으므로 `true`
    -   "이전 결과에서 확인한 내용 다시 보여줘" -> **"이전 결과에서"** 지시사가 있으므로 `true`

* **FALSE 반환 예시 (대화 지시사 없음)**:
    -   "전전 결과에서 두 번째 파일 내용 알려줘" -> **"전전"은 직전 대화 지시사가 아니므로** `false`
    -   "두번째 파일 내용만 알려줘" -> **"두번째 파일"**은 파일 지시사이므로 `false`
    -   "새로운 라인에 대해 찾아줘" -> 지시사 없음. `false`
    -   "공정 A 이슈에 대해 설명해줘" -> 지시사 없음. `false`

---
Input:
current_question: {question}

답변:
"""
