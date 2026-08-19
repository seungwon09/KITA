$ErrorActionPreference = "Stop"
Set-Location "C:\Users\user\Documents\Codex\2026-05-20\transformer-pretraining-fine-tuning-rlhf-hallucination"
$env:USE_MOCK_LLM = "false"
$env:LOCAL_LLM_MODEL = "qwen2.5:3b"
& "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 *> server.log
