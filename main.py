import json
import oolang_ast as oa

source = R'''
is_arg = (Array @is? t)...
            @if (fn: (print: "yes"))
            @else (fn: (print: "no")).

Point = fn x y: { x, y }.

MousePointerController = fn document:
    [mx, my, dx, dy] = [0, 0, 0, 0]

    document @add_event_listener "mousemove" (fn e:
        [dx, dy] = [e->x @sub mx., e->y @sub my.]
        [mx, my] = [e->x, e->y]
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
class OolangTransformer(Transformer):
    @staticmethod
    def start(*stmts):
        return oa.BlockExpression(list(stmts))

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
        return oa.LvalueName(token.value)

    @staticmethod
    def lvalue_array(targets):
        return oa.LvalueArray(targets)

    @staticmethod
    def lvalue_table(targets):
        return oa.LvalueTable(targets)

    @staticmethod
    def assignment_stmt(target, expr):
        return oa.Assignment(target, expr)

    # Literals:
    @staticmethod
    def name_literal(token):
        return oa.Name(token.value)

    @staticmethod
    def int_literal(token):
        return oa.IntLiteral(int(token))

    @staticmethod
    def str_literal(token):
        return oa.StrLiteral(json.loads(token))

    @staticmethod
    def array_literal(exprs):
        return oa.ArrayLiteral(exprs)

    # Table literals:
    @staticmethod
    def table_literal(entries):
        return oa.TableLiteral(entries)

    @staticmethod
    def table_literal_entry(key, value):
        if value is None:
            return oa.TableEntry.KeyShorthand(key.value)
        elif value == "()":
            return oa.TableEntry.GetterShorthand(key.value)
        else:
            return oa.TableEntry.KeyValue(key.value, value)

    @staticmethod
    def fn_parameters(*tokens):
        return [t.value for t in tokens]

    @staticmethod
    def member_access(expr, identifier):
        return oa.MemberAccess(expr, identifier.value)

    @staticmethod
    def bare_method_call(expr, method_name, *args):
        return oa.MethodCall(expr, method_name.value, list(args))

    @staticmethod
    def bare_function_call(function, *args):
        return oa.FunctionCall(function, list(args))

    @staticmethod
    def singleton_function_call_expr(function):
        return oa.FunctionCall(function, [])

    @staticmethod
    def bare_function_definition(parameters, *statements):
        return oa.FunctionDefinition(parameters, oa.BlockExpression(list(statements)))

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
        return oa.SingleChainedCall(kind, method_name.value, list(exprs))

    @staticmethod
    def chained_method_call_expr(subject, *calls):
        return oa.ChainedMethodCall(subject, list(calls))


parser = Lark.open(
    "grammar.lark",
    rel_to=__file__,
    parser="earley",  # TODO: resolve reduce/reduce collisions in LALR
    debug=True,
    maybe_placeholders=True,
)


source2 = (
    OolangTransformer()
    .transform(parser.parse(source))
    .as_source()
)
print(source2)

source3 = (
    OolangTransformer()
    .transform(parser.parse(source2))
    .as_source()
)
print(source3)

assert source2 == source3