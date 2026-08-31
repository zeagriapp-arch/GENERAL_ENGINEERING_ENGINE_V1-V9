"""
Conocimiento curado manualmente para el dominio satellite.propulsion,
caso cold-gas thruster (decisión #7 confirmada). Fuentes públicas
(NASA Glenn Research Center — contenido de agencia gubernamental de EE.UU.,
de dominio público; y Wikipedia para definiciones estándar). Los resúmenes
están escritos en palabras propias — NO son copias de las páginas fuente.

Ejecutar: python -m domains.satellite.propulsion.knowledge.seed_knowledge
"""
from __future__ import annotations

import asyncio

from core.knowledge.engine import KnowledgeEngine
from core.knowledge.embeddings import HashingEmbedder
from core.knowledge.schema import Equation, ExtractedFact, RawDocument, Source
from core.knowledge.structured_store import SQLiteStructuredKnowledgeStore
from core.knowledge.vector_store import SQLiteCosineVectorStore

DOMAIN = "satellite.propulsion"

# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

SRC_THRUST_EQ = Source(
    id="nasa-grc-rocket-thrust-eq",
    title="Rocket Thrust Equations",
    publisher="NASA Glenn Research Center",
    url="https://www.grc.nasa.gov/WWW/K-12/BGP/rktthsum.html",
)

SRC_SPECIFIC_IMPULSE = Source(
    id="nasa-grc-specific-impulse",
    title="Specific Impulse",
    publisher="NASA Glenn Research Center",
    url="https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/specific-impulse/",
)

SRC_THRUST_SUMMARY = Source(
    id="nasa-grc-thrust-equations-summary",
    title="Thrust Equations Summary",
    publisher="NASA Glenn Research Center",
    url="https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/thrust-equations-summary/",
)

SRC_NOZZLE_DESIGN = Source(
    id="nasa-grc-nozzle-design",
    title="Nozzle Design",
    publisher="NASA Glenn Research Center",
    url="https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/nozzle-design/",
)

SRC_WIKI_CSTAR = Source(
    id="wikipedia-characteristic-velocity",
    title="Characteristic velocity",
    publisher="Wikipedia",
    url="https://en.wikipedia.org/wiki/Characteristic_velocity",
)

SRC_WIKI_CF = Source(
    id="wikipedia-thrust-coefficient",
    title="Thrust coefficient",
    publisher="Wikipedia",
    url="https://en.wikipedia.org/wiki/Thrust_Coefficient",
)

ALL_SOURCES = [
    SRC_THRUST_EQ,
    SRC_SPECIFIC_IMPULSE,
    SRC_THRUST_SUMMARY,
    SRC_NOZZLE_DESIGN,
    SRC_WIKI_CSTAR,
    SRC_WIKI_CF,
]

# ---------------------------------------------------------------------------
# Documents (resúmenes en palabras propias, no copiados de la fuente)
# ---------------------------------------------------------------------------

DOC_THRUST_EQ = RawDocument(
    id="doc-thrust-equation",
    title="Ecuación general de empuje de cohete",
    source=SRC_THRUST_EQ,
    domain=DOMAIN,
    summary=(
        "El empuje de un motor cohete (incluye thrusters de gas frío) se "
        "produce por la tercera ley de Newton al acelerar el gas de escape "
        "a través de una tobera. Como no se toma aire del entorno, la "
        "ecuación de empuje no tiene término de flujo libre entrante: el "
        "empuje depende solo del flujo másico de salida, la velocidad de "
        "salida, y la diferencia entre presión de salida y presión ambiente "
        "actuando sobre el área de salida."
    ),
)

DOC_SPECIFIC_IMPULSE = RawDocument(
    id="doc-specific-impulse",
    title="Impulso específico (Isp)",
    source=SRC_SPECIFIC_IMPULSE,
    domain=DOMAIN,
    summary=(
        "El impulso específico mide la eficiencia de un propulsor: es el "
        "empuje producido por unidad de peso de propelente consumido por "
        "segundo. Tiene unidades de tiempo (segundos) y permite comparar "
        "motores de tamaños distintos de forma independiente de escala. Es "
        "una de las métricas de objetivo más comunes al optimizar un "
        "diseño de propulsión."
    ),
)

