from dataclasses import dataclass
from typing import Iterator, List, Literal, Optional, Set, Tuple, Union, Generic, TypeVar
from sum_type import SumType


T = TypeVar("T")


class Box(Generic[T]):
    def __init__(self, value: T):
        self.boxed = value


@dataclass
class JsContext:
    parent: Optional["JsContext"]
    nonlocal_names: Set[str]
    local_names: Set[str]

    def can_local_name_be_used(self, name: str) -> bool:
        return name not in self.nonlocal_names

    def can_outer_name_be_used(self, name: str) -> bool:
        return name not in self.local_names


# the _as_source_iter method yields (indent_level?, string) parts
AsSource = Iterator[Tuple[Optional[int], str]]

class AstElement:
    def to_js(self, ctx: Box[JsContext]) -> str:
        return self.as_source()

    def _as_source_iter(self) -> AsSource:
        raise NotImplementedError

    def _indented_source(self) -> Iterator[str]:
        for (indent, part) in self._as_source_iter():
            if indent is not None:
                yield "\n"
                for _ in range(indent):
                    yield "    "
            yield part

    def as_source(self):
        return "".join(self._indented_source())


class Expression(AstElement):
    pass


class Statement(AstElement):
    pass


class AssignmentTarget(AstElement):
    pass


def var_prefix_for(stmt):
    if (isinstance(stmt, Assignment)
        and not isinstance(stmt.target, LvalueNameNonlocal)
    ):
        return "var "
    else:
        return ""


@dataclass
class BlockExpression(Expression):
    statements: List[Statement]
    implicit_return: bool = True

    def to_js(self, ctx: Box[JsContext]):
        ctx.boxed = JsContext(ctx.boxed, set(), set())
        result = "{ "
        if self.implicit_return:
            for stmt in self.statements[:-1]:
                result += var_prefix_for(stmt)
                result += stmt.to_js(ctx) + "; "
            for stmt in self.statements[-1:]:
                if isinstance(stmt, Assignment):
                    result += var_prefix_for(stmt) + stmt.to_js(ctx) + ";"
                else:
                    result += "return (" + var_prefix_for(stmt) + stmt.to_js(ctx) + "); "
        else:
            for stmt in self.statements:
                result += var_prefix_for(stmt)
                result += stmt.to_js(ctx) + "; "
        result += "}"
        ctx.boxed = ctx.boxed.parent  # type: ignore
        return result

    def _as_source_iter(self) -> AsSource:
        if len(self.statements) == 0:
            yield (None, " ")
        elif len(self.statements) == 1:
            yield from self.statements[0]._as_source_iter()
        else:
            for stmt in self.statements:
                yield (0, "")
                for (indent, part) in stmt._as_source_iter():
                    if indent is None:
                        yield (None, part)
                    else:
                        yield (indent + 1, part)


@dataclass
class ExpressionStatement(Statement):
    expression: Expression

    def to_js(self, ctx):
        return self.expression.to_js(ctx) + "; "

    def _as_source_iter(self) -> AsSource:
        yield from self.expression._as_source_iter()


@dataclass
class Name(AstElement):
    value: str

    def to_js(self, ctx):
        return self.value.replace("?", "__QMARK")

    def _as_source_iter(self) -> AsSource:
        yield (None, self.value)


@dataclass
class IntLiteral(AstElement):
    value: int

    def to_js(self, ctx):
        return f"Integer({self.value})"

    def _as_source_iter(self) -> AsSource:
        yield (None, str(self.value))


@dataclass
class StrLiteral(AstElement):
    value: str

    def to_js(self, ctx):
        return f"String({self._encode()})"

    def _encode(self):
        return '"' + "".join("\\" + c if c in {"\\" , '"'} else c for c in self.value) + '"'

    def _as_source_iter(self) -> AsSource:
        yield (None, self._encode())


