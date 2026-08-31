import pytest

from core.knowledge.vector_store import SQLiteCosineVectorStore


@pytest.fixture
def store(tmp_path):
    return SQLiteCosineVectorStore(tmp_path / "vectors.db")


def test_add_and_query_returns_closest_first(store):
    store.add("a", [1.0, 0.0, 0.0], {"label": "a"})
    store.add("b", [0.0, 1.0, 0.0], {"label": "b"})
    store.add("c", [0.9, 0.1, 0.0], {"label": "c"})

    results = store.query([1.0, 0.0, 0.0], top_k=2)
    ids = [r[0] for r in results]

    assert ids[0] == "a"  # idéntico al query -> similitud máxima
    assert "c" in ids  # más cercano a 'a' que 'b'
    assert "b" not in ids  # top_k=2 excluye el más lejano


def test_query_empty_store_returns_empty(store):
    assert store.query([1.0, 0.0], top_k=5) == []


def test_add_is_upsert(store):
    store.add("x", [1.0, 0.0], {"v": 1})
    store.add("x", [0.0, 1.0], {"v": 2})
    results = store.query([0.0, 1.0], top_k=1)
    assert results[0][2]["v"] == 2
