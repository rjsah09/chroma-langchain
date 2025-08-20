from langchain_core.prompts import PromptTemplate
import history_template
import history_template_2
import requests
import json


def prompt_binder(question: str, history: list) -> str:
    """LangChain 템플릿에 질문과 JSON 직렬화한 history를 바인딩."""
    prompt_template = PromptTemplate.from_template(history_template_2.prompt_4)

    # history를 실제 JSON 문자열로 변환 (한글 보존)
    history_json = json.dumps(history, ensure_ascii=False)

    prompt = prompt_template.format(question=question)
    return prompt


def vllm_requester(prompt: str):
    # ❗ 중복 슬래시 제거
    # url = "http://49.254.228.18:8002/v1/completions"
    url = "http://192.168.0.200:8002/v1/completions"
    headers = {"Content-Type": "application/json"}

    data = {
        # vLLM는 대체로 model 명시를 권장/요구
        "model": "google/gemma-3-27b-it",
        # /v1/completions는 messages가 아니라 prompt를 사용
        "prompt": prompt,
        "max_tokens": 1024,  # completions에서는 max_tokens 사용 권장
        "temperature": 0.1,
        "top_p": 0.3,
        "stream": False,
    }

    resp = requests.post(url, headers=headers, json=data, timeout=60)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    history = [
        {
            "chat_id": 12313223,
            "user_message": "공정 A에서 발생한 B 이슈 찾아줘",
            "created_at": "2025-08-17 19:00:00",
            "bot_response": {
                "result": "rag",
                "files": [
                    {
                        "file_name": "공정 A 불량 리포트.pptx",
                        "file_path": "path/to/공정 A 불량 리포트.pptx",
                    },
                    {
                        "file_name": "B 이슈 발생 건.msg",
                        "file_path": "path/to/B 이슈 발생 건.msg",
                    },
                ],
                "response_time": "2025-08-18 10:00:00",
            },
        },
        {
            "chat_id": 1234567890,
            "user_message": "공정 A에서 발생한 B 이슈 찾아줘",
            "created_at": "2025-08-18 10:00:00",
            "bot_response": {
                "result": "rag",
                "files": [
                    {
                        "file_name": "공정 A 불량 리포트.pptx",
                        "file_path": "path/to/공정 A 불량 리포트.pptx",
                    },
                    {
                        "file_name": "B 이슈 발생 건.msg",
                        "file_path": "path/to/B 이슈 발생 건.msg",
                    },
                ],
                "response_time": "2025-08-18 10:00:00",
            },
        },
        {
            "chat_id": 1234567892,
            "user_message": "각 파일마다 무엇이 오류였는지 알려줘",
            "created_at": "2025-08-18 10:03:00",
            "bot_response": {
                "result": "rag",
                "response": "[공정 A 불량 리포트]\n공정 A에서 B이슈로 인해 C 불량이 발생했습니다. 해결 방법은 D입니다.\n\n[B 이슈 발생 건.msg]\nB 이슈가 발생한 공정들에 대해 조사하고 있으며 현재 밝혀진 바로는 A공정, G공정, F공정, C공정입니다.",
            },
        },
        {
            "chat_id": 1234567894,
            "user_message": "갈매기성 현상이 있는 파일 찾아줘",
            "created_at": "2025-08-18 14:00:00",
            "bot_response": {
                "result": "rag",
                "files": [
                    {
                        "file_name": "장치 AB 이상 현상 리포트.pptx",
                        "file_path": "path/to/장치 AB 이상 현상 리포트.pptx",
                    },
                    {
                        "file_name": "B 이슈 발생 건.msg",
                        "file_path": "path/to/B 이슈 발생 건.msg",
                    },
                    {
                        "file_name": "장치 Z 갈매기 현상 이슈 발생 건.msg",
                        "file_path": "path/to/장치 Z 갈매기 현상 이슈 발생 건.msg",
                    },
                ],
                "response_time": "2025-08-18 14:00:00",
            },
        },
        {
            "chat_id": 1234567896,
            "user_message": "전 결과에서 장치 A와 관련된 파일 찾아줘",
            "created_at": "2025-08-19 10:02:00",
            "bot_response": {
                "result": "rag",
                "files": [
                    {
                        "file_name": "장치 A 이상 현상 리포트.pptx",
                        "file_path": "path/to/장치 A 이상 현상 리포트.pptx",
                    },
                ],
            },
        },
    ]

    prompt = prompt_binder(
        question="방금 결과에서 장치 A 이상.pptx 파일의 내용 중 이상 현상이 정확히 어떻게 발생한 것인지 설명해줘",
        history=history,
    )
    try:
        response = vllm_requester(prompt)
        print(json.dumps(response, ensure_ascii=False, indent=2))
    except requests.HTTPError as e:
        print("HTTPError:", e.response.text)
    except Exception as e:
        print("Error:", repr(e))