@dataclass
class ArrayLiteral(AstElement):
    elements: List[AstElement]

    def to_js(self, ctx):
        return "Array([" + ", ".join(e.to_js(ctx) for e in self.elements) + "])"

    def _as_source_iter(self) -> AsSource:
        if self.elements == []:
            yield (None, "[]")
        else:
            yield (None, "[")
            for e in self.elements:
                for (indent, part) in e._as_source_iter():
                    if indent is None:
                        yield (None, part)
                    else:
                        yield (indent + 1, part)
                yield (None, ", ")
            yield (None, "]")


class TableEntry(SumType):
    KeyValue(str, object)  # type: ignore
    KeyShorthand(str)      # type: ignore
    GetterShorthand(str)   # type: ignore

def render_table_entry(e: TableEntry) -> AsSource:
    if isinstance(e, TableEntry.KeyValue):
        [k, v] = e
        yield (None, k + " ")
        it = iter(v._as_source_iter())
        for (_indent, part) in it:
            yield (None, part)
            break
        yield from it
    elif isinstance(e, TableEntry.KeyShorthand):
        [k] = e
        yield (None, k)
    elif isinstance(e, TableEntry.GetterShorthand):
        [k] = e
        yield (None, k + "()")
    else:
        assert False

def table_entry_to_js(e: TableEntry, ctx: Box[JsContext]) -> str:
    if isinstance(e, TableEntry.KeyValue):
        [k, v] = e
        return k + ": " + v.to_js(ctx)
    elif isinstance(e, TableEntry.KeyShorthand):
        [k] = e
        return k
    elif isinstance(e, TableEntry.GetterShorthand):
        [k] = e
        return f"{k}: () => {k}"
    else:
        assert False


@dataclass
class TableLiteral(AstElement):
    entries: List[TableEntry]

    def to_js(self, ctx):
        return "({" + ", ".join(table_entry_to_js(e, ctx) for e in self.entries) + "})"

    def _as_source_iter(self) -> AsSource:
        if self.entries == []:
            yield (None, "{}")
        else:
            yield (None, "{")
            for e in self.entries:
                for (indent, part) in render_table_entry(e):
                    if indent is None:
                        yield (None, part)
                    else:
                        yield (indent + 1, part)
                yield (None, ", ")
            yield (None, "}")


@dataclass
class LvalueName(AssignmentTarget):
    name: str

    def to_js(self, ctx: Box[JsContext]):
        if not ctx.boxed.can_local_name_be_used(self.name):
            raise TypeError(f"Cannot use name {self.name} as local here.")
        ctx.boxed.local_names.add(self.name)
        return self.name.replace("?", "__QMARK")

    def _as_source_iter(self) -> AsSource:
        yield (None, self.name)


@dataclass
class LvalueNameNonlocal(AssignmentTarget):
    name: str

    def to_js(self, ctx: Box[JsContext]):
        if not ctx.boxed.can_outer_name_be_used(self.name):
            raise TypeError(f"Cannot use name {self.name} as outer here.")
        ctx.boxed.nonlocal_names.add(self.name)
        return self.name.replace("?", "__QMARK")

    def _as_source_iter(self) -> AsSource:
        yield (None, "outer ")
        yield (None, self.name)



@dataclass
class LvalueArray(AssignmentTarget):
    targets: List[AssignmentTarget]

    def to_js(self, ctx):
        for t in self.targets:
            if isinstance(t, LvalueNameNonlocal):
                raise TypeError("Cannot use nonlocal name in array destructuring.")
        return "[" + ", ".join(t.to_js(ctx) for t in self.targets) + "]"

    def _as_source_iter(self) -> AsSource:
        yield (None, "$[")
        for t in self.targets:
            yield from t._as_source_iter()
            yield (None, ", ")
        yield (None, "]")


@dataclass
class LvalueTable(AssignmentTarget):
    names: List[str]

    def to_js(self, ctx):
        return "{" + ", ".join(self.names) + "}"

    def _as_source_iter(self) -> AsSource:
        yield (None, "${" + ", ".join(self.names) + "}")


