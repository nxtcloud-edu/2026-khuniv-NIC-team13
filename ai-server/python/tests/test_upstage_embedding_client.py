import httpx
import pytest

from app.vector.upstage_embedding_client import UpstageEmbeddingClient


def async_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_embeds_query_with_embed_2_query_model():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.upstage.ai/v1/embeddings"
        assert request.headers["Authorization"] == "Bearer up_test"
        assert request.read().decode() == (
            '{"input":"기업: 삼성\\n직무: 백엔드","model":"solar-embedding-2-query"}'
        )
        return httpx.Response(
            200,
            json={
                "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 0.3]}],
                "model": "solar-embedding-2-query",
                "usage": {"prompt_tokens": 8, "total_tokens": 8},
            },
        )

    async with async_client(handler) as client:
        embedder = UpstageEmbeddingClient("up_test", http_client=client)
        result = await embedder.embed_query("기업: 삼성\n직무: 백엔드")

    assert result.embeddings == [[0.1, 0.2, 0.3]]
    assert result.prompt_tokens == 8
    assert result.model == "solar-embedding-2-query"


@pytest.mark.asyncio
async def test_embeds_passages_in_response_index_order():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.read())
        assert payload == {
            "input": ["첫 번째 문서", "두 번째 문서"],
            "model": "solar-embedding-2-passage",
        }
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.3, 0.4]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ],
                "model": "solar-embedding-2-passage",
                "usage": {"prompt_tokens": 12, "total_tokens": 12},
            },
        )

    async with async_client(handler) as client:
        embedder = UpstageEmbeddingClient("up_test", http_client=client)
        result = await embedder.embed_passages(["첫 번째 문서", "두 번째 문서"])

    assert result.embeddings == [[0.1, 0.2], [0.3, 0.4]]
    assert result.prompt_tokens == 12


@pytest.mark.asyncio
async def test_rejects_missing_or_malformed_embedding_data():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": []}]})

    async with async_client(handler) as client:
        embedder = UpstageEmbeddingClient("up_test", http_client=client)
        with pytest.raises(RuntimeError, match="유효한 임베딩"):
            await embedder.embed_query("검색 요청")


@pytest.mark.asyncio
async def test_rejects_more_than_official_batch_limit():
    embedder = UpstageEmbeddingClient("up_test")
    with pytest.raises(ValueError, match="100"):
        await embedder.embed_passages(["문서"] * 101)
    await embedder.aclose()
