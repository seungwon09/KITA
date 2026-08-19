import httpx

from app.core.config import settings


class LocalLlmService:
    async def generate(self, prompt: str) -> str:
        if settings.use_mock_llm:
            return self._mock_generate(prompt)
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    settings.local_llm_url,
                    json={"model": settings.local_llm_model, "prompt": prompt, "stream": False},
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except Exception:
            return self._mock_generate(prompt)

    def _mock_generate(self, prompt: str) -> str:
        return """
[기본 풀이]
문제에서 주어진 값과 구해야 하는 값을 먼저 분리하세요.
사용할 공식이나 핵심 개념을 하나 고른 뒤, 필요한 값만 대입해 계산합니다.

[빠른 풀이]
시험장에서는 문제의 단위와 핵심 조건을 보고 가장 짧은 공식부터 적용하세요.

[오답 이유]
조건을 빠뜨렸거나 부호와 단위를 확인하지 않았을 가능성이 있습니다.

[비슷한 문제]
같은 개념에서 숫자 하나만 바꿔 다시 풀어 보세요.
""".strip()
