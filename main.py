import json
from typing import Any
import zuv_ast

from lark import Lark, Transformer, v_args


@v_args(inline=True)
class ZuvTransformer(Transformer):
    @staticmethod
    def start(*stmts):
        return zuv_ast.BlockExpression(list(stmts), implicit_return=False)

    # Utilities:
    @staticmethod
    def sep_by(*args):
        return list(args)

    @staticmethod
    def sep_by_strict(*args):
        return list(args)

    @staticmethod
    def sep_by_plus(*args):
        return list(args)

    # Assignment:
    @staticmethod
    def lvalue_name_nonlocal(token):
        return zuv_ast.LvalueNameNonlocal(token.value)

    @staticmethod
    def lvalue_name(token):
        return zuv_ast.LvalueName(token.value)

    @staticmethod
    def lvalue_array(targets):
        return zuv_ast.LvalueArray(targets)

    @staticmethod
    def lvalue_table(targets):
        return zuv_ast.LvalueTable(targets)

    @staticmethod
    def assignment_stmt(target, expr):
        return zuv_ast.Assignment(target, expr)

    # Literals:
    @staticmethod
    def name_literal(token):
        return zuv_ast.Name(token.value)

    @staticmethod
    def int_literal(token):
        return zuv_ast.IntLiteral(int(token))

    @staticmethod
    def str_literal(token):
        return zuv_ast.StrLiteral(json.loads(token))

    @staticmethod
    def array_literal(exprs):
        return zuv_ast.ArrayLiteral(exprs)

    # Table literals:
    @staticmethod
    def table_literal(entries):
        return zuv_ast.TableLiteral(entries)

    @staticmethod
    def table_literal_entry(key, value):
        if value is None:
            return zuv_ast.TableEntry.KeyShorthand(key.value)
        elif value == "()":
            return zuv_ast.TableEntry.GetterShorthand(key.value)
        else:
            return zuv_ast.TableEntry.KeyValue(key.value, value)

    @staticmethod
    def fn_parameters(*params):
        return list(params)

    @staticmethod
    def member_access(expr, identifier):
        return zuv_ast.MemberAccess(expr, identifier.value)

    @staticmethod
    def shorthand_args(*params):
        return list(params)

    @staticmethod
    def param_name(name):
        return zuv_ast.NamedParameter(str(name))

    @staticmethod
    def param_object(names):
        return zuv_ast.ObjectParameter(names)

    @staticmethod
    def param_array(names):
        return zuv_ast.ArrayParameter(names)

    @staticmethod
    def bare_method_call(expr, method_name, shorthand_args, *args):
        if shorthand_args is not None:
            return zuv_ast.MethodCall(
                expr,
                method_name.value,
                [zuv_ast.FunctionDefinition(shorthand_args, zuv_ast.BlockExpression(list(args)))]
            )
        else:
            return zuv_ast.MethodCall(expr, method_name.value, list(args))

    @staticmethod
    def bare_function_call(function, *args):
        return zuv_ast.FunctionCall(function, list(args))

    @staticmethod
    def singleton_function_call_expr(function):
        return zuv_ast.FunctionCall(function, [])

    @staticmethod
    def bare_function_definition(parameters, *statements):
        return zuv_ast.FunctionDefinition(parameters, zuv_ast.BlockExpression(list(statements)))

    # Chained method calls:
    @staticmethod
    def chain(token):
        if token == "@":
            return "@"
        elif token == "|>":
            return "|>"
        else:
            assert False, token.value

    @staticmethod
    def single_chained_call(kind, method_name, shorthand_args, *args):
        if shorthand_args is not None:
            return zuv_ast.SingleChainedCall(
                kind,
                method_name.value,
                [zuv_ast.FunctionDefinition(shorthand_args, zuv_ast.BlockExpression(list(args)))]
            )
        else:
            return zuv_ast.SingleChainedCall(kind, method_name.value, list(args))

    @staticmethod
    def chained_method_call_expr(subject, *calls):
        return zuv_ast.ChainedMethodCall(subject, list(calls))


parser = Lark.open(
    "grammar.lark",
    rel_to=__file__,
    parser="lalr",
    maybe_placeholders=True,
    transformer=ZuvTransformer(),
)


if __name__ == "__main__":
    import sys

    with open(sys.argv[1], "r") as file:
        ast: Any = parser.parse(file.read())
        assert isinstance(ast, zuv_ast.AstElement)
        print(ast.to_js(zuv_ast.Box(zuv_ast.JsContext(
            None, set(), set()
        ))))