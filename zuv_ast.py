from dataclasses import dataclass
from typing import Iterator, List, Literal, Optional, Tuple, Union
from sum_type import SumType


# the _as_source_iter method yields (indent_level?, string) parts
AsSource = Iterator[Tuple[Optional[int], str]]

class AstElement:
    def to_js(self) -> str:
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


@dataclass
class BlockExpression(Expression):
    statements: List[Statement]
    implicit_return: bool = True

    def to_js(self):
        result = "{ "
        if self.implicit_return:
            for stmt in self.statements[:-1]:
                result += stmt.to_js() + "; "
            for stmt in self.statements[-1:]:
                result += "const __rv__ = (" + stmt.to_js() + "); return __rv__; "
        else:
            for stmt in self.statements:
                result += stmt.to_js() + "; "
        result += "}"
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

    def to_js(self):
        return self.expression.to_js() + "; "

    def _as_source_iter(self) -> AsSource:
        yield from self.expression._as_source_iter()


@dataclass
class Name(AstElement):
    value: str

    def to_js(self):
        return self.value.replace("?", "__QMARK")

    def _as_source_iter(self) -> AsSource:
        yield (None, self.value)


@dataclass
class IntLiteral(AstElement):
    value: int

    def _as_source_iter(self) -> AsSource:
        yield (None, str(self.value))


@dataclass
class StrLiteral(AstElement):
    value: str

    def _as_source_iter(self) -> AsSource:
        yield (None, '"' + "".join("\\" + c if c in {"\\" , '"'} else c for c in self.value) + '"')


@dataclass
class ArrayLiteral(AstElement):
    elements: List[AstElement]

    def to_js(self):
        return "[" + ", ".join(e.to_js() for e in self.elements) + "]"

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

def table_entry_to_js(e: TableEntry) -> str:
    if isinstance(e, TableEntry.KeyValue):
        [k, v] = e
        return k + ": " + v.to_js()
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

    def to_js(self):
        return "({" + ", ".join(table_entry_to_js(e) for e in self.entries) + "})"

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

    def to_js(self):
        return self.name.replace("?", "__QMARK")

    def _as_source_iter(self) -> AsSource:
        yield (None, self.name)


@dataclass
class LvalueArray(AssignmentTarget):
    targets: List[AssignmentTarget]

    def to_js(self):
        return "[" + ", ".join(t.to_js() for t in self.targets) + "]"

    def _as_source_iter(self) -> AsSource:
        yield (None, "$[")
        for t in self.targets:
            yield from t._as_source_iter()
            yield (None, ", ")
        yield (None, "]")


@dataclass
class LvalueTable(AssignmentTarget):
    names: List[str]

    def to_js(self):
        return "{" + ", ".join(self.names) + "}"

    def _as_source_iter(self) -> AsSource:
        yield (None, "${" + ", ".join(self.names) + "}")


@dataclass
class Assignment(Statement):
    target: AssignmentTarget
    expression: Expression

    def to_js(self):
        return self.target.to_js() + " = " + self.expression.to_js() + " "

    def _as_source_iter(self) -> AsSource:
        yield from self.target._as_source_iter()
        yield (None, " = ")
        yield from self.expression._as_source_iter()


@dataclass
class MemberAccess(Expression):
    expression: Expression
    member_name: str

    def to_js(self):
        return self.expression.to_js() + "." + self.member_name.replace("?", "__QMARK")

    def _as_source_iter(self) -> AsSource:
        yield from self.expression._as_source_iter()
        yield (None, "->")
        yield (None, self.member_name)


@dataclass
class MethodCall(Expression):
    expression: Expression
    method_name: str
    arguments: List[Expression]

    def to_js(self):
        return (
            self.expression.to_js()
            + "."
            + self.method_name.replace("?", "__QMARK")
            + "("
            + ", ".join(arg.to_js() for arg in self.arguments)
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

    def to_js(self):
        if self.kind == "@":
            return (
                "__result__ = __root__."
                + self.method_name.replace("?", "__QMARK")
                + "("
                + ", ".join(arg.to_js() for arg in self.arguments)
                + ");"
            )
        elif self.kind == "|>":
            return (
                "__result__ = __result__."
                + self.method_name.replace("?", "__QMARK")
                + "("
                + ", ".join(arg.to_js() for arg in self.arguments)
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

    def to_js(self):
        return (
            "((__subject__) => { "
            + " let __root__ = __subject__; "
            + " let __result__ = __subject__; "
            + "; ".join(call.to_js() for call in self.calls)
            + "; return __result__ })("
            + self.subject.to_js()
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

    def to_js(self):
        return (
            "("
            + ", ".join(p.replace("?", "__QMARK") for p in self.parameters)
            + ") => "
            + self.body.to_js()
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

    def to_js(self):
        return (
            "("
            + self.function.to_js()
            + ")("
            + ", ".join(arg.to_js() for arg in self.arguments)
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