"""
`DesignRelation` / `CandidateRelation` (secciones 10, 11, 31).

`volume = f(radius, length)`: una variable derivada nunca debe tratarse
como independiente si su valor puede calcularse determinísticamente. El
LLM puede PROPONER una relación (`CandidateRelation`), pero nunca tiene
autoridad para ejecutarla directamente — sección 31, regla de seguridad
más estricta de toda esta fase.

Mecanismo de seguridad: `_SafeEvaluator` recorre el AST de la expresión
(`ast.parse(expr, mode="eval")`) con una política de **denegación por
defecto** — cada tipo de nodo debe tener un `visit_*` explícito o se
rechaza (`UnsafeExpressionError`). No hay `eval()`/`exec()` en ningún
punto de este módulo. Solo se permiten:

- Literales numéricos/booleanos.
- Nombres de variable (`Name`) que existan en el namespace provisto.
- Operadores aritméticos (`+ - * / // % **`) y de comparación
  (`< <= > >= == !=`).
- Llamadas a funciones POR NOMBRE SIMPLE (nunca `obj.attr(...)`,
  nunca `obj[...]`) que estén en un registro explícito de funciones
  seguras (`_DEFAULT_SAFE_FUNCTIONS` + `register_relation_function()` —
  mismo patrón de extensión que `dimensional_validator.register_parameter_dimension`
  de `requirement_contract`).

Cualquier otra construcción (atributos, subíndices, comprensiones,
lambdas, imports, f-strings, `__dunder__`, etc.) se rechaza porque
simplemente no existe un `visit_*` para ella — no hace falta enumerar una
lista negra, que siempre corre el riesgo de quedar incompleta.
"""
from __future__ import annotations

import ast
import math
import operator
from typing import Callable, Optional

from pydantic import BaseModel, Field
from requirement_contract.schema import Provenance

from design_contract.schema import new_id


class UnsafeExpressionError(ValueError):
    """La expresión usa una construcción del lenguaje no permitida por el DSL seguro."""


class ExpressionEvaluationError(ValueError):
    """La expresión es sintácticamente segura pero no se pudo evaluar (variable faltante, etc.)."""


_SAFE_BINARY_OPERATORS: dict[type, Callable] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_SAFE_UNARY_OPERATORS: dict[type, Callable] = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_SAFE_COMPARE_OPERATORS: dict[type, Callable] = {
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}

_DEFAULT_SAFE_FUNCTIONS: dict[str, Callable] = {
    "min": min,
    "max": max,
    "abs": abs,
    "sqrt": math.sqrt,
    "sum": lambda *args: sum(args),
    "pow": pow,
    "round": round,
}
_registered_functions: dict[str, Callable] = dict(_DEFAULT_SAFE_FUNCTIONS)


def register_relation_function(name: str, func: Callable) -> None:
    """
    Punto de extensión explícito (ej. un futuro Domain Pack registrando
    `minimum_thickness(diameter)`) — nunca se registra ejecutando texto
    propuesto por un LLM, solo código Python de confianza del propio
    proyecto. No se usa en esta fase por ningún dominio concreto.
    """
    _registered_functions[name] = func


class _SafeEvaluator(ast.NodeVisitor):
    """Denegación por defecto: cualquier nodo sin `visit_*` explícito se rechaza."""

    def __init__(self, namespace: dict[str, float]):
        self.namespace = namespace

    def visit(self, node: ast.AST):
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is None:
            raise UnsafeExpressionError(f"Construcción no permitida en la expresión: {type(node).__name__}")
        return method(node)

    def visit_Expression(self, node: ast.Expression):
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, complex):
            return node.value
        if isinstance(node.value, bool):
            return node.value
        raise UnsafeExpressionError(f"Constante no numérica no permitida: {node.value!r}")

    def visit_Name(self, node: ast.Name):
        if node.id not in self.namespace:
            raise ExpressionEvaluationError(f"Variable no definida en el namespace disponible: '{node.id}'")
        return self.namespace[node.id]

    def visit_BinOp(self, node: ast.BinOp):
        op = _SAFE_BINARY_OPERATORS.get(type(node.op))
        if op is None:
            raise UnsafeExpressionError(f"Operador binario no permitido: {type(node.op).__name__}")
        return op(self.visit(node.left), self.visit(node.right))

    def visit_UnaryOp(self, node: ast.UnaryOp):
        op = _SAFE_UNARY_OPERATORS.get(type(node.op))
        if op is None:
            raise UnsafeExpressionError(f"Operador unario no permitido: {type(node.op).__name__}")
        return op(self.visit(node.operand))

    def visit_Compare(self, node: ast.Compare):
        left = self.visit(node.left)
        result = True
        for op_node, comparator in zip(node.ops, node.comparators):
            op = _SAFE_COMPARE_OPERATORS.get(type(op_node))
            if op is None:
                raise UnsafeExpressionError(f"Comparador no permitido: {type(op_node).__name__}")
            right = self.visit(comparator)
            result = result and op(left, right)
            left = right
        return result

    def visit_Call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name):
            raise UnsafeExpressionError("Solo se permiten llamadas a funciones por nombre simple (nunca obj.attr(...) ni obj[...]).")
        if node.keywords:
            raise UnsafeExpressionError("No se permiten argumentos por palabra clave en llamadas a función.")
        func = _registered_functions.get(node.func.id)
        if func is None:
            raise UnsafeExpressionError(f"Función no permitida/no registrada: '{node.func.id}'")
        return func(*(self.visit(a) for a in node.args))


