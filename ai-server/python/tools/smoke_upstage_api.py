"""Interactive Upstage Embed 2 query/passage API smoke test."""
import getpass

import httpx

secret_key = getpass.getpass("Upstage Secret key: ").strip()
url = "https://api.upstage.ai/v1/embeddings"

tests = [
    ("solar-embedding-2-query", "삼성전자 백엔드 개발자 지원서"),
    ("solar-embedding-2-passage", "지원자는 데이터 플랫폼 개발 경험이 있습니다."),
]

with httpx.Client(timeout=60) as client:
    for model, text in tests:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {secret_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": text},
        )

        if response.is_error:
            print({"model": model, "status": response.status_code, "error": response.text})
            continue

        result = response.json()
        embedding = result["data"][0]["embedding"]
        print(
            {
                "model": result.get("model", model),
                "dimension": len(embedding),
                "usage": result.get("usage"),
                "success": len(embedding) == 1024,
            }
        )
