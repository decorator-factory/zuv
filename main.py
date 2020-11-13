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


parser = Lark.open(
    "grammar.lark",
    rel_to=__file__,
    parser="earley",  # TODO: resolve reduce/reduce collisions in LALR
    debug=True,
    maybe_placeholders=True,
)



print(
    parser
    .parse(source)
    .pretty()
)