DOC_CHOKED_FLOW = RawDocument(
    id="doc-choked-flow",
    title="Flujo másico atorado (choked flow) en la garganta de la tobera",
    source=SRC_THRUST_SUMMARY,
    domain=DOMAIN,
    summary=(
        "En una tobera convergente-divergente, el área mínima (garganta) "
        "limita el flujo másico que puede pasar: cuando el número de Mach "
        "en la garganta llega a 1, el flujo queda 'atorado' y el flujo "
        "másico depende solo del área de garganta, la presión y "
        "temperatura totales de la cámara, y las propiedades del gas "
        "(razón de calores específicos y constante de gas). Aumentar la "
        "presión aguas abajo de la garganta no incrementa más el flujo "
        "másico una vez que está atorado."
    ),
)

DOC_ISENTROPIC_EXIT = RawDocument(
    id="doc-isentropic-exit-relations",
    title="Relaciones isentrópicas de salida y razón de áreas",
    source=SRC_THRUST_SUMMARY,
    domain=DOMAIN,
    summary=(
        "Aguas abajo de la garganta, el flujo se expande isentrópicamente "
        "(sin pérdidas) hasta un número de Mach de salida que depende de "
        "la razón entre el área de salida y el área de garganta. Esa razón "
        "de áreas determina tanto la presión de salida como la temperatura "
        "de salida, que a su vez determinan la velocidad de salida del gas."
    ),
)

DOC_NOZZLE_QUALITATIVE = RawDocument(
    id="doc-nozzle-design-qualitative",
    title="Comportamiento cualitativo de una tobera convergente-divergente",
    source=SRC_NOZZLE_DESIGN,
    domain=DOMAIN,
    summary=(
        "Si la sección convergente no logra atorar el flujo en la "
        "garganta, la velocidad de salida es baja y el empuje resultante "
        "es pobre. Si el flujo sí se atora, un pequeño incremento de área "
        "aguas abajo de la garganta acelera el flujo a régimen supersónico "
        "— comportamiento opuesto al de un flujo subsónico en un ducto "
        "divergente. Este es el principio detrás del diseño convergente-"
        "divergente usado en toberas de gas frío."
    ),
)

DOC_CSTAR_CF = RawDocument(
    id="doc-cstar-thrust-coefficient",
    title="Velocidad característica (c*) y coeficiente de empuje (CF)",
    source=SRC_WIKI_CSTAR,
    domain=DOMAIN,
    summary=(
        "La velocidad característica c* mide el desempeño de la cámara de "
        "combustión/almacenamiento de gas independientemente de la tobera "
        "— depende de la presión de cámara, el área de garganta, y el "
        "flujo másico. El coeficiente de empuje CF mide el desempeño de la "
        "tobera en sí, independientemente de la fuente de gas. El producto "
        "de ambos, dividido por la gravedad estándar, da el impulso "
        "específico total del sistema."
    ),
)

ALL_DOCUMENTS = [
    DOC_THRUST_EQ,
    DOC_SPECIFIC_IMPULSE,
    DOC_CHOKED_FLOW,
    DOC_ISENTROPIC_EXIT,
    DOC_NOZZLE_QUALITATIVE,
    DOC_CSTAR_CF,
]

# ---------------------------------------------------------------------------
# Equations (sección 13/8 — validity_range y assumptions explícitos)
# ---------------------------------------------------------------------------

EQ_THRUST = Equation(
    id="eq-thrust-general",
    name="Ecuación general de empuje",
    expression="F = mdot * Ve + (pe - p0) * Ae",
    variables={
        "F": "empuje",
        "mdot": "flujo másico de propelente",
        "Ve": "velocidad de salida del gas",
        "pe": "presión estática de salida",
        "p0": "presión ambiente",
        "Ae": "área de salida de la tobera",
    },
    units={"F": "N", "mdot": "kg/s", "Ve": "m/s", "pe": "Pa", "p0": "Pa", "Ae": "m^2"},
    assumptions=["Flujo 1-D estacionario", "No hay ingesta de aire externo (motor cohete/gas frío)"],
    source_id=SRC_THRUST_EQ.id,
    domain=DOMAIN,
)

EQ_ISP = Equation(
    id="eq-specific-impulse",
    name="Impulso específico",
    expression="Isp = F / (mdot * g0)",
    variables={"Isp": "impulso específico", "F": "empuje", "mdot": "flujo másico", "g0": "gravedad estándar"},
    units={"Isp": "s", "F": "N", "mdot": "kg/s", "g0": "m/s^2"},
    assumptions=["g0 = 9.80665 m/s^2 (constante estándar, no la gravedad local)"],
    source_id=SRC_SPECIFIC_IMPULSE.id,
    domain=DOMAIN,
)

