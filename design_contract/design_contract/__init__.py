"""
Design & DesignSpace Engine.

Transforma un `CandidateDesign` (propuesto por un generador determinista o
un LLM) en un `Design` formal, validado y trazable — independiente de
dominio. Ver DESIGN_DESIGNSPACE_CONTRACT.md (raíz del repositorio) para la
documentación completa.
"""
from __future__ import annotations

from design_contract.candidate import CandidateDesign
from design_contract.constraints import DesignConstraint
from design_contract.design_space import DesignSpace, DesignSpaceStatus
from design_contract.feasibility import FeasibilityReport, FeasibilityStatus, StructuralFeasibilityChecker
from design_contract.lineage import DesignLineage, LineageEdge
from design_contract.novelty import NoveltyScore, ParameterDistanceNoveltyScorer
from design_contract.objectives import DesignObjective, ObjectiveDirection, ObjectiveVector
from design_contract.relations import CandidateRelation, DesignRelation, validate_candidate_relation
from design_contract.schema import (
    Architecture,
    Component,
    ComponentInterface,
    Design,
    DesignProvenance,
    DesignProvenanceSource,
    DesignStatus,
    Geometry,
    GeometryRepresentationType,
    Material,
    MaterialProperty,
)
from design_contract.search_space import SearchSpace, SearchStrategyKind
from design_contract.validators.pipeline import DesignValidationPipeline
from design_contract.variables import DesignDomain, DesignDomainType, DesignVariable, VariableRole

__all__ = [
    "Design",
    "DesignStatus",
    "DesignProvenance",
    "DesignProvenanceSource",
    "Architecture",
    "Component",
    "ComponentInterface",
    "Geometry",
    "GeometryRepresentationType",
    "Material",
    "MaterialProperty",
    "DesignVariable",
    "DesignDomain",
    "DesignDomainType",
    "VariableRole",
    "DesignRelation",
    "CandidateRelation",
    "validate_candidate_relation",
    "DesignConstraint",
    "DesignObjective",
    "ObjectiveDirection",
    "ObjectiveVector",
    "DesignSpace",
    "DesignSpaceStatus",
    "SearchSpace",
    "SearchStrategyKind",
    "CandidateDesign",
    "DesignValidationPipeline",
    "FeasibilityReport",
    "FeasibilityStatus",
    "StructuralFeasibilityChecker",
    "DesignLineage",
    "LineageEdge",
    "NoveltyScore",
    "ParameterDistanceNoveltyScorer",
]
