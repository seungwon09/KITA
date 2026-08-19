# Study AI MVP

외부 AI API 없이, 로컬/자체 서버 모델을 붙일 수 있게 설계한 공부앱 AI 백엔드 MVP입니다.

## 첫 목표

사진 또는 문제 텍스트를 받아서:

- 문제 유형 분석
- 기본 풀이
- 빠른 풀이
- 오답 이유
- 비슷한 문제 생성

을 반환하는 구조를 만듭니다.

## 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API 문서:

```text
http://127.0.0.1:8000/docs
```

## 구조

```text
app/
  main.py                 FastAPI 진입점
  core/config.py          설정
  models/schemas.py       요청/응답 스키마
  services/ocr.py         OCR 어댑터
  services/llm.py         로컬 LLM 어댑터
  services/rag.py         지식 검색/RAG
  services/problem_ai.py  문제풀이 AI 파이프라인
  data/knowledge_base.json 기본 지식/풀이 패턴
```

## 다음 단계

1. 로컬 LLM 실행 서버 연결: Ollama, vLLM, llama.cpp 중 선택
2. OCR 연결: PaddleOCR 또는 수식 OCR
3. 문제/풀이 데이터 DB화
4. 사용자별 오답/시간 기록 저장
5. LoRA 파인튜닝 데이터셋 생성
