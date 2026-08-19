# 로컬 모델 실행 전략

외부 AI API를 쓰지 않는 기준입니다.

## 개발 단계 추천

1. Ollama
   - 설치와 실행이 쉬움
   - Windows 개발 PC에 적합
   - `qwen2.5:3b`, `qwen2.5:7b`, `gemma2:9b` 같은 모델로 시작

2. vLLM
   - 서버 배포와 동시 요청 처리에 적합
   - NVIDIA GPU 서버에서 운영할 때 추천

3. llama.cpp
   - 저비용 CPU/GPU 혼합 실행에 적합
   - 모바일/엣지 배포 연구에 좋음

## 현재 코드 연결 방식

`app/core/config.py`에서 아래 값을 읽습니다.

```text
USE_MOCK_LLM=false
LOCAL_LLM_URL=http://127.0.0.1:11434/api/generate
LOCAL_LLM_MODEL=qwen2.5:3b
```

Ollama가 실행 중이면 `/solve` 요청이 로컬 모델로 전달됩니다.