def evaluate_expression(expression: str, namespace: dict[str, float]) -> float:
    """Parsea y evalúa `expression` de forma segura contra `namespace`. Nunca usa eval()/exec()."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ExpressionEvaluationError(f"Expresión con sintaxis inválida: {exc}") from exc
    return _SafeEvaluator(namespace).visit(tree)


class _StructureChecker(ast.NodeVisitor):
    """Como _SafeEvaluator pero sin evaluar — solo recolecta errores de forma
    (nodos no permitidos, nombres/funciones fuera de lo autorizado)."""

    def __init__(self, allowed_names: set[str]):
        self.allowed_names = allowed_names
        self.errors: list[str] = []

    def visit(self, node: ast.AST) -> None:
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is None:
            self.errors.append(f"Construcción no permitida: {type(node).__name__}")
            return
        method(node)

    def visit_Expression(self, node: ast.Expression) -> None:
        self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> None:
        if not isinstance(node.value, (int, float, bool)):
            self.errors.append(f"Constante no numérica no permitida: {node.value!r}")

    def visit_Name(self, node: ast.Name) -> None:
        if node.id not in self.allowed_names:
            self.errors.append(f"Nombre no autorizado (no está entre los inputs declarados): '{node.id}'")

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if type(node.op) not in _SAFE_BINARY_OPERATORS:
            self.errors.append(f"Operador binario no permitido: {type(node.op).__name__}")
        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        if type(node.op) not in _SAFE_UNARY_OPERATORS:
            self.errors.append(f"Operador unario no permitido: {type(node.op).__name__}")
        self.visit(node.operand)

    def visit_Compare(self, node: ast.Compare) -> None:
        for op_node in node.ops:
            if type(op_node) not in _SAFE_COMPARE_OPERATORS:
                self.errors.append(f"Comparador no permitido: {type(op_node).__name__}")
        self.visit(node.left)
        for c in node.comparators:
            self.visit(c)

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            self.errors.append("Solo se permiten llamadas a funciones por nombre simple.")
            return
        if node.keywords:
            self.errors.append("No se permiten argumentos por palabra clave.")
        if node.func.id not in _registered_functions:
            self.errors.append(f"Función no permitida/no registrada: '{node.func.id}'")
        for a in node.args:
            self.visit(a)


def validate_expression_structure(expression: str, *, allowed_names: set[str]) -> list[str]:
    """
    Valida `expression` SIN evaluarla — usado por la pipeline de
    `CandidateRelation` cuando todavía no hay valores numéricos concretos
    (sección 11). Lista vacía == válida.
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        return [f"Expresión con sintaxis inválida: {exc}"]
    checker = _StructureChecker(allowed_names)
    checker.visit(tree)
    return checker.errors


class DesignRelation(BaseModel):
    """Sección 10. Una relación ya validada — construida SIEMPRE a través de
    `validate_candidate_relation()`, nunca directamente a partir de una
    propuesta del LLM."""

    id: str = Field(default_factory=new_id)
    name: str
    inputs: list[str] = Field(description="Nombres de variables de las que depende — deben existir en el DesignSpace.")
    output: str = Field(description="Nombre de la variable/derived_quantity que esta relación calcula.")
    expression: str
    provenance: Provenance

    def evaluate(self, values: dict[str, float]) -> float:
        missing = [name for name in self.inputs if name not in values]
        if missing:
            raise ExpressionEvaluationError(f"Faltan valores para inputs declarados de '{self.name}': {missing}")
        namespace = {name: values[name] for name in self.inputs}
        return evaluate_expression(self.expression, namespace)


class CandidateRelation(BaseModel):
    """Sección 11. Propuesta cruda — sin autoridad hasta pasar `validate_candidate_relation()`."""

    name: str
    inputs: list[str]
    output: str
    expression: str
    provenance: Provenance
    source_text: Optional[str] = None


def validate_candidate_relation(
    candidate: CandidateRelation, *, known_variable_names: set[str]
) -> tuple[Optional[DesignRelation], list[str]]:
    """CandidateRelation -> Validation -> DesignRelation (sección 11). Nunca ejecuta la expresión aquí."""
    errors: list[str] = []

    allowed_names = set(candidate.inputs)
    errors.extend(validate_expression_structure(candidate.expression, allowed_names=allowed_names))

    missing_inputs = sorted(set(candidate.inputs) - known_variable_names)
    if missing_inputs:
        errors.append(f"Inputs no encontrados entre las variables conocidas del DesignSpace: {missing_inputs}")

    if candidate.output in candidate.inputs:
        errors.append(f"El output '{candidate.output}' no puede ser también uno de sus propios inputs (dependencia circular trivial).")

    if not candidate.inputs:
        errors.append("Una relación requiere al menos un input.")

    if errors:
        return None, errors

    relation = DesignRelation(
        name=candidate.name,
        inputs=list(candidate.inputs),
        output=candidate.output,
        expression=candidate.expression,
        provenance=candidate.provenance,
    )
    return relation, []
