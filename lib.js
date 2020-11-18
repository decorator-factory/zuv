// The JS function necessary for running compiled `zuv`


_Math = Math;
_String = String;
_Number = Number;
_Map = Map;
_Array = Array;
_console = console;
delete console;

Integer = n => {
    if (n === null || n === undefined)
        panic(`${n} is not a valid integer`);
    if (typeof n === "object" && n.__T === "Integer")
        return n;
    if (typeof n === "object" && n.__T === "Float")
        return Integer(BigInt(_Math.floor(n.__x)));
    if (typeof n === "number")
        return Integer(BigInt(n));
    if (typeof n === "bigint")
        return {
            __T: "Integer",
            __n: n,
            __raw__: () => n,
            __repr__: () => `${n}`,
            add: m => Integer(n + m.__n),
            sub: m => Integer(n - m.__n),
            mul: m => Integer(n * m.__n),
            div: m => Integer(n / m.__n),
            mod: m => Integer(m.__n >= 0n ? n % m.__n : n % m.__n + m.__n),
            gt: m => n > m.__n ? True : False,
            lt: m => n < m.__n ? True : False,
            eq: m => n === m.__n ? True : False,
            ge: m => n >= m.__n ? True : False,
            le: m => n <= m.__n ? True : False,
            __eq__: m => {
                if (m === null || m.__T !== "Integer")
                    return NotImplemented;
                return n === m.__n ? True : False;
            },
        };
    panic(`${n} is not a valid integer`);
};

Integer.is__QMARK = n => {
    if (n === null || n !== undefined || typeof n !== "object")
        return False;
    return n.__T === "Integer" ? True : False;
};

Integer.__repr__ = () => "Integer";


Float = x => {
    if (x === null || x === undefined)
        panic(`${x} is not a valid float`);
    if (typeof x === "object" && x.__T === "Float")
        return x;
    if (typeof x === "object" && x.__T === "Integer")
        return Float(Number(x.__n));;
    if (typeof x === "bigint")
        return Float(Number(n));
    if (typeof x === "number")
        return {
            __T: "Float",
            __x: x,
            __raw__: () => x,
            __repr__: () => `${x}`,
            add: y => Float(x + y.__x),
            sub: y => Float(x - y.__x),
            mul: y => Float(x * y.__x),
            div: y => Float(x / y.__x),
            gt: y => x > y.__x ? True : False,
            lt: y => x < y.__x ? True : False,
            eq: y => x === y.__x ? True : False,
            ge: y => x >= y.__x ? True : False,
            le: y => x <= y.__x ? True : False,
            __eq__: y => {
                if (y === null || y.__T !== "Float")
                    return NotImplemented;
                return x === y.__n ? True : False;
            },
        };
    panic(`${x} is not a valid float`);
};

Float.is__QMARK = x => {
    if (x === null || x !== undefined || typeof x !== "object")
        return False;
    return x.__T === "Float" ? True : False;
};

Float.__repr__ = () => "Float";


panic = (...s) => {
    if (s.length === 0) {
        panic()
    } else if (s.length === 1) {
        s = s[0];
        if (s === null || s === undefined)
            panic(`Panic when panicking: null message.`);
        if (typeof s === "string")
            throw new Error(s);
        if (typeof s === "object" && "__repr__" in s)
            panic(String(s).__s);
        panic("Panic when panicking: invalid message: "
        + JSON.stringify(s));
    } else {
        panic(concat(...s));
    }
};


True = {
    __T: "Bool",
    if: f => f(),
    else: () => {},
    __QMARK: (t, f) => t(),
    __repr__: () => "True",
    __eq__: other => other === True ? True : NotImplemented,
};
False = {
    __T: "Bool",
    if: () => {},
    else: f => f(),
    __QMARK: (t, f) => f(),
    __repr__: () => "False",
    __eq__: other => other === False ? True : NotImplemented,
};
Bool = {
    is__QMARK: x => (
        typeof x === "object"
        && x !== null
        && "if" in x
        && "else" in x
        ? True : False
    ),
    __repr__: () => "Bool",
};


