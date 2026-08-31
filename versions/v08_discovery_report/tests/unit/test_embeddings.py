import pytest

from core.knowledge.embeddings import HashingEmbedder


@pytest.mark.asyncio
async def test_hashing_embedder_is_deterministic():
    embedder = HashingEmbedder(dim=64)
    v1 = await embedder.embed(["choked flow nozzle throat"])
    v2 = await embedder.embed(["choked flow nozzle throat"])
    assert v1 == v2


@pytest.mark.asyncio
async def test_hashing_embedder_similar_text_more_similar_than_unrelated():
    import numpy as np

    embedder = HashingEmbedder(dim=128)
    [a] = await embedder.embed(["thrust coefficient nozzle throat area"])
    [b] = await embedder.embed(["nozzle throat area thrust performance"])
    [c] = await embedder.embed(["banana smoothie recipe breakfast"])

    def cos(x, y):
        x, y = np.array(x), np.array(y)
        return float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y)))

    assert cos(a, b) > cos(a, c)


@pytest.mark.asyncio
async def test_hashing_embedder_vectors_are_normalized():
    import numpy as np

    embedder = HashingEmbedder(dim=32)
    [v] = await embedder.embed(["some text with several tokens here"])
    assert np.linalg.norm(v) == pytest.approx(1.0, abs=1e-6)
