import pytest

from core.knowledge.schema import Equation, ExtractedFact, RawDocument, Source
from core.knowledge.structured_store import SQLiteStructuredKnowledgeStore, StructuredKnowledgeNotFoundError


@pytest.fixture
def store(tmp_path):
    return SQLiteStructuredKnowledgeStore(tmp_path / "knowledge.db")


def test_source_roundtrip(store):
    src = Source(title="Test Source", publisher="Test Publisher", url="https://example.com")
    store.save_source(src)
    fetched = store.get_source(src.id)
    assert fetched.title == "Test Source"


def test_get_missing_source_raises(store):
    with pytest.raises(StructuredKnowledgeNotFoundError):
        store.get_source("does-not-exist")


def test_document_roundtrip(store):
    src = Source(title="S", publisher="P")
    doc = RawDocument(title="Doc", source=src, summary="resumen propio", domain="satellite.propulsion")
    store.save_document(doc)
    fetched = store.get_document(doc.id)
    assert fetched.title == "Doc"


def test_equations_filtered_by_domain(store):
    eq1 = Equation(
        name="eq1", expression="a=b", variables={}, units={}, source_id="s1", domain="satellite.propulsion"
    )
    eq2 = Equation(name="eq2", expression="c=d", variables={}, units={}, source_id="s2", domain="satellite.thermal")
    store.save_equation(eq1)
    store.save_equation(eq2)

    propulsion_eqs = store.get_equations_for_domain("satellite.propulsion")
    assert len(propulsion_eqs) == 1
    assert propulsion_eqs[0].name == "eq1"


def test_facts_filtered_by_document(store):
    fact = ExtractedFact(document_id="doc1", claim="claim", confidence=0.9, source_id="s1")
    store.save_fact(fact)
    facts = store.get_facts_for_document("doc1")
    assert len(facts) == 1
    assert facts[0].claim == "claim"

    assert store.get_facts_for_document("doc-without-facts") == []