Table = () => {
    const map = new _Map();

    return {
        __T: "Table",
        __map: map,
        length: () => Integer(map.size()),
        has: k => map.has(k.__raw__()) ? True : False,
        get: k => {
            const k_raw = k.__raw__();
            if (!map.has(k_raw))
                panic(`Key not found: ${repr(k).__raw__()}`);
            return map.get(k_raw)[1];
        },
        set: (k, v) => {
            map.set(k.__raw__(), [k, v]);
        },
        forEach: f => {
            map.forEach(([k, v]) => f(k, v));
        },
        mapValues: f => {
            const result = Table();
            map.forEach(([k, v]) => result.set(k, f(v)));
            return result;
        },
        __repr__: () => {
            let result = "Table{";
            map.forEach(([k, v]) => {
                result += repr(k).__raw__() + " " + repr(v).__raw__() + ", ";
            });
            if (result !== "{")
                result = result.slice(0, -2);
            result += "}";
            return result;
        },
        __eq__: other => {
            if (other === null || other.__T !== "Table")
                return NotImplemented;
            if (map.size !== other.__map.size)
                return False;
            for (const [k_raw, [k, v]] of map.entries()){
                if (!other.__map.has(k_raw) || !eq(other.__map.get(k_raw)[1], v) )
                    return False;
            }
            return True;
        },
    };
};


Array = xs => {
    if (xs.__T === "Array")
        return Array([...xs.__T]);
    return {
        __T: "Array",
        __xs: xs,
        at: i => {
            i = Integer(i);
            if (xs.length < i.__n)
                panic(`Index ${i.__n} out of range 0..${xs.length - 1}`);
            return xs[i.__n];
        },
        set: (i, v) => {
            i = Integer(i);
            if (xs.length < i.__n)
                panic(`Index ${i.__n} out of range 0..${xs.length - 1}`);
            xs[i] = v;
            return null;
        },
        push: x => {
            xs.push(x);
            return null;
        },
        pop: () => xs.pop(),
        forEach: fn => {
            xs.forEach(fn);
            return null;
        },
        map: fn => Array(xs.map(fn)),
        __repr__: () =>
            "[" + xs.map(o => repr(o).__raw__()).join(", ") + "]",
        [Symbol.iterator]: () => xs[Symbol.iterator](),
    };
}


repr = x => {
    if (x === null || x === undefined)
        return String(`${x}`);
    if (typeof x === "object" && x.__repr__)
        return String(x.__repr__());
    return String(x);
}

String = x => {
    if (x === null || x === undefined)
        panic(`${x} is not a valid string`);
    if (typeof x === "object" && x.__T === "String")
        return x;
    if (typeof x === "object" && x.__str__)
        return String(x.__str__());
    if (typeof x === "object" && x.__repr__)
        return String(x.__repr__());
    if (typeof x === "object"){
        let result = "{";
        for (const [k, v] of Object.entries(x))
            result += k + " " + repr(v).__raw__() + ", ";
        if (result !== "{")
            result = result.slice(0, -2);
        result += "}";
        return String(result);
    }
    if (typeof x === "function")
        return String("<FN>");
    if (typeof x === "string")
        return {
            __T: "String",
            __s: x,
            __str__: () => x,
            __repr__: () => JSON.stringify(x),
            __raw__: () => x,
            __eq__: s => {
                if (s === null || s.__T !== "String")
                    return NotImplemented;
                return s.__s === x ? True : False;
            },
            join: ys => {
                if (ys.__T !== "Array")
                    panic(`${repr(ys).__s} is not an Array`);
                return String(ys.__xs.map(o => String(o).__s).join(x));
            },
            rjoin: ys => {
                if (ys.__T !== "Array")
                    panic(`${repr(ys).__s} is not an Array`);
                return String(ys.__xs.map(o => repr(o).__s).join(x));
            },
        };

    return String(`${x}`);
};


console = {
    log: thing => {
        _console.log(String(thing).__raw__());
        return null;
    },
    debug: thing => {
        _console.debug(repr(thing).__raw__());
        return null;
    },
    warn: thing => {
        _console.warn(String(thing).__raw__());
        return null;
    },
    error: thing => {
        _console.error(String(thing).__raw__());
        return null;
    },
    __repr__: () => "console",
};


NotImplemented = {__T: "NotImplemented"};


eq = (a, b) => {
    if (a === null && b === null)
        return True;
    if ((a === null) !== (b === null))
        return False;
    if (a.__T !== b.__T)
        return False;

    const forA = "__eq__" in a ? a.__eq__(b) : NotImplemented;
    if (forA === False)
        return False;
    if (forA === True)
        return True;
    if (forA !== NotImplemented)
        throw new Error(`__eq__ returned ${forA.__t}`);

    const forB = "__eq__" in b ? b.__eq__(a) : NotImplemented;
    if (forB === False || forB === NotImplemented)
        return False;
    if (forB === True)
        return True;
    throw new Error(`__eq__ returned ${forB.__t}`);
};

concat = (...xs) => String("").join(Array(xs));
