from types import SimpleNamespace

import httpx
import pytest

from app.vector.vector_embedder import VectorEmbedder


@pytest.mark.asyncio
async def test_vector_embedder_uses_openai_embedding_for_search_input():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.openai.com/v1/embeddings"
        payload = __import__("json").loads(request.read())
        assert payload["model"] == "text-embedding-3-small"
        assert payload["input"] == (
            "기업: 삼성전자\n직무: 백엔드 개발자\n\n"
            "질문 1: 지원 동기는?\n답변 1: 데이터 플랫폼 경험을 활용하기 위해 지원했습니다."
        )
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.9]}]})

    settings = SimpleNamespace(openai_api_key="sk_test")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        embedder = VectorEmbedder(http_client=client, settings=settings)
        result = await embedder.create_embedding(
            "삼성전자",
            "백엔드 개발자",
            ["지원 동기는?"],
            ["데이터 플랫폼 경험을 활용하기 위해 지원했습니다."],
        )

    assert result == [0.9]