EQ_CHOKED_MDOT = Equation(
    id="eq-choked-mass-flow",
    name="Flujo másico atorado en la garganta",
    expression="mdot = (At * pt / sqrt(Tt)) * sqrt(gamma / R) * ((gamma + 1) / 2) ** (-(gamma + 1) / (2 * (gamma - 1)))",
    variables={
        "mdot": "flujo másico",
        "At": "área de garganta",
        "pt": "presión total (de cámara)",
        "Tt": "temperatura total (de cámara)",
        "gamma": "razón de calores específicos del gas",
        "R": "constante específica del gas",
    },
    units={"mdot": "kg/s", "At": "m^2", "pt": "Pa", "Tt": "K", "gamma": "", "R": "J/(kg*K)"},
    assumptions=["Flujo isentrópico", "Mach = 1 exactamente en la garganta (flujo atorado)"],
    source_id=SRC_THRUST_SUMMARY.id,
    domain=DOMAIN,
)

EQ_EXIT_PRESSURE_RATIO = Equation(
    id="eq-exit-pressure-ratio",
    name="Relación isentrópica de presión de salida",
    expression="pe / pt = (1 + Me**2 * (gamma - 1) / 2) ** (-gamma / (gamma - 1))",
    variables={"pe": "presión de salida", "pt": "presión total", "Me": "número de Mach de salida", "gamma": "razón de calores específicos"},
    units={"pe": "Pa", "pt": "Pa", "Me": "", "gamma": ""},
    assumptions=["Flujo isentrópico entre cámara y salida"],
    source_id=SRC_THRUST_SUMMARY.id,
    domain=DOMAIN,
)

EQ_CSTAR = Equation(
    id="eq-characteristic-velocity",
    name="Velocidad característica (c*)",
    expression="c_star = pt * At / mdot",
    variables={"c_star": "velocidad característica", "pt": "presión de cámara", "At": "área de garganta", "mdot": "flujo másico"},
    units={"c_star": "m/s", "pt": "Pa", "At": "m^2", "mdot": "kg/s"},
    assumptions=["Independiente del diseño de la tobera aguas abajo de la garganta"],
    source_id=SRC_WIKI_CSTAR.id,
    domain=DOMAIN,
)

EQ_THRUST_COEFFICIENT = Equation(
    id="eq-thrust-coefficient",
    name="Coeficiente de empuje (CF)",
    expression="CF = F / (pt * At)",
    variables={"CF": "coeficiente de empuje", "F": "empuje", "pt": "presión de cámara", "At": "área de garganta"},
    units={"CF": "", "F": "N", "pt": "Pa", "At": "m^2"},
    assumptions=["Adimensional; mide desempeño de la tobera independientemente de la combustión/fuente de gas"],
    source_id=SRC_WIKI_CF.id,
    domain=DOMAIN,
)

ALL_EQUATIONS = [EQ_THRUST, EQ_ISP, EQ_CHOKED_MDOT, EQ_EXIT_PRESSURE_RATIO, EQ_CSTAR, EQ_THRUST_COEFFICIENT]

# ---------------------------------------------------------------------------
# Extracted facts curados (valores/rangos típicos citables — sección 7)
# ---------------------------------------------------------------------------

ALL_FACTS = [
    ExtractedFact(
        document_id=DOC_ISENTROPIC_EXIT.id,
        claim="El número de Mach es exactamente 1.0 en la garganta cuando el flujo está atorado.",
        extracted_value=1.0,
        unit=None,
        confidence=0.95,
        source_id=SRC_THRUST_SUMMARY.id,
    ),
    ExtractedFact(
        document_id=DOC_SPECIFIC_IMPULSE.id,
        claim="Gravedad estándar g0 usada para definir Isp.",
        extracted_value=9.80665,
        unit="m/s^2",
        confidence=0.99,
        source_id=SRC_SPECIFIC_IMPULSE.id,
    ),
]


async def seed(db_prefix: str = "gede_knowledge") -> KnowledgeEngine:
    engine = KnowledgeEngine(
        vector_store=SQLiteCosineVectorStore(f"{db_prefix}.vectors.db"),
        structured_store=SQLiteStructuredKnowledgeStore(f"{db_prefix}.db"),
        embedder=HashingEmbedder(),
    )
    for doc in ALL_DOCUMENTS:
        await engine.ingest_document(doc, doc.summary)
    for eq in ALL_EQUATIONS:
        engine.save_equation(eq)
    for fact in ALL_FACTS:
        engine.save_fact(fact)
    return engine


if __name__ == "__main__":
    asyncio.run(seed())
    print("Knowledge base sembrada: gede_knowledge.db + gede_knowledge.vectors.db")
