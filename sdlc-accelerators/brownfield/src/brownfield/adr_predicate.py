"""ADR predicate DSL interpreter — deterministic, NO eval().

A small recursive-descent parser + evaluator for ADR rule predicates like:
  target_tech == 'aurora-mysql' AND data_size_gb > 10000
  cross_cloud_egress AND target_gateway != 'apigee'
Supported: identifiers, string literals ('...'), numbers, booleans (true/false),
operators == != > < >= <=, AND OR NOT, parentheses. Identifier ceiling: 25 (CI-enforced).

This is the engine. The rule CONTENT (predicates, actions) is human-authored by the EA office.
"""

from __future__ import annotations

import re
from typing import Any

MAX_IDENTIFIERS = 25

TOKEN_RE = re.compile(
    r"""
    \s*(?:
      (?P<op>==|!=|>=|<=|>|<)
    | (?P<lparen>\()
    | (?P<rparen>\))
    | (?P<str>'[^']*')
    | (?P<num>\d+(?:\.\d+)?)
    | (?P<word>[A-Za-z_][A-Za-z0-9_]*)
    )
""",
    re.VERBOSE,
)

KEYWORDS = {"and", "or", "not", "true", "false"}


class PredicateError(ValueError):
    pass


def tokenize(expr: str) -> list[Any]:
    """Tokenize a predicate expression into (kind, value) tuples."""
    tokens, pos = [], 0
    while pos < len(expr):
        if expr[pos].isspace():
            pos += 1
            continue
        m = TOKEN_RE.match(expr, pos)
        if not m or m.end() == pos:
            raise PredicateError(f"cannot tokenize at: {expr[pos:][:20]!r}")
        pos = m.end()
        kind = m.lastgroup
        val = m.group().strip()
        tokens.append((kind, val))
    return tokens


def identifiers(expr: str) -> set[Any]:
    """Return the set of non-keyword identifiers used in a predicate."""
    return {v for k, v in tokenize(expr) if k == "word" and v.lower() not in KEYWORDS}


def check_identifier_ceiling(expr: str) -> None:
    """CI guard: raise if a predicate exceeds the 25-identifier ceiling."""
    ids = identifiers(expr)
    if len(ids) > MAX_IDENTIFIERS:
        raise PredicateError(
            f"predicate exceeds {MAX_IDENTIFIERS} identifiers: {sorted(ids)}"
        )


class _Parser:
    """Recursive descent: expr := or_expr ; or := and (OR and)* ; and := not (AND not)* ;
    not := NOT not | comparison ; comparison := atom (op atom)? ; atom := '(' expr ')' | literal | ident."""

    def __init__(self, tokens: Any, ctx: Any) -> None:
        self.toks = tokens
        self.i = 0
        self.ctx = ctx

    def peek(self) -> Any:
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def next(self) -> Any:
        t = self.toks[self.i]
        self.i += 1
        return t

    def parse(self) -> Any:
        v = self.or_expr()
        if self.i != len(self.toks):
            raise PredicateError(f"unexpected trailing tokens: {self.toks[self.i :]}")
        return v

    def or_expr(self) -> Any:
        v = self.and_expr()
        while self.peek() == ("word", "or") or (
            self.peek()[0] == "word" and self.peek()[1].lower() == "or"
        ):
            self.next()
            v = bool(v) or bool(self.and_expr())
        return v

    def and_expr(self) -> Any:
        v = self.not_expr()
        while self.peek()[0] == "word" and self.peek()[1].lower() == "and":
            self.next()
            rhs = self.not_expr()
            v = bool(v) and bool(rhs)
        return v

    def not_expr(self) -> Any:
        if self.peek()[0] == "word" and self.peek()[1].lower() == "not":
            self.next()
            return not bool(self.not_expr())
        return self.comparison()

    def comparison(self) -> Any:
        left = self.atom()
        if self.peek()[0] == "op":
            op = self.next()[1]
            right = self.atom()
            return self._apply(op, left, right)
        return left

    def atom(self) -> Any:
        kind, val = self.peek()
        if kind == "lparen":
            self.next()
            v = self.or_expr()
            if self.peek()[0] != "rparen":
                raise PredicateError("missing )")
            self.next()
            return v
        if kind == "str":
            self.next()
            return val[1:-1]
        if kind == "num":
            self.next()
            return float(val) if "." in val else int(val)
        if kind == "word":
            self.next()
            low = val.lower()
            if low == "true":
                return True
            if low == "false":
                return False
            return self.ctx.get(val)  # identifier -> context value (None if absent)
        raise PredicateError(f"unexpected token: {(kind, val)}")

    @staticmethod
    def _apply(op: Any, left: Any, right: Any) -> Any:
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        # numeric comparisons; coerce when possible
        try:
            lf, rf = float(left), float(right)
        except (TypeError, ValueError):
            raise PredicateError(
                f"non-numeric comparison: {left!r} {op} {right!r}"
            ) from None
        return {">": lf > rf, "<": lf < rf, ">=": lf >= rf, "<=": lf <= rf}[op]


def evaluate(expr: str, context: dict[str, Any]) -> bool:
    """Evaluate a predicate against a context dict. Deterministic, no eval()."""
    check_identifier_ceiling(expr)
    tokens = tokenize(expr)
    return bool(_Parser(tokens, context).parse())