@dataclass
class Assignment(Statement):
    target: AssignmentTarget
    expression: Expression

    def to_js(self, ctx):
        return self.target.to_js(ctx) + " = " + self.expression.to_js(ctx) + " "

    def _as_source_iter(self) -> AsSource:
        yield from self.target._as_source_iter()
        yield (None, " = ")
        yield from self.expression._as_source_iter()


@dataclass
class MemberAccess(Expression):
    expression: Expression
    member_name: str

    def to_js(self, ctx):
        return self.expression.to_js(ctx) + "." + self.member_name.replace("?", "__QMARK")

    def _as_source_iter(self) -> AsSource:
        yield from self.expression._as_source_iter()
        yield (None, "->")
        yield (None, self.member_name)


@dataclass
class MethodCall(Expression):
    expression: Expression
    method_name: str
    arguments: List[Expression]

    def to_js(self, ctx):
        return (
            self.expression.to_js(ctx)
            + "."
            + self.method_name.replace("?", "__QMARK")
            + "("
            + ", ".join(arg.to_js(ctx) for arg in self.arguments)
            + ")"
        )

    def _as_source_iter(self) -> AsSource:
        yield (None, "(")
        yield from self.expression._as_source_iter()
        yield (None, " @")
        yield (None, self.method_name)
        for arg in self.arguments:
            yield (None, " ")
            yield from arg._as_source_iter()
        yield (None, ")")


@dataclass
class SingleChainedCall(AstElement):
    kind: Union[Literal["@"], Literal["|>"]]
    method_name: str
    arguments: List[Expression]

    def to_js(self, ctx):
        if self.kind == "@":
            return (
                "__x = __s."
                + self.method_name.replace("?", "__QMARK")
                + "("
                + ", ".join(arg.to_js(ctx) for arg in self.arguments)
                + ");"
            )
        elif self.kind == "|>":
            return (
                "__x = __x."
                + self.method_name.replace("?", "__QMARK")
                + "("
                + ", ".join(arg.to_js(ctx) for arg in self.arguments)
                + ");"
            )
        else:
            assert False

    def _as_source_iter(self) -> AsSource:
        yield (None, self.kind)
        yield (None, self.method_name)
        for arg in self.arguments:
            yield (None, " ")
            yield from arg._as_source_iter()


@dataclass
class ChainedMethodCall(Expression):
    subject: Expression
    calls: List[SingleChainedCall]

    def to_js(self, ctx):
        return (
            "((__s) => { "
            + "var __x = __s; "
            + "; ".join(call.to_js(ctx) for call in self.calls)
            + "; return __x })("
            + self.subject.to_js(ctx)
            + ")"
        )

    def _as_source_iter(self) -> AsSource:
        yield (None, "(")

        yield from self.subject._as_source_iter()
        yield (None, "...")

        for call in self.calls:
            yield (0, "")
            for (indent, part) in call._as_source_iter():
                if indent is None:
                    yield (None, part)
                else:
                    yield (indent + 1, part)
        yield (None, " .)")


@dataclass
class FunctionDefinition(Expression):
    parameters: List[str]
    body: Expression

    def to_js(self, ctx):
        return (
            "("
            + ", ".join(p.replace("?", "__QMARK") for p in self.parameters)
            + ") => "
            + self.body.to_js(ctx)
        )

    def _as_source_iter(self) -> AsSource:
        yield (None, "(")
        yield (None, "fn")
        for param in self.parameters:
            yield (None, " " + param)
        yield (None, ": ")
        yield from self.body._as_source_iter()
        yield (None, ")")


@dataclass
class FunctionCall(Expression):
    function: Expression
    arguments: List[Expression]

    def to_js(self, ctx):
        return (
            "("
            + self.function.to_js(ctx)
            + ")("
            + ", ".join(arg.to_js(ctx) for arg in self.arguments)
            + ")"
        )

    def _as_source_iter(self) -> AsSource:
        if self.arguments == []:
            yield from self.function._as_source_iter()
            yield (None, "!")
        else:
            yield (None, "(")
            yield from self.function._as_source_iter()
            yield (None, ":")
            for arg in self.arguments:
                yield (None, " ")
                yield from arg._as_source_iter()
            yield (None, ")")