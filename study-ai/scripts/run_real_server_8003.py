import os
import sys
from pathlib import Path

import uvicorn


project_root = Path(__file__).resolve().parents[1]
os.chdir(project_root)
sys.path.insert(0, str(project_root))

os.environ["USE_MOCK_LLM"] = "false"
os.environ["LOCAL_LLM_MODEL"] = "qwen2.5:3b"
os.environ["PYTHONIOENCODING"] = "utf-8"

uvicorn.run("app.main:app", host="127.0.0.1", port=8003)
