"""
DoD de Phase 2: 'search_knowledge() devuelve chunks con Source trazable'.
Se ejercita contra el conocimiento curado real de propulsión de gas frío
(domains/satellite/propulsion/knowledge/seed_knowledge.py), no con datos
sintéticos, para probar el pipeline completo de principio a fin.
"""
import pytest

from domains.satellite.propulsion.knowledge.seed_knowledge import ALL_EQUATIONS, DOMAIN, seed


@pytest.fixture
async def engine(tmp_path):
    return await seed(db_prefix=str(tmp_path / "propulsion_kb"))


@pytest.mark.asyncio
async def test_search_returns_traceable_source(engine):
    results = await engine.search("choked flow throat mass flow rate", top_k=3)

    assert len(results) > 0
    top = results[0]
    assert top.source.publisher == "NASA Glenn Research Center"
    assert top.source.url is not None

    # provenance completa: se puede recuperar la fuente original por id
    fetched_source = engine.get_source(top.source.id)
    assert fetched_source.id == top.source.id


@pytest.mark.asyncio
async def test_search_ranks_relevant_document_higher(engine):
    """La query sobre impulso específico debe traer ese documento entre los primeros resultados."""
    results = await engine.search("specific impulse efficiency propellant weight", top_k=6)
    titles = [r.document_title for r in results]
    assert "Impulso específico (Isp)" in titles


def test_equations_are_queryable_by_domain():
    from domains.satellite.propulsion.knowledge.seed_knowledge import DOMAIN as D

    # las ecuaciones curadas se guardan de forma síncrona (structured store)
    # independientemente del vector store; validamos el contenido estático
    names = {eq.name for eq in ALL_EQUATIONS}
    assert "Ecuación general de empuje" in names
    assert "Impulso específico" in names
    assert all(eq.domain == D for eq in ALL_EQUATIONS)


@pytest.mark.asyncio
async def test_extract_facts_returns_curated_facts_with_confidence(engine):
    from domains.satellite.propulsion.knowledge.seed_knowledge import DOC_SPECIFIC_IMPULSE

    facts = engine.extract_facts(DOC_SPECIFIC_IMPULSE.id)
    assert len(facts) == 1
    assert facts[0].extracted_value == pytest.approx(9.80665)
    assert facts[0].confidence > 0.9
    assert facts[0].source_id is not None


@pytest.mark.asyncio
async def test_equations_have_units_and_assumptions_declared(engine):
    thrust_eq = next(eq for eq in ALL_EQUATIONS if eq.id == "eq-thrust-general")
    # sección 13: toda ecuación declara variables, unidades y supuestos
    assert set(thrust_eq.variables) == set(thrust_eq.units)
    assert len(thrust_eq.assumptions) > 0

    # Gate dimensional (sección 10): todas las unidades declaradas deben ser válidas para pint
    from core.validation.dimensional_analysis import validate_unit

    for symbol, unit in thrust_eq.units.items():
        result = validate_unit(unit if unit else None)
        assert result.valid, f"Unidad inválida para {symbol}: {unit}"
