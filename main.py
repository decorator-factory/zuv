import json
import zuv_ast

source = R'''
is_arg = (Array @is? t)...
            @if (fn: (print: "yes"))
            @else (fn: (print: "no")).

Point = fn x y: { x, y }.

MousePointerController = fn document:
    $[mx, my, dx, dy] = [0, 0, 0, 0]

    document @add_event_listener "mousemove" (fn e:
        $[dx, dy] = [e->x @sub mx., e->y @sub my.]
        $[mx, my] = [e->x, e->y]
    ).

    is_pressed = False

    on_press = Event!
    document @add_event_listener "mousedown" (fn e:
        is_pressed = True
        on_press @emit { x e->x, y e->y }.).

    on_release = Event!
    document @add_event_listener "mousedown" (fn e:
        is_pressed = True
        on_press @emit { x e->x, y e->y }.).

    { x(), y(), dx(), dy(), is_pressed(), on_press, on_release }.
'''





from lark import Lark, Transformer, v_args


@v_args(inline=True)
class ZuvTransformer(Transformer):
    @staticmethod
    def start(*stmts):
        return zuv_ast.BlockExpression(list(stmts))

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
    def fn_parameters(*tokens):
        return [t.value for t in tokens]

    @staticmethod
    def member_access(expr, identifier):
        return zuv_ast.MemberAccess(expr, identifier.value)

    @staticmethod
    def bare_method_call(expr, method_name, *args):
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
    def single_chained_call(kind, method_name, *exprs):
        return zuv_ast.SingleChainedCall(kind, method_name.value, list(exprs))

    @staticmethod
    def chained_method_call_expr(subject, *calls):
        return zuv_ast.ChainedMethodCall(subject, list(calls))


parser = Lark.open(
    "grammar.lark",
    rel_to=__file__,
    parser="lalr",  # TODO: resolve reduce/reduce collisions in LALR
    debug=True,
    maybe_placeholders=True,
)


source2 = (
    ZuvTransformer()
    .transform(parser.parse(source))
    .as_source()
)
print(source2)

source3 = (
    ZuvTransformer()
    .transform(parser.parse(source2))
    .as_source()
)
print(source3)

assert source2 == source3