# 51 templates

import re
from exprs import ExprGen, INT_LIM, uexpr

REGISTRY = []

def template(family, tid, weight=1.0):
    def deco(fn):
        REGISTRY.append((family, f"{family}.{tid}", fn, weight))
        return fn
    return deco


SCALAR_NAMES = ["a", "b", "c", "x", "y", "z", "m", "p", "q", "u", "v", "w", "k",
                "val", "num", "lhs", "rhs", "base", "limit", "step", "key", "d", "s"]
LOCAL_NAMES = ["t", "r", "acc", "tmp", "res", "e", "g", "h", "sum", "diff", "prod",
               "mid", "cur", "prev", "best", "cnt", "out", "total", "y2", "j2"]
LEN_NAMES = ["n", "n", "len", "count", "size"]
ARR_NAMES = ["a", "arr", "xs", "v", "data", "nums", "vals", "buf"]
STR_NAMES = ["s", "str", "buf", "text", "chars"]


def P(name, type_, lo, hi, kind="scalar", const=False, len_=None):
    d = {"name": name, "type": type_, "kind": kind, "const": const, "lo": lo, "hi": hi}
    if len_:
        d["len"] = len_
    return d


def pick_names(rng, pool, k, avoid=()):
    pool = [x for x in pool if x not in avoid]
    return rng.sample(pool, k)


def fname(rng, *opts):
    base = rng.choice(opts)
    return base if rng.random() < 0.7 else f"{base}_{rng.choice(['v2', 'fn', 'impl', 'calc', 'i', 'x'])}"


def rint_range(rng):
    return rng.choice([(-100, 100), (-1000, 1000), (0, 1000), (-50, 50), (0, 100), (-10000, 10000)])


def itype(rng):
    return rng.choice(["int", "int", "int", "long"])


def for_loop(rng, i, lo, cond_hi, body, step="1", decl=True, cmp="<"):
    inc = f"{i}++" if step == "1" else f"{i} += {step}"
    if rng.random() < 0.15 and step == "1":
        inc = f"++{i}"
    head = f"for ({'int ' if decl else ''}{i} = {lo}; {i} {cmp} {cond_hi}; {inc})"
    if len(body) == 1 and rng.random() < 0.35:
        return [head] + ["    " + body[0]]
    return [head + " {"] + ["    " + b for b in body] + ["}"]


def block(head, body):
    return [head + " {"] + ["    " + b for b in body] + ["}"]


@template("arith", "expr")
def arith_expr(rng):
    k = rng.randint(1, 3)
    names = pick_names(rng, SCALAR_NAMES, k)
    lo, hi = rint_range(rng)
    ps = [P(n, "int", lo, hi) for n in names]
    g = ExprGen(rng, [(n, max(abs(lo), abs(hi))) for n in names])
    e = g.gen(rng.randint(2, 3))
    ret = itype(rng)
    return fname(rng, "compute", "eval_expr", "calc", "mix", "combine", "formula", "fn"), ret, ps, [f"return {e.s};"], []


@template("arith", "locals", 1.5)
def arith_locals(rng):
    k = rng.randint(1, 3)
    names = pick_names(rng, SCALAR_NAMES, k)
    lo, hi = rint_range(rng)
    ps = [P(n, "int", lo, hi) for n in names]
    vars_ = [(n, max(abs(lo), abs(hi))) for n in names]
    lt = rng.choice(["int", "long"])
    body = []
    for ln in pick_names(rng, LOCAL_NAMES, rng.randint(2, 4)):
        g = ExprGen(rng, vars_)
        e = g.gen_using(rng.randint(1, 2), [vars_[-1][0]])
        body.append(f"{lt} {ln} = {e.s};")
        vars_.append((ln, e.b))
        if rng.random() < 0.35:
            g2 = ExprGen(rng, vars_)
            e2 = g2.gen(1)
            op = rng.choice(["+=", "-="])
            if e.b + e2.b <= INT_LIM:
                body.append(f"{ln} {op} {e2.s};")
                vars_[-1] = (ln, e.b + e2.b)
    e = ExprGen(rng, vars_).gen_using(rng.randint(1, 2), [vars_[-1][0]])
    body.append(f"return {e.s};")
    return fname(rng, "compute", "transform", "step", "blend", "score", "evaluate"), lt, ps, body, []


@template("arith", "unsigned_bits")
def arith_unsigned(rng):
    k = rng.randint(1, 3)
    names = pick_names(rng, SCALAR_NAMES, k)
    ut = rng.choice(["unsigned int", "unsigned int", "unsigned long"])
    ps = [P(n, ut, 0, rng.choice([255, 65535, 2**32 - 1])) for n in names]
    body = []
    vs = list(names)
    for ln in pick_names(rng, LOCAL_NAMES, rng.randint(0, 2)):
        e = uexpr(rng, vs, 2)
        for _ in range(10):
            if vs[-1] in e:
                break
            e = uexpr(rng, vs, 2)
        body.append(f"{ut} {ln} = {e};")
        vs.append(ln)
    e = uexpr(rng, vs, 3)
    for _ in range(10):
        if vs[-1] in e:
            break
        e = uexpr(rng, vs, 3)
    body.append(f"return {e};")
    return fname(rng, "hash_bits", "mix_bits", "scramble", "bitmix", "fold"), ut, ps, body, []


@template("arith", "update")
def arith_update(rng):
    names = pick_names(rng, SCALAR_NAMES, 2)
    lo, hi = rint_range(rng)
    ps = [P(n, "int", lo, hi) for n in names]
    B = max(abs(lo), abs(hi))
    acc = rng.choice(LOCAL_NAMES)
    body = [f"long {acc} = {names[0]};"]
    b = B
    for _ in range(rng.randint(2, 5)):
        op = rng.choice(["+=", "-=", "*=", "/=", "%=", "+=", "-="])
        if op in ("*=",):
            c = rng.randint(2, 7)
            if b * c > INT_LIM:
                continue
            body.append(f"{acc} *= {c};"); b *= c
        elif op in ("/=", "%="):
            c = rng.randint(2, 9)
            body.append(f"{acc} {op} {c};")
            if op == "%=":
                b = min(b, c - 1)
        else:
            v = rng.choice(names + [str(rng.randint(1, 50))])
            body.append(f"{acc} {op} {v};"); b += B
    body.append(f"return {acc};")
    return fname(rng, "accumulate", "update", "apply_ops", "adjust"), "long", ps, body, []


@template("cond", "ifchain", 1.5)
def cond_ifchain(rng):
    k = rng.randint(1, 3)
    names = pick_names(rng, SCALAR_NAMES, k)
    lo, hi = rint_range(rng)
    ps = [P(n, "int", lo, hi) for n in names]
    vars_ = [(n, max(abs(lo), abs(hi))) for n in names]
    g = ExprGen(rng, vars_)
    r = rng.choice(LOCAL_NAMES)
    t = itype(rng)
    nb = rng.randint(1, 3)
    body = []
    if rng.random() < 0.5:
        body.append(f"{t} {r};")
        for i in range(nb):
            kw = "if" if i == 0 else "} else if"
            body += [f"{kw} ({g.cond()}) {{", f"    {r} = {g.gen(2).s};"]
        body += ["} else {", f"    {r} = {g.gen(2).s};", "}", f"return {r};"]
    else:
        for i in range(nb):
            body += [f"if ({g.cond()})", f"    return {g.gen(2).s};"]
        body.append(f"return {g.gen(2).s};")
    return fname(rng, "classify", "select_val", "pick", "branch", "decide", "piecewise"), t, ps, body, []


@template("cond", "ternary")
def cond_ternary(rng):
    k = rng.randint(1, 3)
    names = pick_names(rng, SCALAR_NAMES, k)
    lo, hi = rint_range(rng)
    ps = [P(n, "int", lo, hi) for n in names]
    g = ExprGen(rng, [(n, max(abs(lo), abs(hi))) for n in names])
    e = f"{g.cond()} ? {g.gen(2).wrap(1)} : {g.gen(2).wrap(1)}"
    if rng.random() < 0.4:
        e = f"{g.cond()} ? {g.gen(1).wrap(1)} : ({e})"
    return fname(rng, "choose", "selector", "sel", "pick_value"), itype(rng), ps, [f"return {e};"], []


@template("cond", "minmax", 1.5)
def cond_minmax(rng):
    x, y, z = pick_names(rng, SCALAR_NAMES, 3)
    lo, hi = rint_range(rng)
    kind = rng.choice(["max3", "min3", "clamp", "median3", "absdiff", "sign", "max2", "between"])
    tern = rng.random() < 0.5
    if kind in ("max3", "min3"):
        c = ">" if kind == "max3" else "<"
        if tern:
            body = [f"int {LOCAL_NAMES[1]} = {x} {c} {y} ? {x} : {y};",
                    f"return {LOCAL_NAMES[1]} {c} {z} ? {LOCAL_NAMES[1]} : {z};"]
        else:
            body = [f"int r = {x};", f"if ({y} {c} r)", f"    r = {y};", f"if ({z} {c} r)", f"    r = {z};", "return r;"]
        ps = [P(n, "int", lo, hi) for n in (x, y, z)]
        name = fname(rng, kind, "max_of3" if kind == "max3" else "min_of3")
    elif kind == "clamp":
        ps = [P(x, "int", lo, hi), P(y, "int", lo, hi), P(z, "int", lo, hi)]
        body = [f"if ({x} < {y})", f"    return {y};", f"if ({x} > {z})", f"    return {z};", f"return {x};"] \
            if not tern else [f"return {x} < {y} ? {y} : ({x} > {z} ? {z} : {x});"]
        name = fname(rng, "clamp", "clip", "bound")
    elif kind == "median3":
        ps = [P(n, "int", lo, hi) for n in (x, y, z)]
        body = [f"if (({x} >= {y} && {x} <= {z}) || ({x} <= {y} && {x} >= {z}))", f"    return {x};",
                f"if (({y} >= {x} && {y} <= {z}) || ({y} <= {x} && {y} >= {z}))", f"    return {y};",
                f"return {z};"]
        name = fname(rng, "median3", "middle")
    elif kind == "absdiff":
        ps = [P(x, "int", lo, hi), P(y, "int", lo, hi)]
        body = [f"return {x} > {y} ? {x} - {y} : {y} - {x};"] if tern else \
            [f"int diff = {x} - {y};", "if (diff < 0)", "    diff = -diff;", "return diff;"]
        name = fname(rng, "abs_diff", "distance", "gap")
    elif kind == "sign":
        ps = [P(x, "int", lo, hi)]
        body = [f"return ({x} > 0) - ({x} < 0);"] if tern else \
            [f"if ({x} > 0)", "    return 1;", f"if ({x} < 0)", "    return -1;", "return 0;"]
        name = fname(rng, "sign", "sgn", "signum")
    elif kind == "max2":
        ps = [P(x, "int", lo, hi), P(y, "int", lo, hi)]
        body = [f"return {x} >= {y} ? {x} : {y};"] if tern else [f"if ({x} >= {y})", f"    return {x};", f"return {y};"]
        name = fname(rng, "max2", "larger", "maximum")
    else:
        ps = [P(x, "int", lo, hi), P(y, "int", lo, hi), P(z, "int", lo, hi)]
        body = [f"return {x} >= {y} && {x} <= {z};"] if tern else \
            [f"if ({x} < {y} || {x} > {z})", "    return 0;", "return 1;"]
        name = fname(rng, "in_range", "between", "within")
    return name, "int", ps, body, []


@template("cond", "switch")
def cond_switch(rng):
    x, y = pick_names(rng, SCALAR_NAMES, 2)
    lo, hi = rint_range(rng)
    B = max(abs(lo), abs(hi))
    m = rng.randint(3, 8)
    sel = rng.choice([f"{x} % {m}", f"({x} % {m} + {m}) % {m}", f"{x} & {m - 1 if m in (4, 8) else 7}"])
    if "&" in sel and lo < 0:
        sel = f"({x} % {m} + {m}) % {m}"
    g = ExprGen(rng, [(x, B), (y, B)])
    body = [f"switch ({sel}) {{"]
    used = rng.sample(range(0, m), rng.randint(2, min(m, 5)))
    for c in sorted(used):
        body.append(f"case {c}:")
        if rng.random() < 0.3 and c != sorted(used)[-1]:
            continue  # fallthrough
        body.append(f"    return {g.gen(2).s};")
    body += ["default:", f"    return {g.gen(1).s};", "}"]
    return fname(rng, "dispatch", "by_case", "op_select", "table"), "int", [P(x, "int", lo, hi), P(y, "int", lo, hi)], body, []


@template("cond", "nested")
def cond_nested(rng):
    names = pick_names(rng, SCALAR_NAMES, rng.randint(2, 3))
    lo, hi = rint_range(rng)
    ps = [P(n, "int", lo, hi) for n in names]
    vars_ = [(n, max(abs(lo), abs(hi))) for n in names]
    g = ExprGen(rng, vars_)
    r = rng.choice(LOCAL_NAMES)
    body = [f"long {r} = {g.gen(1).s};",
            f"if ({g.cond()}) {{",
            f"    if ({g.cond()})",
            f"        {r} += {g.gen(1).s};",
            "    else",
            f"        {r} -= {g.gen(1).s};",
            "} else {",
            f"    {r} = {g.gen(2).s};",
            "}",
            f"return {r};"]
    return fname(rng, "nested_pick", "evaluate", "rule", "adjust"), "long", ps, body, []


@template("loop", "accum", 2.0)
def loop_accum(rng):
    n = rng.choice(["n", "n", "count", "steps", "limit"])
    i = rng.choice(["i", "i", "k", "j"])
    acc = rng.choice(["acc", "sum", "total", "s", "r"])
    a = rng.choice([x for x in SCALAR_NAMES if x not in (n, i, acc)])
    N = rng.choice([20, 50, 100])
    ps = [P(n, "int", 0, N)]
    vars_ = [(i, N)]
    if rng.random() < 0.6:
        ps.append(P(a, "int", -50, 50))
        vars_.append((a, 50))
    term = ExprGen(rng, vars_, ops="+-*%").gen_using(2, [i])
    modded = term.b * (N + 1) > INT_LIM // 2
    upd = f"{acc} = ({acc} + {term.s}) % 1000003;" if modded else f"{acc} += {term.wrap(4)};"
    inner = [upd]
    if rng.random() < 0.35:
        inner = [f"if ({i} % {rng.randint(2, 4)} == {rng.randint(0, 1)})", "    " + upd]
    start = rng.choice(["0", "0", "1"])
    if rng.random() < 0.7:
        loop = for_loop(rng, i, start, n, inner, cmp=rng.choice(["<", "<="]))
        body = [f"long {acc} = {rng.choice(['0', '0', '1'])};"] + loop
    else:
        body = [f"long {acc} = 0;", f"int {i} = {start};"] + block(f"while ({i} < {n})", inner + [f"{i}++;"])
    body.append(f"return {acc};")
    return fname(rng, "series_sum", "accumulate", "sum_terms", "running_total", "series"), "long", ps, body, []


@template("loop", "digits", 1.5)
def loop_digits(rng):
    x = rng.choice(["x", "num", "n", "value", "v"])
    base = rng.choice([10, 10, 10, 2, 8, 16, rng.randint(3, 9)])
    neg = rng.random() < 0.4
    ps = [P(x, "int", -1000000 if neg else 0, 1000000)]
    kind = rng.choice(["sum", "count", "reverse", "max", "product", "alt"])
    pre = [f"if ({x} < 0)", f"    {x} = -{x};"] if neg else []
    r = rng.choice(["r", "res", "acc", "out"])
    if kind == "sum":
        upd, init, name = [f"{r} += {x} % {base};"], "0", ("digit_sum", "sum_digits")
    elif kind == "count":
        upd, init, name = [f"{r}++;"], "0", ("count_digits", "num_digits")
    elif kind == "reverse":
        upd, init, name = [f"{r} = {r} * {base} + {x} % {base};"], "0", ("reverse_digits", "reverse_num")
    elif kind == "max":
        upd, init, name = [f"if ({x} % {base} > {r})", f"    {r} = {x} % {base};"], "0", ("max_digit", "largest_digit")
    elif kind == "product":
        upd, init, name = [f"{r} *= {x} % {base};"], "1", ("digit_product", "product_digits")
        ps = [P(x, "int", -99999 if neg else 0, 99999)]
    else:
        upd, init, name = [f"{r} = -{r} + {x} % {base};"], "0", ("alt_digit_sum", "digit_alternate")
    rt = "long" if kind in ("reverse", "product") else "int"
    if kind == "count" and rng.random() < 0.5:
        body = pre + [f"{rt} {r} = 0;"] + block("do", upd + [f"{x} /= {base};"])
        body[-1] = f"}} while ({x} > 0);"
    else:
        body = pre + [f"{rt} {r} = {init};"] + block(f"while ({x} > 0)", upd + [f"{x} /= {base};"])
    if kind == "reverse" and base > 10:
        ps = [P(x, "int", ps[0]["lo"] // 100, 1000000 // 100)]
    body.append(f"return {r};")
    return fname(rng, *name), rt, ps, body, []


@template("loop", "gcd")
def loop_gcd(rng):
    a, b = rng.sample(["a", "b", "x", "y", "m", "u", "v"], 2)
    kind = rng.choice(["mod", "sub", "lcm", "coprime"])
    ps = [P(a, "int", 0, 10000), P(b, "int", 0, 10000)]
    t = rng.choice(["t", "tmp", "r"])
    core = block(f"while ({b} != 0)", [f"int {t} = {a} % {b};", f"{a} = {b};", f"{b} = {t};"])
    if kind == "mod":
        body, name = core + [f"return {a};"], ("gcd", "gcd_iter", "greatest_common")
    elif kind == "sub":
        ps = [P(a, "int", 1, 2000), P(b, "int", 1, 2000)]
        body = block(f"while ({a} != {b})", [f"if ({a} > {b})", f"    {a} -= {b};", "else", f"    {b} -= {a};"]) + [f"return {a};"]
        name = ("gcd_sub", "euclid_sub")
    elif kind == "lcm":
        ps = [P(a, "int", 1, 10000), P(b, "int", 1, 10000)]
        body = [f"long {t}0 = {a}, {t}1 = {b};"] + core + [f"return {t}0 / {a} * {t}1;"]
        name = ("lcm", "least_common_multiple")
    else:
        body = core + [f"return {a} == 1;"]
        name = ("coprime", "is_coprime", "rel_prime")
    return fname(rng, *name), "long" if kind == "lcm" else "int", ps, body, []


@template("loop", "bits", 1.5)
def loop_bits(rng):
    x = rng.choice(["x", "v", "bits", "mask", "w"])
    ut = rng.choice(["unsigned int", "unsigned int", "unsigned long"])
    ps = [P(x, ut, 0, 2**32 - 1 if ut == "unsigned int" else 2**64 - 1)]
    kind = rng.choice(["pop1", "pop2", "parity", "ctz", "highbit", "pow2", "rev8"])
    c = rng.choice(["c", "count", "n", "r"])
    if kind == "pop1":
        body = [f"int {c} = 0;"] + block(f"while ({x})", [f"{c} += {x} & 1;", f"{x} >>= 1;"]) + [f"return {c};"]
        name = ("popcount", "count_ones", "bit_count")
    elif kind == "pop2":
        body = [f"int {c} = 0;"] + block(f"while ({x} != 0)", [f"{x} &= {x} - 1;", f"{c}++;"]) + [f"return {c};"]
        name = ("popcount", "count_set_bits")
    elif kind == "parity":
        body = [f"int {c} = 0;"] + block(f"while ({x})", [f"{c} ^= {x} & 1;", f"{x} >>= 1;"]) + [f"return {c};"]
        name = ("parity", "odd_parity")
    elif kind == "ctz":
        body = [f"if ({x} == 0)", "    return -1;", f"int {c} = 0;"] + \
            block(f"while (({x} & 1) == 0)", [f"{x} >>= 1;", f"{c}++;"]) + [f"return {c};"]
        name = ("trailing_zeros", "ctz", "lowest_bit")
    elif kind == "highbit":
        body = [f"int {c} = -1;"] + block(f"while ({x})", [f"{x} >>= 1;", f"{c}++;"]) + [f"return {c};"]
        name = ("highest_bit", "log2_floor", "msb_index")
    elif kind == "pow2":
        body = [f"return {x} != 0 && ({x} & ({x} - 1)) == 0;"]
        name = ("is_pow2", "is_power_of_two")
    else:
        w = rng.choice([8, 16])
        body = [f"{ut} {c} = 0;"] + for_loop(rng, "i", "0", str(w), [f"{c} = ({c} << 1) | (({x} >> i) & 1);"]) + [f"return {c};"]
        name = (f"reverse{w}", f"bitrev{w}")
    rt = ut if kind == "rev8" else "int"
    return fname(rng, *name), rt, ps, body, []


@template("loop", "numeric", 1.5)
def loop_numeric(rng):
    kind = rng.choice(["isqrt", "prime", "divsum", "collatz", "powmod", "fib", "tri", "ilog"])
    x = rng.choice(["n", "x", "num", "value"])
    if kind == "isqrt":
        ps = [P(x, "int", 0, 100000)]
        body = ["long r = 0;"] + block(f"while ((r + 1) * (r + 1) <= {x})", ["r++;"]) + ["return r;"]
        name, rt = ("isqrt", "int_sqrt", "floor_sqrt"), "long"
    elif kind == "prime":
        ps = [P(x, "int", -10, 5000)]
        body = [f"if ({x} < 2)", "    return 0;"] + \
            for_loop(rng, "d", "2", f"{x}", [f"if ({x} % d == 0)", "    return 0;"], cmp="* d <=") + ["return 1;"]
        name, rt = ("is_prime", "prime", "check_prime"), "int"
    elif kind == "divsum":
        ps = [P(x, "int", 1, 3000)]
        body = ["int s = 0;"] + for_loop(rng, "d", "1", x, [f"if ({x} % d == 0)", "    s += d;"], cmp="<") + ["return s;"]
        name, rt = ("sum_divisors", "aliquot", "divisor_sum"), "int"
    elif kind == "collatz":
        cap = rng.choice([100, 200, 500])
        ps = [P(x, "long", 1, 100000)]
        body = ["int steps = 0;"] + block(f"while ({x} != 1 && steps < {cap})",
                                         [f"if ({x} % 2 == 0)", f"    {x} /= 2;", "else", f"    {x} = 3 * {x} + 1;", "steps++;"]) + ["return steps;"]
        name, rt = ("collatz_steps", "hailstone_len"), "int"
    elif kind == "powmod":
        ps = [P("b", "long", -1000, 1000), P("e", "int", 0, 60), P("m", "long", 1, 10007)]
        if rng.random() < 0.5:
            body = ["long r = 1 % m;", "b %= m;", "if (b < 0)", "    b += m;"] + \
                block("while (e > 0)", ["if (e & 1)", "    r = r * b % m;", "b = b * b % m;", "e >>= 1;"]) + ["return r;"]
        else:
            body = ["long r = 1 % m;"] + for_loop(rng, "i", "0", "e", ["r = r * (b % m) % m;"]) + ["return r;"]
        name, rt, x = ("powmod", "mod_pow", "power_mod"), "long", None
    elif kind == "fib":
        M = rng.choice([1000000007, 1000003, 10007])
        ps = [P(x, "int", 0, 90)]
        body = ["long a = 0, b = 1;"] + for_loop(rng, "i", "0", x, [f"long t = (a + b) % {M};", "a = b;", "b = t;"]) + ["return a;"]
        name, rt = ("fib_mod", "fibonacci"), "long"
    elif kind == "tri":
        ps = [P(x, "int", 0, 1000)]
        body = ["long t = 0;", "int k = 0;"] + block(f"while (t + k + 1 <= {x})", ["k++;", "t += k;"]) + ["return k;"]
        name, rt = ("tri_root", "max_triangular"), "long"
    else:
        bb = rng.randint(2, 10)
        ps = [P(x, "long", 1, 10**9)]
        body = ["int k = 0;"] + block(f"while ({x} >= {bb})", [f"{x} /= {bb};", "k++;"]) + ["return k;"]
        name, rt = (f"ilog{bb}", "int_log"), "int"
    return fname(rng, *name), rt, ps, body, []


@template("loop", "nested")
def loop_nested(rng):
    n, m = rng.sample(["n", "m", "rows", "cols", "w", "h"], 2)
    N = rng.choice([8, 12, 20])
    ps = [P(n, "int", 0, N), P(m, "int", 0, N)]
    i, j = "i", "j"
    term = ExprGen(rng, [(i, N), (j, N)], ops="+-*%").gen_using(2, [j])
    acc = rng.choice(["acc", "sum", "total"])
    inner_hi = rng.choice([m, i, f"{i} + 1"])
    inner = for_loop(rng, j, "0", inner_hi, [f"{acc} += {term.wrap(4)};"])
    if rng.random() < 0.3:
        inner = for_loop(rng, j, "0", inner_hi, [f"if (({i} + {j}) % {rng.randint(2, 3)} == 0)", f"    {acc} += {term.wrap(4)};"])
    body = [f"long {acc} = 0;"] + for_loop(rng, i, "0", n, inner) + [f"return {acc};"]
    return fname(rng, "grid_sum", "double_sum", "pair_total", "table_sum"), "long", ps, body, []


def _helper(rng, hname, nparams, arg_bound):
    names = pick_names(rng, SCALAR_NAMES, nparams)
    g = ExprGen(rng, [(n, arg_bound) for n in names], lim=INT_LIM // 4)
    if rng.random() < 0.4:
        e = g.gen(2)
        c = g.cond()
        e2 = g.gen(1)
        text = [f"static int {hname}({', '.join('int ' + n for n in names)})", "{",
                f"    if ({c})", f"        return {e.s};", f"    return {e2.s};", "}"]
        b = max(e.b, e2.b)
    else:
        e = g.gen(rng.randint(1, 2))
        text = [f"static int {hname}({', '.join('int ' + n for n in names)})", "{", f"    return {e.s};", "}"]
        b = e.b
    return text, b


@template("calls", "helpers", 2.0)
def calls_helpers(rng):
    k = rng.randint(1, 3)
    names = pick_names(rng, SCALAR_NAMES, k)
    lo, hi = rng.choice([(-100, 100), (-50, 50), (0, 100), (-1000, 1000)])
    B = max(abs(lo), abs(hi))
    ps = [P(n, "int", lo, hi) for n in names]
    helpers = []
    vars_ = [(n, B) for n in names]
    hnames = pick_names(rng, ["sq", "twice", "half", "mix", "adj", "scale", "nudge", "clampish", "f1", "g1", "tweak", "norm"], rng.randint(1, 2))
    body = []
    for h in hnames:
        np_ = rng.randint(1, 2)
        args = [ExprGen(rng, vars_, lim=INT_LIM // 8, ops="+-").gen(1) for _ in range(np_)]
        ab = max(a.b for a in args)
        text, hb = _helper(rng, h, np_, ab)
        helpers.append(text)
        loc = rng.choice([x for x in LOCAL_NAMES if x not in [v[0] for v in vars_]])
        body.append(f"int {loc} = {h}({', '.join(a.s for a in args)});")
        vars_.append((loc, hb))
    locs = vars_[len(names):]
    rest = INT_LIM - sum(b for _, b in locs)
    e = ExprGen(rng, vars_[:len(names)], lim=rest, ops="+-*").gen(1)
    terms = [l for l, _ in locs]
    rng.shuffle(terms)
    expr = terms[0] + "".join(f" {rng.choice('+-')} {t}" for t in terms[1:])
    if rng.random() < 0.7:
        expr += f" {rng.choice('+-')} {e.wrap(5)}"
    body.append(f"return {expr};")
    return fname(rng, "combine", "pipeline", "apply", "evaluate", "process"), "long", ps, body, helpers


@template("calls", "recursive", 1.5)
def calls_recursive(rng):
    kind = rng.choice(["fact", "sumto", "power", "fib", "gcd", "digits", "binom"])
    x = rng.choice(["n", "k", "x"])
    if kind == "fact":
        ps, rt = [P(x, "int", 0, 20)], "long"
        body = [f"if ({x} <= 1)", "    return 1;", f"return {x} * FN({x} - 1);"]
        name = ("factorial", "fact")
    elif kind == "sumto":
        ps, rt = [P(x, "int", 0, 1000)], "long"
        body = [f"if ({x} == 0)", "    return 0;", f"return {x} + FN({x} - 1);"]
        name = ("sum_to", "triangular")
    elif kind == "power":
        ps, rt = [P("b", "long", -9, 9), P("e", "int", 0, 18)], "long"
        if rng.random() < 0.5:
            body = ["if (e == 0)", "    return 1;", "return b * FN(b, e - 1);"]
        else:
            body = ["if (e == 0)", "    return 1;", "long h = FN(b, e / 2);",
                    "if (e % 2 == 0)", "    return h * h;", "return h * h * b;"]
        name = ("power", "ipow", "pow_rec")
    elif kind == "fib":
        ps, rt = [P(x, "int", 0, 22)], "int"
        body = [f"if ({x} < 2)", f"    return {x};", f"return FN({x} - 1) + FN({x} - 2);"]
        name = ("fib", "fibonacci")
    elif kind == "gcd":
        ps, rt = [P("a", "int", 0, 100000), P("b", "int", 0, 100000)], "int"
        body = ["if (b == 0)", "    return a;", "return FN(b, a % b);"]
        name = ("gcd", "gcd_rec")
    elif kind == "digits":
        ps, rt = [P(x, "int", 0, 2000000000)], "int"
        body = [f"if ({x} < 10)", f"    return {x};", f"return {x} % 10 + FN({x} / 10);"]
        name = ("digit_sum", "sum_digits_rec")
    else:
        ps, rt = [P("n", "int", 0, 16), P("k", "int", 0, 16)], "long"
        body = ["if (k < 0 || k > n)", "    return 0;", "if (k == 0 || k == n)", "    return 1;",
                "return FN(n - 1, k - 1) + FN(n - 1, k);"]
        name = ("binom", "choose")
    fn = fname(rng, *name)
    body = [b.replace("FN", fn) for b in body]
    helpers = []
    if rng.random() < 0.3:
        # static recursive core + public wrapper
        core = fn + "_rec"
        sig = ", ".join(f"{p['type']} {p['name']}" for p in ps)
        helpers.append([f"static {rt} {core}({sig})", "{"] + ["    " + b.replace(fn + "(", core + "(") for b in body] + ["}"])
        g = rng.choice(["", "w"])
        body = [f"return {core}({', '.join(p['name'] for p in ps)});"]
        if g:
            body = [f"{rt} r = {core}({', '.join(p['name'] for p in ps)});", "return r;"]
    return fn, rt, ps, body, helpers


@template("calls", "predicate")
def calls_predicate(rng):
    pk = rng.choice(["even", "prime", "square", "digit7", "mult"])
    if pk == "even":
        helper = ["static int is_even(int v)", "{", "    return v % 2 == 0;", "}"]; hn = "is_even"
    elif pk == "prime":
        helper = ["static int is_prime(int v)", "{", "    if (v < 2)", "        return 0;",
                  "    for (int d = 2; d * d <= v; d++)", "        if (v % d == 0)", "            return 0;",
                  "    return 1;", "}"]; hn = "is_prime"
    elif pk == "square":
        helper = ["static int is_square(int v)", "{", "    int r = 0;", "    while (r * r < v)", "        r++;",
                  "    return r * r == v;", "}"]; hn = "is_square"
    elif pk == "digit7":
        helper = ["static int has_seven(int v)", "{", "    if (v < 0)", "        v = -v;", "    while (v > 0) {",
                  "        if (v % 10 == 7)", "            return 1;", "        v /= 10;", "    }", "    return 0;", "}"]; hn = "has_seven"
    else:
        m = rng.randint(3, 9)
        helper = [f"static int divisible(int v)", "{", f"    return v % {m} == 0;", "}"]; hn = "divisible"
    lo, hi = rng.sample(["lo", "hi", "a", "b", "start", "end", "from", "to"], 2)
    ps = [P(lo, "int", -100, 500), P(hi, "int", -100, 500)]
    mode = rng.choice(["count", "sum", "first"])
    if mode == "count":
        body = ["int c = 0;"] + for_loop(rng, "i", lo, hi, [f"if ({hn}(i))", "    c++;"], cmp="<=") + ["return c;"]
        name = ("count_matching", f"count_{hn}")
    elif mode == "sum":
        body = ["long s = 0;"] + for_loop(rng, "i", lo, hi, [f"if ({hn}(i))", "    s += i;"], cmp="<=") + ["return s;"]
        name = ("sum_matching", f"sum_{hn}")
    else:
        body = for_loop(rng, "i", lo, hi, [f"if ({hn}(i))", "    return i;"], cmp="<=") + ["return -1;"]
        name = ("first_matching", f"first_{hn}")
    return fname(rng, *name), "long" if mode == "sum" else "int", ps, body, [helper]


def _arr_setup(rng, const=True, et=None, N=None):
    a = rng.choice(ARR_NAMES)
    n = rng.choice(LEN_NAMES)
    et = et or rng.choice(["int", "int", "int", "long"])
    N = N or rng.choice([8, 16, 24])
    lo, hi = rng.choice([(-1000, 1000), (-100, 100), (0, 100), (0, 1000), (-10, 10)])
    ps = [P(a, et, lo, hi, kind="array", const=const, len_=n), P(n, "int", 0, N, kind="len")]
    return a, n, et, ps, max(abs(lo), abs(hi)), N


def _pred(rng, v):
    k = rng.random()
    if k < 0.35:
        return f"{v} {rng.choice(['>', '<', '>=', '<=', '==', '!='])} {rng.randint(-20, 50)}"
    if k < 0.65:
        return f"{v} % {rng.randint(2, 5)} == 0"
    if k < 0.8:
        return f"{v} % 2 != 0"
    lo = rng.randint(-50, 10)
    return f"{v} >= {lo} && {v} <= {lo + rng.randint(5, 60)}"


@template("array", "reduce", 2.5)
def array_reduce(rng):
    a, n, et, ps, B, N = _arr_setup(rng)
    i = rng.choice(["i", "i", "k", "j"])
    kind = rng.choice(["sum", "sumsq", "min", "max", "count", "avg", "range", "altsum", "sumif"])
    x = f"{a}[{i}]"
    if kind == "sum":
        body = ["long s = 0;"] + for_loop(rng, i, "0", n, [f"s += {x};"]) + ["return s;"]
        name, rt = ("sum", "array_sum", "total"), "long"
    elif kind == "sumsq":
        body = ["long s = 0;"] + for_loop(rng, i, "0", n, [f"s += (long){x} * {x};"]) + ["return s;"]
        name, rt = ("sum_squares", "energy", "norm2"), "long"
    elif kind in ("min", "max"):
        c = "<" if kind == "min" else ">"
        best = rng.choice(["best", "m", "r", "cur"])
        body = [f"if ({n} <= 0)", "    return 0;", f"{et} {best} = {a}[0];"] + \
            for_loop(rng, i, "1", n, [f"if ({x} {c} {best})", f"    {best} = {x};"]) + [f"return {best};"]
        name, rt = ((f"array_{kind}", f"find_{kind}", f"{kind}_element")), et
    elif kind == "count":
        body = ["int c = 0;"] + for_loop(rng, i, "0", n, [f"if ({_pred(rng, x)})", "    c++;"]) + ["return c;"]
        name, rt = ("count_if", "count_matching", "tally"), "int"
    elif kind == "sumif":
        body = ["long s = 0;"] + for_loop(rng, i, "0", n, [f"if ({_pred(rng, x)})", f"    s += {x};"]) + ["return s;"]
        name, rt = ("sum_if", "filtered_sum", "conditional_sum"), "long"
    elif kind == "avg":
        body = ["long s = 0;", f"if ({n} == 0)", "    return 0;"] + for_loop(rng, i, "0", n, [f"s += {x};"]) + [f"return s / {n};"]
        name, rt = ("average", "mean", "avg"), "long"
    elif kind == "range":
        body = [f"if ({n} == 0)", "    return 0;", f"{et} lo = {a}[0], hi = {a}[0];"] + \
            for_loop(rng, i, "1", n, [f"if ({x} < lo)", f"    lo = {x};", f"if ({x} > hi)", f"    hi = {x};"]) + ["return hi - lo;"]
        name, rt = ("spread", "value_range", "range_width"), "long"
    else:
        body = ["long s = 0;"] + for_loop(rng, i, "0", n, [f"if ({i} % 2 == 0)", f"    s += {x};", "else", f"    s -= {x};"]) + ["return s;"]
        name, rt = ("alternating_sum", "alt_sum"), "long"
    if rng.random() < 0.2 and kind in ("sum", "count"):
        # pointer-walking variant
        p = "p"
        if kind == "sum":
            body = ["long s = 0;", f"const {et} *{p} = {a};", f"const {et} *end = {a} + {n};"] + \
                block(f"while ({p} < end)", [f"s += *{p};", f"{p}++;"]) + ["return s;"]
        else:
            body = ["int c = 0;", f"for (const {et} *{p} = {a}; {p} != {a} + {n}; {p}++)",
                    f"    if ({_pred(rng, '*' + p)})", "        c++;", "return c;"]
    return fname(rng, *name), rt, ps, body, []


@template("array", "search", 1.5)
def array_search(rng):
    a, n, et, ps, B, N = _arr_setup(rng)
    ps[0]["lo"], ps[0]["hi"] = rng.choice([(-10, 10), (0, 20), (-5, 5)])
    key = rng.choice(["key", "target", "x", "val"])
    ps.append(P(key, et, ps[0]["lo"], ps[0]["hi"]))
    i = rng.choice(["i", "k"])
    kind = rng.choice(["first", "last", "contains", "occurrences", "firstpred"])
    if kind == "first":
        body = for_loop(rng, i, "0", n, [f"if ({a}[{i}] == {key})", f"    return {i};"]) + ["return -1;"]
        name = ("index_of", "find", "linear_search")
    elif kind == "last":
        body = block(f"for (int {i} = {n} - 1; {i} >= 0; {i}--)", [f"if ({a}[{i}] == {key})", f"    return {i};"]) + ["return -1;"]
        name = ("last_index_of", "rfind")
    elif kind == "contains":
        body = [f"int {i} = 0;"] + block(f"while ({i} < {n} && {a}[{i}] != {key})", [f"{i}++;"]) + [f"return {i} < {n};"]
        name = ("contains", "member", "has_value")
    elif kind == "occurrences":
        body = ["int c = 0;"] + for_loop(rng, i, "0", n, [f"c += {a}[{i}] == {key};"]) + ["return c;"]
        name = ("count_occurrences", "frequency")
    else:
        ps.pop()
        body = for_loop(rng, i, "0", n, [f"if ({_pred(rng, f'{a}[{i}]')})", f"    return {i};"]) + ["return -1;"]
        name = ("find_first", "first_index_where")
    return fname(rng, *name), "int", ps, body, []


@template("array", "inplace", 2.0)
def array_inplace(rng):
    a, n, et, ps, B, N = _arr_setup(rng, const=False)
    i = rng.choice(["i", "k"])
    x = f"{a}[{i}]"
    kind = rng.choice(["map", "clamp", "abs", "zero", "reverse", "rotate", "swappairs", "scale"])
    rt = "void"
    if kind == "map":
        g = ExprGen(rng, [(x, B), (i, N)], ops="+-*%")
        e = g.gen(2)
        ps[0]["lo"], ps[0]["hi"] = (-1000, 1000)
        g = ExprGen(rng, [(x, 1000), (i, N)], ops="+-*%", lim=2**31 - 1)
        e = g.gen_using(2, [x])
        body = for_loop(rng, i, "0", n, [f"{x} = {e.s};"])
        name = ("transform", "map_values", "apply_inplace")
    elif kind == "clamp":
        lo = rng.randint(-50, 0); hi = rng.randint(1, 80)
        body = for_loop(rng, i, "0", n, [f"if ({x} < {lo})", f"    {x} = {lo};", f"else if ({x} > {hi})", f"    {x} = {hi};"])
        name = ("clamp_all", "saturate", "clip_array")
    elif kind == "abs":
        body = ["int changed = 0;"] + for_loop(rng, i, "0", n, [f"if ({x} < 0) {{", f"    {x} = -{x};", "    changed++;", "}"]) + ["return changed;"]
        rt = "int"
        name = ("abs_all", "make_positive")
    elif kind == "zero":
        body = for_loop(rng, i, "0", n, [f"if ({_pred(rng, x)})", f"    {x} = 0;"])
        name = ("zero_matching", "mask_out", "filter_zero")
    elif kind == "reverse":
        if rng.random() < 0.5:
            body = block(f"for (int lo = 0, hi = {n} - 1; lo < hi; lo++, hi--)",
                         [f"{et} t = {a}[lo];", f"{a}[lo] = {a}[hi];", f"{a}[hi] = t;"])
        else:
            body = for_loop(rng, i, "0", f"{n} / 2", [f"{et} t = {x};", f"{x} = {a}[{n} - 1 - {i}];", f"{a}[{n} - 1 - {i}] = t;"])
        name = ("reverse", "reverse_inplace", "flip")
    elif kind == "rotate":
        if rng.random() < 0.5:
            body = [f"if ({n} < 2)", "    return;", f"{et} first = {a}[0];"] + \
                for_loop(rng, i, "0", f"{n} - 1", [f"{x} = {a}[{i} + 1];"]) + [f"{a}[{n} - 1] = first;"]
            name = ("rotate_left", "rotl1")
        else:
            body = [f"if ({n} < 2)", "    return;", f"{et} last = {a}[{n} - 1];"] + \
                block(f"for (int {i} = {n} - 1; {i} > 0; {i}--)", [f"{x} = {a}[{i} - 1];"]) + [f"{a}[0] = last;"]
            name = ("rotate_right", "rotr1")
    elif kind == "swappairs":
        body = for_loop(rng, i, "0", f"{n}", [f"{et} t = {x};", f"{x} = {a}[{i} + 1];", f"{a}[{i} + 1] = t;"], step="2", cmp="+ 1 <")
        name = ("swap_pairs", "pairwise_swap")
    else:
        c = rng.randint(2, 9)
        body = for_loop(rng, i, "0", n, [f"{x} {rng.choice(['*=', '/=', '+=', '-='])} {c};"])
        name = ("scale", "adjust_all", "shift_values")
    return fname(rng, *name), rt, ps, body, []


@template("array", "sort", 1.0)
def array_sort(rng):
    a, n, et, ps, B, N = _arr_setup(rng, const=False, N=16)
    kind = rng.choice(["bubble", "insertion", "selection"])
    c = rng.choice([">", "<"])
    if kind == "bubble":
        body = block(f"for (int i = 0; i + 1 < {n}; i++)", block(f"for (int j = 0; j + 1 < {n} - i; j++)", block(
            f"if ({a}[j] {c} {a}[j + 1])", [f"{et} t = {a}[j];", f"{a}[j] = {a}[j + 1];", f"{a}[j + 1] = t;"])))
    elif kind == "insertion":
        body = block(f"for (int i = 1; i < {n}; i++)", [f"{et} key = {a}[i];", "int j = i - 1;"] +
                     block(f"while (j >= 0 && {a}[j] {c} key)", [f"{a}[j + 1] = {a}[j];", "j--;"]) + [f"{a}[j + 1] = key;"])
    else:
        body = block(f"for (int i = 0; i < {n}; i++)", ["int m = i;"] + block(f"for (int j = i + 1; j < {n}; j++)", [
            f"if ({a}[j] {'<' if c == '>' else '>'} {a}[m])", "    m = j;"]) + [f"{et} t = {a}[i];", f"{a}[i] = {a}[m];", f"{a}[m] = t;"])
    d = "asc" if c == ">" else "desc"
    return fname(rng, f"{kind}_sort", f"sort_{d}", f"{kind}_sort_{d}"), "void", ps, body, []


@template("array", "scan", 1.5)
def array_scan(rng):
    kind = rng.choice(["prefix", "runmax", "kadane", "sorted", "inversions", "longest_run", "diff"])
    const = kind in ("kadane", "sorted", "inversions", "longest_run")
    a, n, et, ps, B, N = _arr_setup(rng, const=const)
    rt = "void"
    if kind == "prefix":
        body = for_loop(rng, "i", "1", n, [f"{a}[i] += {a}[i - 1];"])
        name = ("prefix_sum", "cumulative_sum", "scan_add")
    elif kind == "runmax":
        body = for_loop(rng, "i", "1", n, [f"if ({a}[i] < {a}[i - 1])", f"    {a}[i] = {a}[i - 1];"])
        name = ("running_max", "prefix_max")
    elif kind == "kadane":
        body = [f"if ({n} == 0)", "    return 0;", f"long best = {a}[0], cur = {a}[0];"] + \
            for_loop(rng, "i", "1", n, [f"cur = cur + {a}[i] > {a}[i] ? cur + {a}[i] : {a}[i];", "if (cur > best)", "    best = cur;"]) + ["return best;"]
        rt, name = "long", ("max_subarray", "kadane", "best_run_sum")
    elif kind == "sorted":
        c = rng.choice([">", "<"])
        body = for_loop(rng, "i", "1", n, [f"if ({a}[i - 1] {c} {a}[i])", "    return 0;"]) + ["return 1;"]
        rt, name = "int", ("is_sorted", "nondecreasing" if c == ">" else "nonincreasing")
    elif kind == "inversions":
        body = ["int c = 0;"] + for_loop(rng, "i", "0", n, for_loop(rng, "j", "i + 1", n, [f"if ({a}[i] > {a}[j])", "    c++;"])) + ["return c;"]
        rt, name = "int", ("count_inversions", "inversions")
    elif kind == "longest_run":
        body = [f"if ({n} == 0)", "    return 0;", "int best = 1, cur = 1;"] + \
            for_loop(rng, "i", "1", n, [f"if ({a}[i] {rng.choice(['>', '==', '>='])} {a}[i - 1])", "    cur++;", "else", "    cur = 1;",
                                       "if (cur > best)", "    best = cur;"]) + ["return best;"]
        rt, name = "int", ("longest_run", "max_streak")
    else:
        out = rng.choice(["out", "dst", "res"])
        ps.insert(1, P(out, et, 0, 0, kind="array", const=False, len_=n))
        ps[0]["const"] = True
        body = [f"if ({n} == 0)", "    return;", f"{out}[0] = {a}[0];"] + for_loop(rng, "i", "1", n, [f"{out}[i] = {a}[i] - {a}[i - 1];"])
        name = ("adjacent_diff", "differences", "deltas")
    return fname(rng, *name), rt, ps, body, []


@template("array", "pair", 1.5)
def array_pair(rng):
    a, b = rng.sample(["a", "b", "x", "y", "u", "v", "lhs", "rhs", "src"], 2)
    n = rng.choice(LEN_NAMES)
    et = rng.choice(["int", "int", "long"])
    lo, hi = rng.choice([(-100, 100), (-1000, 1000), (0, 10), (-5, 5)])
    ps = [P(a, et, lo, hi, kind="array", const=True, len_=n), P(b, et, lo, hi, kind="array", const=True, len_=n),
          P(n, "int", 0, rng.choice([8, 16, 24]), kind="len")]
    kind = rng.choice(["dot", "eq", "add", "maxabs", "lexcmp", "dist"])
    rt = "long"
    if kind == "dot":
        body = ["long s = 0;"] + for_loop(rng, "i", "0", n, [f"s += (long){a}[i] * {b}[i];"]) + ["return s;"]
        name = ("dot", "dot_product", "inner")
    elif kind == "eq":
        body = ["int c = 0;"] + for_loop(rng, "i", "0", n, [f"if ({a}[i] == {b}[i])", "    c++;"]) + ["return c;"]
        rt, name = "int", ("count_equal", "matches", "agreement")
    elif kind == "add":
        out = rng.choice(["out", "dst", "sum"])
        ps.insert(2, P(out, et, 0, 0, kind="array", const=False, len_=n))
        op = rng.choice(["+", "-"])
        body = for_loop(rng, "i", "0", n, [f"{out}[i] = {a}[i] {op} {b}[i];"])
        rt, name = "void", ("vec_add" if op == "+" else "vec_sub", "elementwise", "combine_arrays")
    elif kind == "maxabs":
        body = ["long m = 0;"] + for_loop(rng, "i", "0", n, [f"long d = (long){a}[i] - {b}[i];", "if (d < 0)", "    d = -d;", "if (d > m)", "    m = d;"]) + ["return m;"]
        name = ("max_abs_diff", "linf_distance")
    elif kind == "dist":
        body = ["long s = 0;"] + for_loop(rng, "i", "0", n, [f"long d = (long){a}[i] - {b}[i];", "s += d * d;"]) + ["return s;"]
        name = ("sq_distance", "l2_squared")
    else:
        body = for_loop(rng, "i", "0", n, [f"if ({a}[i] != {b}[i])", f"    return {a}[i] < {b}[i] ? -1 : 1;"]) + ["return 0;"]
        rt, name = "int", ("compare", "lex_compare", "cmp_arrays")
    return fname(rng, *name), rt, ps, body, []


def _ind(lines, k=1):
    return ["    " * k + l for l in lines]


def _helper_fn(sig, body):
    return [sig, "{"] + _ind(body) + ["}"]


def _cmp(rng):
    return rng.choice([("<", "asc"), (">", "desc")])


def _sort_helper(rng, et, hname):
    """static sort helper (insertion or bubble or selection), ascending."""
    a, n = "a", "n"
    k = rng.choice(["ins", "bub", "sel"])
    if k == "ins":
        body = block(f"for (int i = 1; i < {n}; i++)", [f"{et} key = {a}[i];", "int j = i - 1;"] +
                     block(f"while (j >= 0 && {a}[j] > key)", [f"{a}[j + 1] = {a}[j];", "j--;"]) + [f"{a}[j + 1] = key;"])
    elif k == "bub":
        body = block(f"for (int i = 0; i + 1 < {n}; i++)", block(f"for (int j = 0; j + 1 < {n} - i; j++)", block(
            f"if ({a}[j] > {a}[j + 1])", [f"{et} t = {a}[j];", f"{a}[j] = {a}[j + 1];", f"{a}[j + 1] = t;"])))
    else:
        body = block(f"for (int i = 0; i < {n}; i++)", ["int m = i;"] + for_loop(rng, "j", "i + 1", n, [
            f"if ({a}[j] < {a}[m])", "    m = j;"]) + [f"{et} t = {a}[i];", f"{a}[i] = {a}[m];", f"{a}[m] = t;"])
    return _helper_fn(f"static void {hname}({et} *{a}, int {n})", body)


def _arr(rng, const, et=None, N=None, rng_vals=None):
    a = rng.choice(ARR_NAMES)
    n = rng.choice(LEN_NAMES)
    et = et or rng.choice(["int", "int", "long"])
    lo, hi = rng_vals or rng.choice([(-100, 100), (-1000, 1000), (0, 50), (-20, 20), (0, 9)])
    N = N or rng.choice([12, 16, 24])
    return a, n, et, [P(a, et, lo, hi, kind="array", const=const, len_=n), P(n, "int", 0, N, kind="len")], max(abs(lo), abs(hi))


@template("array", "sort_search", 1.5)
def sort_then_search(rng):
    a, n, et, ps, B = _arr(rng, False)
    key = rng.choice(["key", "target", "x"])
    ps.append(P(key, et, ps[0]["lo"], ps[0]["hi"]))
    hs = rng.choice(["sort_vals", "isort", "order", "sort_inplace"])
    helpers = [_sort_helper(rng, et, hs)]
    kind = rng.choice(["exact", "lower", "upper", "count"])
    body = [f"{hs}({a}, {n});", "int lo = 0, hi = " + (f"{n} - 1;" if kind == "exact" else f"{n};")]
    if kind == "exact":
        body += block("while (lo <= hi)", ["int mid = lo + (hi - lo) / 2;", f"if ({a}[mid] == {key})", "    return mid;",
                                           f"if ({a}[mid] < {key})", "    lo = mid + 1;", "else", "    hi = mid - 1;"]) + ["return -1;"]
    else:
        c = "<" if kind in ("lower", "count") else "<="
        body += block("while (lo < hi)", ["int mid = lo + (hi - lo) / 2;", f"if ({a}[mid] {c} {key})", "    lo = mid + 1;", "else", "    hi = mid;"])
        if kind == "count":
            body += ["int first = lo;", f"hi = {n};"] + block("while (lo < hi)", ["int mid = lo + (hi - lo) / 2;", f"if ({a}[mid] <= {key})", "    lo = mid + 1;", "else", "    hi = mid;"]) + ["return lo - first;"]
        else:
            body += ["return lo;"]
    names = {"exact": ("sorted_find", "binary_search", "bsearch_idx"), "lower": ("lower_bound", "first_not_less"),
             "upper": ("upper_bound", "first_greater"), "count": ("count_equal_sorted", "equal_range_len")}[kind]
    return fname(rng, *names), "int", ps, body, helpers


@template("array", "dedupe", 1.0)
def dedupe_sorted(rng):
    a, n, et, ps, B = _arr(rng, False, rng_vals=rng.choice([(0, 9), (-5, 5), (0, 20)]))
    hs = rng.choice(["sort_vals", "isort", "sort_asc"])
    pre = rng.random() < 0.7
    body = ([f"{hs}({a}, {n});"] if pre else []) + [f"if ({n} == 0)", "    return 0;", "int w = 1;"] + \
        for_loop(rng, "r", "1", n, [f"if ({a}[r] != {a}[w - 1]) {{", f"    {a}[w] = {a}[r];", "    w++;", "}"]) + ["return w;"]
    return fname(rng, "unique", "dedupe", "compact_unique", "remove_dups"), "int", ps, body, [_sort_helper(rng, et, hs)] if pre else []


@template("array", "partition", 1.0)
def partition(rng):
    a, n, et, ps, B = _arr(rng, False)
    piv = rng.choice(["pivot", "p", "split"])
    ps.append(P(piv, et, ps[0]["lo"], ps[0]["hi"]))
    c = rng.choice(["<", "<=", ">"])
    body = ["int store = 0;"] + for_loop(rng, "i", "0", n, block(f"if ({a}[i] {c} {piv})", [
        f"{et} t = {a}[i];", f"{a}[i] = {a}[store];", f"{a}[store] = t;", "store++;"])) + ["return store;"]
    return fname(rng, "partition", "split_by", "lomuto", "move_small_front"), "int", ps, body, []


@template("array", "histogram", 1.2)
def histogram(rng):
    K = rng.randint(3, 16)
    a, n, et, ps, B = _arr(rng, True, et="int")
    norm = f"(({a}[i] % {K}) + {K}) % {K}" if ps[0]["lo"] < 0 else f"{a}[i] % {K}"
    kind = rng.choice(["mode", "distinct", "maxcount", "first_repeat"])
    body = [f"int cnt[{K}] = {{0}};"] + for_loop(rng, "i", "0", n, [f"cnt[{norm}]++;"])
    if kind == "mode":
        body += ["int best = 0;"] + for_loop(rng, "k", "1", str(K), ["if (cnt[k] > cnt[best])", "    best = k;"]) + ["return best;"]
        name = ("mode_bucket", "most_common_mod")
    elif kind == "distinct":
        body += ["int d = 0;"] + for_loop(rng, "k", "0", str(K), ["if (cnt[k] > 0)", "    d++;"]) + ["return d;"]
        name = ("distinct_buckets", "count_classes")
    elif kind == "maxcount":
        body += ["int m = 0;"] + for_loop(rng, "k", "0", str(K), ["if (cnt[k] > m)", "    m = cnt[k];"]) + ["return m;"]
        name = ("max_frequency", "largest_bucket")
    else:
        body = [f"int seen[{K}] = {{0}};"] + for_loop(rng, "i", "0", n, [f"int b = {norm};", "if (seen[b])", "    return i;", "seen[b] = 1;"]) + ["return -1;"]
        name = ("first_repeat", "first_collision")
    return fname(rng, *name), "int", ps, body, []


@template("array", "window", 1.2)
def window(rng):
    a, n, et, ps, B = _arr(rng, True)
    k = rng.choice(["k", "w", "width"])
    ps.append(P(k, "int", -1, 10))
    kind = rng.choice(["maxsum", "minsum", "count_above"])
    body = [f"if ({k} <= 0 || {k} > {n})", "    return 0;", "long cur = 0;"] + for_loop(rng, "i", "0", k, [f"cur += {a}[i];"])
    if kind == "count_above":
        t = rng.randint(-20, 60)
        body += [f"int c = cur > {t};"] + for_loop(rng, "i", k, n, [f"cur += {a}[i] - {a}[i - {k}];", f"if (cur > {t})", "    c++;"]) + ["return c;"]
        rt = "int"
    else:
        c = ">" if kind == "maxsum" else "<"
        body += ["long best = cur;"] + for_loop(rng, "i", k, n, [f"cur += {a}[i] - {a}[i - {k}];", f"if (cur {c} best)", "    best = cur;"]) + ["return best;"]
        rt = "long"
    return fname(rng, "window_sum", "best_window", "sliding_" + kind), rt, ps, body, []


@template("array", "pairs", 1.2)
def pairs(rng):
    a, n, et, ps, B = _arr(rng, True, rng_vals=rng.choice([(-20, 20), (0, 30), (-5, 5)]))
    t = rng.choice(["target", "sum", "goal"])
    ps.append(P(t, "int", -40, 60))
    kind = rng.choice(["count", "exists", "closest", "diffk"])
    if kind == "count":
        inner = [f"if ({a}[i] + {a}[j] == {t})", "    c++;"]
        body = ["int c = 0;"] + for_loop(rng, "i", "0", n, for_loop(rng, "j", "i + 1", n, inner)) + ["return c;"]
        name = ("count_pairs", "two_sum_count")
    elif kind == "exists":
        body = for_loop(rng, "i", "0", n, for_loop(rng, "j", "i + 1", n, [f"if ({a}[i] + {a}[j] == {t})", "    return i * 100 + j;"])) + ["return -1;"]
        name = ("two_sum", "find_pair")
    elif kind == "closest":
        body = ["long best = -1;"] + for_loop(rng, "i", "0", n, for_loop(rng, "j", "i + 1", n, [
            f"long d = (long){a}[i] + {a}[j] - {t};", "if (d < 0)", "    d = -d;", "if (best < 0 || d < best)", "    best = d;"])) + ["return best;"]
        name = ("closest_pair_gap", "nearest_sum")
    else:
        ps[-1] = P(t, "int", 0, 10)
        body = ["int c = 0;"] + for_loop(rng, "i", "0", n, for_loop(rng, "j", "0", n, [f"if (i != j && {a}[i] - {a}[j] == {t})", "    c++;"])) + ["return c;"]
        name = ("count_diff_pairs", "pairs_with_gap")
    return fname(rng, *name), "long" if kind == "closest" else "int", ps, body, []


@template("array", "rotate_k", 1.0)
def rotate_k(rng):
    a, n, et, ps, B = _arr(rng, False)
    k = rng.choice(["k", "shift", "by"])
    ps.append(P(k, "int", -30, 30))
    rev = rng.choice(["rev", "reverse_range", "flip"])
    helper = _helper_fn(f"static void {rev}({et} *a, int lo, int hi)",
                        block("while (lo < hi)", [f"{et} t = a[lo];", "a[lo] = a[hi];", "a[hi] = t;", "lo++;", "hi--;"]))
    left = rng.random() < 0.5
    body = [f"if ({n} <= 1)", "    return;", f"{k} %= {n};", f"if ({k} < 0)", f"    {k} += {n};"]
    if left:
        body += [f"{rev}({a}, 0, {k} - 1);", f"{rev}({a}, {k}, {n} - 1);", f"{rev}({a}, 0, {n} - 1);"]
    else:
        body += [f"{rev}({a}, 0, {n} - 1);", f"{rev}({a}, 0, {k} - 1);", f"{rev}({a}, {k}, {n} - 1);"]
    return fname(rng, "rotate_left" if left else "rotate_right", "rotate_by", "cyclic_shift"), "void", ps, body, [helper]


@template("array", "kth", 0.8)
def kth(rng):
    a, n, et, ps, B = _arr(rng, False)
    ps.append(P("k", "int", -1, 16))
    c = rng.choice(["<", ">"])
    body = ["if (k < 0 || k >= " + n + ")", "    return 0;"] + for_loop(rng, "i", "0", "k + 1", ["int m = i;"] + for_loop(rng, "j", "i + 1", n, [
        f"if ({a}[j] {c} {a}[m])", "    m = j;"]) + [f"{et} t = {a}[i];", f"{a}[i] = {a}[m];", f"{a}[m] = t;"]) + [f"return {a}[k];"]
    return fname(rng, "kth_smallest" if c == "<" else "kth_largest", "select_kth", "nth_element"), et, ps, body, []


@template("array", "stats", 1.2)
def stats(rng):
    a, n, et, ps, B = _arr(rng, True)
    helpers = []
    parts = rng.sample(["min", "max", "sum", "neg", "even", "absmax"], rng.randint(3, 5))
    body = [f"if ({n} == 0)", "    return 0;"]
    decl = []
    loop = []
    for p in parts:
        if p == "min":
            decl.append(f"long mn = {a}[0];"); loop += [f"if ({a}[i] < mn)", f"    mn = {a}[i];"]
        if p == "max":
            decl.append(f"long mx = {a}[0];"); loop += [f"if ({a}[i] > mx)", f"    mx = {a}[i];"]
        if p == "sum":
            decl.append("long sum = 0;"); loop += [f"sum += {a}[i];"]
        if p == "neg":
            decl.append("int neg = 0;"); loop += [f"neg += {a}[i] < 0;"]
        if p == "even":
            decl.append("int even = 0;"); loop += [f"if ({a}[i] % 2 == 0)", "    even++;"]
        if p == "absmax":
            decl.append("long am = 0;"); loop += [f"long av = {a}[i] < 0 ? -(long){a}[i] : {a}[i];", "if (av > am)", "    am = av;"]
    names = {"min": "mn", "max": "mx", "sum": "sum", "neg": "neg", "even": "even", "absmax": "am"}
    terms = [names[p] for p in parts]
    rng.shuffle(terms)
    ret = terms[0] + "".join(f" {rng.choice(['+', '-'])} {t}" for t in terms[1:])
    if rng.random() < 0.4 and "mn" in terms and "mx" in terms:
        ret = "(mx - mn) * 1000 + " + " + ".join(t for t in terms if t not in ("mn", "mx")) if len(terms) > 2 else "mx - mn"
    body += decl + for_loop(rng, "i", "0", n, loop) + [f"return {ret};"]
    return fname(rng, "summary", "stats_code", "profile", "describe"), "long", ps, body, helpers


@template("array", "matrix", 1.0)
def matrix(rng):
    """Flat row-major matrix: rows*cols <= len, everything bounds-checked."""
    m = rng.choice(["m", "grid", "mat", "cells"])
    lo, hi = rng.choice([(-9, 9), (0, 9), (-100, 100)])
    ps = [P(m, "int", lo, hi, kind="array", const=True, len_="len"), P("len", "int", 0, 24, kind="len"),
          P("cols", "int", 0, 6)]
    kind = rng.choice(["rowmax", "trace", "colsum", "transpose_eq", "saddle"])
    body = ["if (cols <= 0)", "    return 0;", "int rows = len / cols;"]
    if kind == "rowmax":
        body += ["long best = 0;"] + for_loop(rng, "r", "0", "rows", ["long s = 0;"] + for_loop(rng, "c", "0", "cols", [f"s += {m}[r * cols + c];"]) + ["if (r == 0 || s > best)", "    best = s;"]) + ["return best;"]
        name = ("max_row_sum", "best_row")
    elif kind == "trace":
        body += ["long t = 0;"] + for_loop(rng, "i", "0", "rows", ["if (i < cols)", f"    t += {m}[i * cols + i];"]) + ["return t;"]
        name = ("trace", "diag_sum")
    elif kind == "colsum":
        cc = rng.randint(0, 5)
        body += [f"if ({cc} >= cols)", "    return 0;", "long s = 0;"] + for_loop(rng, "r", "0", "rows", [f"s += {m}[r * cols + {cc}];"]) + ["return s;"]
        name = ("column_sum", "col_total")
    elif kind == "transpose_eq":
        body += ["if (rows != cols)", "    return 0;"] + for_loop(rng, "r", "0", "rows", for_loop(rng, "c", "r + 1", "cols", [
            f"if ({m}[r * cols + c] != {m}[c * cols + r])", "    return 0;"])) + ["return 1;"]
        name = ("is_symmetric", "symmetric")
    else:
        body += ["int count = 0;"] + for_loop(rng, "r", "0", "rows", for_loop(rng, "c", "0", "cols", [
            f"int v = {m}[r * cols + c], ok = 1;"] + for_loop(rng, "k", "0", "cols", [f"if ({m}[r * cols + k] < v)", "    ok = 0;"]) +
            for_loop(rng, "k", "0", "rows", [f"if ({m}[k * cols + c] > v)", "    ok = 0;"]) + ["count += ok;"])) + ["return count;"]
        name = ("count_saddle", "saddle_points")
    return fname(rng, *name), "long" if kind in ("rowmax", "trace", "colsum") else "int", ps, body, []


@template("array", "merge", 1.0)
def merge(rng):
    """merge two arrays (each sorted first by a helper) into out of size n+m."""
    et = "int"
    lo, hi = rng.choice([(-50, 50), (0, 20)])
    hs = rng.choice(["sort_vals", "isort"])
    # out shares length param "total" = n + m is not expressible; use equal halves
    ps = [P("a", et, lo, hi, kind="array", const=False, len_="n"), P("b", et, lo, hi, kind="array", const=False, len_="n"),
          P("n", "int", 0, 10, kind="len")]
    kind = rng.choice(["common", "union_count", "merged_median"])
    body = [f"{hs}(a, n);", f"{hs}(b, n);", "int i = 0, j = 0, c = 0;"]
    if kind == "common":
        body += block("while (i < n && j < n)", ["if (a[i] == b[j]) {", "    c++;", "    i++;", "    j++;", "} else if (a[i] < b[j]) {", "    i++;", "} else {", "    j++;", "}"]) + ["return c;"]
        name = ("count_common", "intersection_size")
    elif kind == "union_count":
        body += ["int last = 0, have = 0;"] + block("while (i < n || j < n)", [
            "int v;", "if (j >= n || (i < n && a[i] <= b[j]))", "    v = a[i++];", "else", "    v = b[j++];",
            "if (!have || v != last) {", "    c++;", "    last = v;", "    have = 1;", "}"]) + ["return c;"]
        name = ("union_size", "distinct_merged")
    else:
        body += ["int target = n, v = 0;"] + block("while (c <= target && (i < n || j < n))", [
            "if (j >= n || (i < n && a[i] <= b[j]))", "    v = a[i++];", "else", "    v = b[j++];", "c++;"]) + ["return n == 0 ? 0 : v;"]
        name = ("merged_median", "median_of_two")
    return fname(rng, *name), "int", ps, body, [_sort_helper(rng, et, hs)]


def _str(rng, const=True, lo=32, hi=126, N=24):
    s = rng.choice(STR_NAMES)
    n = rng.choice(LEN_NAMES)
    return s, n, [P(s, "char", lo, hi, kind="array", const=const, len_=n), P(n, "int", 0, N, kind="len")]


@template("string", "classify", 1.5)
def str_classify(rng):
    s, n, ps = _str(rng)
    helper_name = rng.choice(["is_alpha", "is_letter", "is_vowel", "is_digit", "is_space", "is_upper", "is_punct"])
    conds = {"is_alpha": "(c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')",
             "is_letter": "(c | 32) >= 'a' && (c | 32) <= 'z'",
             "is_vowel": "c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u' || c == 'A' || c == 'E' || c == 'I' || c == 'O' || c == 'U'",
             "is_digit": "c >= '0' && c <= '9'", "is_space": "c == ' ' || c == '\\t' || c == '\\n'",
             "is_upper": "c >= 'A' && c <= 'Z'", "is_punct": "c == '.' || c == ',' || c == '!' || c == '?' || c == '-'"}
    if rng.random() < 0.6:
        # randomized class: a char range or a small set
        if rng.random() < 0.5:
            lo_c = rng.randint(33, 110)
            hi_c = lo_c + rng.randint(1, 15)
            cond = f"c >= '{chr(lo_c)}' && c <= '{chr(hi_c)}'" if chr(lo_c) not in "\\'" and chr(hi_c) not in "\\'" else f"c >= {lo_c} && c <= {hi_c}"
            helper_name = rng.choice(["in_class", "in_band", "matches", "is_target"])
        else:
            chars = rng.sample("abcdefghijklmnopqrstuvwxyz0123456789 .,!?-ABCDEFG", rng.randint(2, 5))
            cond = " || ".join(f"c == '{ch}'" for ch in chars)
            helper_name = rng.choice(["is_special", "is_marker", "is_member", "is_sep"])
        conds[helper_name] = cond
    helper = _helper_fn(f"static int {helper_name}(char c)", [f"return {conds[helper_name]};"])
    kind = rng.choice(["count", "longest", "first", "ratio", "strip"])
    if kind == "count":
        body = ["int c = 0;"] + for_loop(rng, "i", "0", n, [f"if ({helper_name}({s}[i]))", "    c++;"]) + ["return c;"]
    elif kind == "longest":
        body = ["int best = 0, cur = 0;"] + for_loop(rng, "i", "0", n, [f"if ({helper_name}({s}[i])) {{", "    cur++;", "    if (cur > best)", "        best = cur;", "} else {", "    cur = 0;", "}"]) + ["return best;"]
    elif kind == "first":
        body = for_loop(rng, "i", "0", n, [f"if ({'!' if rng.random() < 0.4 else ''}{helper_name}({s}[i]))", "    return i;"]) + ["return -1;"]
    elif kind == "ratio":
        body = [f"if ({n} == 0)", "    return 0;", "int c = 0;"] + for_loop(rng, "i", "0", n, [f"c += {helper_name}({s}[i]) != 0;"]) + [f"return c * 100 / {n};"]
    else:
        ps[0]["const"] = False
        body = ["int w = 0;"] + for_loop(rng, "i", "0", n, [f"if (!{helper_name}({s}[i]))", f"    {s}[w++] = {s}[i];"]) + ["return w;"]
    return fname(rng, f"{kind}_{helper_name[3:]}", f"{helper_name[3:]}_{kind}", f"scan_{kind}"), "int", ps, body, [helper]


@template("string", "transform", 1.5)
def str_transform(rng):
    s, n, ps = _str(rng, const=False)
    kind = rng.choice(["capitalize", "swapcase", "rev_words", "squeeze_spaces", "rot13", "reverse", "leet"])
    helpers = []
    rt = "void"
    if kind == "capitalize":
        body = ["int start = 1;"] + for_loop(rng, "i", "0", n, [f"char c = {s}[i];", "if (c == ' ') {", "    start = 1;", "} else {",
                                                                   "    if (start && c >= 'a' && c <= 'z')", f"        {s}[i] = c - 'a' + 'A';",
                                                                   "    else if (!start && c >= 'A' && c <= 'Z')", f"        {s}[i] = c - 'A' + 'a';", "    start = 0;", "}"])
        ps[0]["lo"], ps[0]["hi"] = 32, 122
    elif kind == "swapcase":
        body = for_loop(rng, "i", "0", n, [f"if ({s}[i] >= 'a' && {s}[i] <= 'z')", f"    {s}[i] -= 32;", f"else if ({s}[i] >= 'A' && {s}[i] <= 'Z')", f"    {s}[i] += 32;"])
    elif kind == "rev_words":
        rv = rng.choice(["rev", "reverse_span"])
        helpers.append(_helper_fn(f"static void {rv}(char *s, int i, int j)", block("while (i < j)", ["char t = s[i];", "s[i] = s[j];", "s[j] = t;", "i++;", "j--;"])))
        ps[0]["lo"], ps[0]["hi"] = 32, 100
        body = ["int start = 0;"] + for_loop(rng, "i", "0", f"{n}", block(f"if (i == {n} || {s}[i] == ' ')", [f"{rv}({s}, start, i - 1);", "start = i + 1;"]), cmp="<=")
        body = [l.replace(f"if (i == {n} || {s}[i] == ' ')", f"if (i == {n} || {s}[i] == ' ')") for l in body]
        if rng.random() < 0.5:
            body.append(f"{rv}({s}, 0, {n} - 1);")
    elif kind == "squeeze_spaces":
        ps[0]["lo"], ps[0]["hi"] = 32, 35
        body = ["int w = 0;"] + for_loop(rng, "i", "0", n, [f"if ({s}[i] == ' ' && w > 0 && {s}[w - 1] == ' ')", "    continue;", f"{s}[w++] = {s}[i];"]) + ["return w;"]
        rt = "int"
    elif kind == "rot13":
        r = rng.randint(1, 25)
        both = rng.random() < 0.6
        body = for_loop(rng, "i", "0", n, [f"char c = {s}[i];", "if (c >= 'a' && c <= 'z')", f"    {s}[i] = (c - 'a' + {r}) % 26 + 'a';"] +
                        (["else if (c >= 'A' && c <= 'Z')", f"    {s}[i] = (c - 'A' + {r}) % 26 + 'A';"] if both else []) +
                        ([ "else if (c >= '0' && c <= '9')", f"    {s}[i] = (c - '0' + {r % 10}) % 10 + '0';"] if rng.random() < 0.4 else []))
    elif kind == "reverse":
        body = block(f"for (int i = 0, j = {n} - 1; i < j; i++, j--)", [f"char t = {s}[i];", f"{s}[i] = {s}[j];", f"{s}[j] = t;"])
    else:
        mp = rng.sample([("a", "4"), ("e", "3"), ("i", "1"), ("o", "0"), ("s", "5"), ("t", "7")], 3)
        body = ["int changed = 0;"] + for_loop(rng, "i", "0", n, ["switch (" + s + "[i]) {"] + sum(
            ([f"case '{x}':", f"    {s}[i] = '{y}';", "    changed++;", "    break;"] for x, y in mp), []) + ["default:", "    break;", "}"]) + ["return changed;"]
        rt = "int"
    return fname(rng, kind, f"str_{kind}", f"{kind}_inplace"), rt, ps, body, helpers


@template("string", "parse", 1.2)
def str_parse(rng):
    s, n, ps = _str(rng, N=9)
    kind = rng.choice(["atoi_signed", "hex", "binary", "sum_numbers", "count_numbers"])
    if kind == "atoi_signed":
        ps[0]["lo"], ps[0]["hi"] = 43, 57
        body = ["int i = 0, sign = 1;", "long v = 0;", f"if (i < {n} && ({s}[i] == '-' || {s}[i] == '+')) {{", f"    if ({s}[i] == '-')", "        sign = -1;", "    i++;", "}"] + \
            block(f"while (i < {n} && {s}[i] >= '0' && {s}[i] <= '9')", [f"v = v * 10 + ({s}[i] - '0');", "i++;"]) + ["return sign * v;"]
    elif kind == "hex":
        ps[0]["lo"], ps[0]["hi"] = 48, 102
        body = ["long v = 0;"] + for_loop(rng, "i", "0", n, [f"char c = {s}[i];", "int d;", "if (c >= '0' && c <= '9')", "    d = c - '0';",
                                                             "else if (c >= 'a' && c <= 'f')", "    d = c - 'a' + 10;", "else if (c >= 'A' && c <= 'F')", "    d = c - 'A' + 10;",
                                                             "else", "    return -1;", "v = v * 16 + d;"]) + ["return v;"]
        ps[1]["hi"] = 7
    elif kind == "binary":
        ps[0]["lo"], ps[0]["hi"] = 48, 50
        body = ["long v = 0;"] + for_loop(rng, "i", "0", n, [f"if ({s}[i] != '0' && {s}[i] != '1')", "    return -1;", f"v = v * 2 + ({s}[i] - '0');"]) + ["return v;"]
    elif kind == "sum_numbers":
        ps[0]["lo"], ps[0]["hi"] = 44, 57
        ps[1]["hi"] = 24
        body = ["long total = 0, cur = 0;"] + for_loop(rng, "i", "0", n, [f"if ({s}[i] >= '0' && {s}[i] <= '9') {{", "    if (cur < 100000)", f"        cur = cur * 10 + ({s}[i] - '0');", "} else {", "    total += cur;", "    cur = 0;", "}"]) + ["return total + cur;"]
    else:
        ps[0]["lo"], ps[0]["hi"] = 44, 57
        ps[1]["hi"] = 24
        body = ["int c = 0, in = 0;"] + for_loop(rng, "i", "0", n, [f"int d = {s}[i] >= '0' && {s}[i] <= '9';", "if (d && !in)", "    c++;", "in = d;"]) + ["return c;"]
    return fname(rng, kind, f"parse_{kind}", f"str_{kind}"), "int" if kind == "count_numbers" else "long", ps, body, []


@template("string", "two", 1.2)
def str_two(rng):
    a, b = rng.sample(["s", "t", "a", "b", "pat", "text", "x", "y"], 2)
    lo, hi = rng.choice([(97, 100), (97, 122), (65, 70)])
    kind = rng.choice(["anagram", "count_sub", "common_prefix", "hamming", "is_sub_seq", "find_sub"])
    if kind in ("count_sub", "is_sub_seq", "find_sub"):
        ps = [P(a, "char", lo, lo + 2, kind="array", const=True, len_="n"), P("n", "int", 0, 20, kind="len"),
              P(b, "char", lo, lo + 2, kind="array", const=True, len_="m"), P("m", "int", 0, 4, kind="len")]
    else:
        ps = [P(a, "char", lo, hi, kind="array", const=True, len_="n"), P(b, "char", lo, hi, kind="array", const=True, len_="n"),
              P("n", "int", 0, 12, kind="len")]
    if kind == "anagram":
        body = ["int cnt[256] = {0};"] + for_loop(rng, "i", "0", "n", [f"cnt[(unsigned char){a}[i]]++;", f"cnt[(unsigned char){b}[i]]--;"]) + \
            for_loop(rng, "i", "0", "256", ["if (cnt[i] != 0)", "    return 0;"]) + ["return 1;"]
    elif kind == "count_sub":
        body = ["if (m == 0)", "    return 0;", "int c = 0;"] + for_loop(rng, "i", "0", "n - m", ["int j = 0;", f"while (j < m && {a}[i + j] == {b}[j])", "    j++;", "if (j == m)", "    c++;"], cmp="<= ") + ["return c;"]
        body = [l.replace("i <=  n - m", "i + m <= n") for l in body]
    elif kind == "find_sub":
        body = for_loop(rng, "i", "0", "n", ["int j = 0;", f"while (j < m && {a}[i + j] == {b}[j])", "    j++;", "if (j == m)", "    return i;"], cmp="+ m <=") + ["return -1;"]
    elif kind == "is_sub_seq":
        body = ["int j = 0;"] + for_loop(rng, "i", "0", "n", [f"if (j < m && {a}[i] == {b}[j])", "    j++;"]) + ["return j == m;"]
    elif kind == "common_prefix":
        body = ["int i = 0;"] + block(f"while (i < n && {a}[i] == {b}[i])", ["i++;"]) + ["return i;"]
    else:
        body = ["int d = 0;"] + for_loop(rng, "i", "0", "n", [f"if ({a}[i] != {b}[i])", "    d++;"]) + ["return d;"]
    if rng.random() < 0.5 and kind not in ("anagram",):
        # case-insensitive / folded comparison variant
        fold = rng.choice(["| 32", "& ~32", "% 32"])
        body = [re.sub(r"(\b%s\[[^\]]+\]|\b%s\[[^\]]+\])\s*(==|!=)\s*(\w+\[[^\]]+\])" % (a, b),
                       lambda m: f"({m.group(1)} {fold}) {m.group(2)} ({m.group(3)} {fold})", l) for l in body]
    return fname(rng, kind, f"str_{kind}", f"{kind}_len"), "int", ps, body, []


@template("string", "basic", 1.5)
def str_basic(rng):
    """the original array.chars routines, now their own family."""
    return array_chars(rng)


@template("loop", "number_theory", 1.5)
def number_theory(rng):
    kind = rng.choice(["perfect_count", "armstrong", "pal_num", "triples", "sieve", "totient", "amicable", "happy", "abundant"])
    x = rng.choice(["n", "limit", "upto", "max"])
    if kind == "perfect_count":
        ps = [P(x, "int", 0, 600)]
        helper = _helper_fn("static int divisor_sum(int v)", ["int s = 0;"] + for_loop(rng, "d", "1", "v", ["if (v % d == 0)", "    s += d;"]))
        helper = helper[:-1] + ["    return s;", "}"]
        body = ["int c = 0;"] + for_loop(rng, "i", "2", x, ["if (divisor_sum(i) == i)", "    c++;"], cmp="<=") + ["return c;"]
        return fname(rng, "count_perfect", "perfect_upto"), "int", ps, body, [helper]
    if kind == "armstrong":
        ps = [P(x, "int", 0, 100000)]
        body = ["int digits = 0, t = " + x + ";"] + block("while (t > 0)", ["digits++;", "t /= 10;"]) + \
            ["long s = 0;", "t = " + x + ";"] + block("while (t > 0)", ["int d = t % 10;", "long p = 1;"] + for_loop(rng, "k", "0", "digits", ["p *= d;"]) + ["s += p;", "t /= 10;"]) + [f"return s == {x};"]
        return fname(rng, "is_armstrong", "narcissistic"), "int", ps, body, []
    if kind == "pal_num":
        b = rng.choice([10, 2, 8, 16])
        ps = [P(x, "int", -100, 1000000)]
        body = [f"if ({x} < 0)", "    return 0;", f"long r = 0, t = {x};"] + block("while (t > 0)", [f"r = r * {b} + t % {b};", f"t /= {b};"]) + [f"return r == {x};"]
        return fname(rng, "is_palindrome_num", f"palindrome_base{b}"), "int", ps, body, []
    if kind == "triples":
        ps = [P(x, "int", 0, 40)]
        body = ["int c = 0;"] + for_loop(rng, "a", "1", x, for_loop(rng, "b", "a", x, for_loop(rng, "c2", "b", x, ["if (a * a + b * b == c2 * c2)", "    c++;"], cmp="<="), cmp="<="), cmp="<=") + ["return c;"]
        return fname(rng, "count_triples", "pythagorean"), "int", ps, body, []
    if kind == "sieve":
        ps = [P(x, "int", -5, 500)]
        body = ["char comp[501] = {0};", "int c = 0;", f"if ({x} > 500)", f"    {x} = 500;"] + for_loop(rng, "i", "2", x, ["if (comp[i])", "    continue;", "c++;"] + for_loop(rng, "j", "i * i", x, ["comp[j] = 1;"], step="i", cmp="<="), cmp="<=") + ["return c;"]
        return fname(rng, "count_primes", "prime_count", "sieve_count"), "int", ps, body, []
    if kind == "totient":
        ps = [P(x, "int", 1, 5000)]
        body = [f"int r = {x};", f"int v = {x};"] + block("for (int p = 2; p * p <= v; p++)", block("if (v % p == 0)", block("while (v % p == 0)", ["v /= p;"]) + ["r -= r / p;"])) + ["if (v > 1)", "    r -= r / v;", "return r;"]
        return fname(rng, "phi", "totient", "euler_phi"), "int", ps, body, []
    if kind == "amicable":
        ps = [P("a", "int", 1, 3000), P("b", "int", 1, 3000)]
        helper = _helper_fn("static int proper_sum(int v)", ["int s = 0;"] + for_loop(rng, "d", "1", "v", ["if (v % d == 0)", "    s += d;"]) + ["return s;"])
        body = ["return a != b && proper_sum(a) == b && proper_sum(b) == a;"]
        return fname(rng, "amicable", "is_amicable_pair"), "int", ps, body, [helper]
    if kind == "happy":
        ps = [P(x, "int", 1, 100000)]
        helper = _helper_fn("static int digit_squares(int v)", ["int s = 0;"] + block("while (v > 0)", ["int d = v % 10;", "s += d * d;", "v /= 10;"]) + ["return s;"])
        body = ["int steps = 0;"] + block(f"while ({x} != 1 && {x} != 4 && steps < 100)", [f"{x} = digit_squares({x});", "steps++;"]) + [f"return {x} == 1;"]
        return fname(rng, "is_happy", "happy_number"), "int", ps, body, [helper]
    ps = [P("lo", "int", 1, 300), P("hi", "int", 1, 300)]
    helper = _helper_fn("static int sum_proper(int v)", ["int s = 0;"] + for_loop(rng, "d", "1", "v / 2", ["if (v % d == 0)", "    s += d;"], cmp="<=") + ["return s;"])
    body = ["int c = 0;"] + for_loop(rng, "i", "lo", "hi", ["if (sum_proper(i) > i)", "    c++;"], cmp="<=") + ["return c;"]
    return fname(rng, "count_abundant", "abundant_in_range"), "int", ps, body, [helper]


@template("loop", "gcd_more", 1.0)
def gcd_more(rng):
    kind = rng.choice(["binary", "ext", "lcm_range", "gcd_count", "steps", "reduce_frac"])
    a, b = rng.sample(["a", "b", "x", "y", "p", "q"], 2)
    if kind == "binary":
        ps = [P(a, "unsigned int", 0, 1000000), P(b, "unsigned int", 0, 1000000)]
        body = [f"if ({a} == 0)", f"    return {b};", f"if ({b} == 0)", f"    return {a};", "int shift = 0;"] + \
            block(f"while ((({a} | {b}) & 1) == 0)", [f"{a} >>= 1;", f"{b} >>= 1;", "shift++;"]) + block(f"while (({a} & 1) == 0)", [f"{a} >>= 1;"]) + \
            block(f"while ({b} != 0)", block(f"while (({b} & 1) == 0)", [f"{b} >>= 1;"]) + [f"if ({a} > {b}) {{", f"    unsigned int t = {a};", f"    {a} = {b};", f"    {b} = t;", "}", f"{b} -= {a};"]) + [f"return {a} << shift;"]
        return fname(rng, "binary_gcd", "stein_gcd"), "unsigned int", ps, body, []
    if kind == "ext":
        ps = [P(a, "long", 0, 10000), P(b, "long", 0, 10000)]
        body = ["long x0 = 1, x1 = 0;"] + block(f"while ({b} != 0)", [f"long qt = {a} / {b};", f"long t = {a} - qt * {b};", f"{a} = {b};", f"{b} = t;", "t = x0 - qt * x1;", "x0 = x1;", "x1 = t;"]) + ["return x0;"]
        return fname(rng, "ext_gcd_coef", "bezout_x"), "long", ps, body, []
    if kind == "lcm_range":
        ps = [P("n", "int", 0, 20)]
        helper = _helper_fn("static long gcd_l(long a, long b)", block("while (b != 0)", ["long t = a % b;", "a = b;", "b = t;"]) + ["return a;"])
        body = ["long l = 1;"] + for_loop(rng, "i", "2", "n", ["l = l / gcd_l(l, i) * i;"], cmp="<=") + ["return l;"]
        return fname(rng, "lcm_upto", "smallest_multiple"), "long", ps, body, [helper]
    if kind == "gcd_count":
        ps = [P("n", "int", 0, 60)]
        helper = _helper_fn("static int g(int a, int b)", ["return b == 0 ? a : g(b, a % b);"])
        body = ["int c = 0;"] + for_loop(rng, "i", "1", "n", ["if (g(i, n) == 1)", "    c++;"], cmp="<=") + ["return c;"]
        return fname(rng, "count_coprime", "coprime_upto"), "int", ps, body, [helper]
    if kind == "steps":
        ps = [P(a, "int", 0, 100000), P(b, "int", 0, 100000)]
        body = ["int steps = 0;"] + block(f"while ({b} != 0)", [f"int t = {a} % {b};", f"{a} = {b};", f"{b} = t;", "steps++;"]) + ["return steps;"]
        return fname(rng, "euclid_steps", "gcd_iterations"), "int", ps, body, []
    ps = [P("num", "int", -1000, 1000), P("den", "int", -1000, 1000)]
    body = ["if (den == 0)", "    return 0;", "int a = num < 0 ? -num : num, b = den < 0 ? -den : den;"] + block("while (b != 0)", ["int t = a % b;", "a = b;", "b = t;"]) + \
        ["int sign = (num < 0) != (den < 0) ? -1 : 1;", "if (num == 0)", "    return 0;", "return sign * (num < 0 ? -num : num) / a * 10000 + (den < 0 ? -den : den) / a;"]
    return fname(rng, "reduce_fraction", "simplify"), "int", ps, body, []


@template("loop", "sim", 1.2)
def sim(rng):
    """small simulations with a step cap: loan payoff, population, bouncing."""
    kind = rng.choice(["payoff", "growth", "bounce", "josephus", "staircase"])
    if kind == "payoff":
        ps = [P("debt", "int", 0, 100000), P("pay", "int", 0, 5000), P("rate", "int", 0, 20)]
        body = ["int months = 0;", "long d = debt;"] + block("while (d > 0 && months < 600)", ["d += d * rate / 1000;", "d -= pay;", "months++;"]) + ["return d > 0 ? -1 : months;"]
        return fname(rng, "months_to_payoff", "payoff_time"), "int", ps, body, []
    if kind == "growth":
        ps = [P("start", "int", 1, 1000), P("pct", "int", 0, 50), P("goal", "int", 0, 1000000)]
        body = ["long p = start;", "int years = 0;"] + block("while (p < goal && years < 200)", ["p = p + p * pct / 100 + 1;", "years++;"]) + ["return years;"]
        return fname(rng, "years_to_goal", "growth_steps"), "int", ps, body, []
    if kind == "bounce":
        ps = [P("h", "int", 0, 10000), P("keep", "int", 0, 99)]
        body = ["long total = h;", "int bounces = 0;"] + block("while (h > 0 && bounces < 100)", ["h = h * keep / 100;", "total += 2L * h;", "bounces++;"]) + ["return total;"]
        return fname(rng, "bounce_distance", "total_travel"), "long", ps, body, []
    if kind == "josephus":
        ps = [P("n", "int", 0, 200), P("k", "int", 1, 20)]
        body = ["if (n <= 0)", "    return -1;", "int pos = 0;"] + for_loop(rng, "i", "2", "n", ["pos = (pos + k) % i;"], cmp="<=") + ["return pos;"]
        return fname(rng, "josephus", "last_survivor"), "int", ps, body, []
    ps = [P("n", "int", 0, 40), P("maxstep", "int", 1, 3)]
    body = ["long ways[41] = {0};", "ways[0] = 1;"] + for_loop(rng, "i", "1", "n", for_loop(rng, "s", "1", "maxstep", ["if (i - s >= 0)", "    ways[i] += ways[i - s];"], cmp="<="), cmp="<=") + ["return ways[n];"]
    return fname(rng, "count_ways", "staircase"), "long", ps, body, []


@template("loop", "bits_more", 1.0)
def bits_more(rng):
    x = rng.choice(["x", "v", "w", "bits"])
    ps = [P(x, "unsigned int", 0, 2**32 - 1)]
    kind = rng.choice(["longest_ones", "gray", "next_pow2", "swap_nibbles", "count_runs", "rotl", "hamming"])
    if kind == "longest_ones":
        body = ["int best = 0, cur = 0;"] + block(f"while ({x})", [f"if ({x} & 1u) {{", "    cur++;", "    if (cur > best)", "        best = cur;", "} else {", "    cur = 0;", "}", f"{x} >>= 1;"]) + ["return best;"]
        rt = "int"
    elif kind == "gray":
        body = [f"unsigned int g = {x} ^ ({x} >> 1);", "unsigned int b = g;"] + block("for (unsigned int s = g >> 1; s; s >>= 1)", ["b ^= s;"]) + [f"return b == {x} ? g : 0u;"]
        rt = "unsigned int"
    elif kind == "next_pow2":
        ps = [P(x, "unsigned int", 0, 2**31)]
        body = [f"if ({x} <= 1)", "    return 1;", "unsigned int p = 1;"] + block(f"while (p < {x})", ["p <<= 1;"]) + ["return p;"]
        rt = "unsigned int"
    elif kind == "swap_nibbles":
        body = ["unsigned int r = 0;"] + for_loop(rng, "i", "0", "4", [f"unsigned int byte = ({x} >> (8 * i)) & 0xffu;", "byte = ((byte & 0x0fu) << 4) | (byte >> 4);", "r |= byte << (8 * i);"]) + ["return r;"]
        rt = "unsigned int"
    elif kind == "count_runs":
        body = ["int runs = 0, prev = -1;"] + for_loop(rng, "i", "0", "32", [f"int bit = ({x} >> i) & 1;", "if (bit != prev)", "    runs++;", "prev = bit;"]) + ["return runs;"]
        rt = "int"
    elif kind == "rotl":
        ps.append(P("r", "int", -40, 40))
        body = ["r %= 32;", "if (r < 0)", "    r += 32;", "if (r == 0)", f"    return {x};", f"return ({x} << r) | ({x} >> (32 - r));"]
        rt = "unsigned int"
    else:
        ps.append(P("y", "unsigned int", 0, 2**32 - 1))
        body = [f"unsigned int d = {x} ^ y;", "int c = 0;"] + block("while (d)", ["d &= d - 1;", "c++;"]) + ["return c;"]
        rt = "int"
    return fname(rng, kind, f"bits_{kind}"), rt, ps, body, []


@template("cond", "piecewise", 1.5)
def piecewise(rng):
    x = rng.choice(["income", "x", "amount", "score", "temp", "speed", "units"])
    k = rng.randint(3, 6)
    ths = sorted(rng.sample(range(0, 10000, 50), k))
    rates = [rng.randint(0, 40) for _ in range(k + 1)]
    ps = [P(x, "int", -500, 12000)]
    style = rng.choice(["bracket", "chain"])
    if style == "bracket":
        body = [f"if ({x} <= 0)", "    return 0;", "long tax = 0;", "int prev = 0;"]
        for t, r in zip(ths, rates):
            body += block(f"if ({x} > {t})", [f"tax += (long)({t} - prev) * {r};", f"prev = {t};"]) + ["else", f"    return tax + (long)({x} - prev) * {r};"]
        body += [f"return tax + (long)({x} - prev) * {rates[-1]};"]
        name = ("bracket_tax", "tiered_cost", "progressive")
    else:
        body = []
        for i, t in enumerate(ths):
            off = rng.randint(-50, 50)
            body += [f"{'if' if i == 0 else 'else if'} ({x} < {t})", f"    return {x} * {rates[i]} / 10 {'-' if off < 0 else '+'} {abs(off)};"]
        off = rng.randint(-50, 50)
        body += [f"return {x} * {rates[-1]} / 10 {'-' if off < 0 else '+'} {abs(off)};"]
        name = ("grade_value", "tier", "rate_for")
    return fname(rng, *name), "long", ps, body, []


@template("cond", "calendar", 1.0)
def calendar(rng):
    kind = rng.choice(["leap", "days_in_month", "day_of_year", "valid_date", "weekday"])
    leap = _helper_fn("static int is_leap(int y)", ["return (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;"])
    dim = _helper_fn("static int month_days(int y, int m)", ["if (m == 2)", "    return is_leap(y) ? 29 : 28;", "if (m == 4 || m == 6 || m == 9 || m == 11)", "    return 30;", "return 31;"])
    if kind == "leap":
        return fname(rng, "is_leap_year", "leap"), "int", [P("year", "int", 1, 3000)], ["return (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;"], []
    if kind == "days_in_month":
        return fname(rng, "days_in_month", "month_length"), "int", [P("y", "int", 1, 3000), P("m", "int", 1, 12)], ["return month_days(y, m);"], [leap, dim]
    if kind == "day_of_year":
        ps = [P("y", "int", 1, 3000), P("m", "int", 1, 12), P("d", "int", 1, 28)]
        body = ["int doy = d;"] + for_loop(rng, "i", "1", "m", ["doy += month_days(y, i);"]) + ["return doy;"]
        return fname(rng, "day_of_year", "ordinal_day"), "int", ps, body, [leap, dim]
    if kind == "valid_date":
        ps = [P("y", "int", -5, 3000), P("m", "int", -1, 14), P("d", "int", -1, 33)]
        body = ["if (y < 1 || m < 1 || m > 12 || d < 1)", "    return 0;", "return d <= month_days(y, m);"]
        return fname(rng, "valid_date", "is_valid_date"), "int", ps, body, [leap, dim]
    ps = [P("y", "int", 1600, 2400), P("m", "int", 1, 12), P("d", "int", 1, 28)]
    body = ["", "if (m < 3) {", "    m += 12;", "    y -= 1;", "}", "int k = y % 100, j = y / 100;",
            "int h = (d + 13 * (m + 1) / 5 + k + k / 4 + j / 4 + 5 * j) % 7;", "return h;"][1:]
    return fname(rng, "weekday", "zeller"), "int", ps, body, []


@template("cond", "state", 1.0)
def state_machine(rng):
    s, n, ps = _str(rng, lo=32, hi=60)
    kind = rng.choice(["comment_strip_count", "number_tokens", "balanced", "vending"])
    if kind == "balanced":
        ps[0]["lo"], ps[0]["hi"] = 40, 41
        body = ["int depth = 0;"] + for_loop(rng, "i", "0", n, [f"if ({s}[i] == '(')", "    depth++;", f"else if ({s}[i] == ')') {{", "    depth--;", "    if (depth < 0)", "        return 0;", "}"]) + ["return depth == 0;"]
        return fname(rng, "balanced", "parens_ok"), "int", ps, body, []
    if kind == "vending":
        ps = [P("coins", "char", 48, 53, kind="array", const=True, len_="n"), P("n", "int", 0, 16, kind="len"), P("price", "int", 0, 40)]
        body = ["int credit = 0, sold = 0;"] + for_loop(rng, "i", "0", "n", ["switch (coins[i]) {", "case '1':", "    credit += 1;", "    break;", "case '2':", "    credit += 5;", "    break;",
                                                                       "case '3':", "    credit += 10;", "    break;", "case '0':", "    credit = 0;", "    break;", "default:", "    break;", "}",
                                                                       "if (price > 0 && credit >= price) {", "    credit -= price;", "    sold++;", "}"]) + ["return sold * 100 + credit;"]
        return fname(rng, "vend", "vending_machine"), "int", ps, body, []
    if kind == "number_tokens":
        body = ["int state = 0, tokens = 0;"] + for_loop(rng, "i", "0", n, [f"char c = {s}[i];", "switch (state) {", "case 0:", "    if (c >= '0' && c <= '9') {", "        state = 1;", "        tokens++;", "    }", "    break;",
                                                                         "case 1:", "    if (c == '.')", "        state = 2;", "    else if (c < '0' || c > '9')", "        state = 0;", "    break;",
                                                                         "default:", "    if (c < '0' || c > '9')", "        state = 0;", "    break;", "}"]) + ["return tokens;"]
        return fname(rng, "count_numbers", "number_tokens"), "int", ps, body, []
    ps[0]["lo"], ps[0]["hi"] = 32, 50
    body = ["int in = 0, kept = 0;"] + for_loop(rng, "i", "0", n, [f"if (!in && {s}[i] == '(')", "    in = 1;", f"else if (in && {s}[i] == ')')", "    in = 0;", "else if (!in)", "    kept++;"]) + ["return kept;"]
    return fname(rng, "strip_comments_len", "outside_parens"), "int", ps, body, []


@template("calls", "multi_helper", 2.0)
def multi_helper(rng):
    """2-3 small named helpers + a caller that loops and branches over them."""
    pool = {
        "square": (["static long square(long v)", "{", "    return v * v;", "}"], 1, "square"),
        "absval": (["static int absval(int v)", "{", "    return v < 0 ? -v : v;", "}"], 1, "absval"),
        "clamp": (["static int clamp(int v, int lo, int hi)", "{", "    if (v < lo)", "        return lo;", "    if (v > hi)", "        return hi;", "    return v;", "}"], 3, "clamp"),
        "digits": (["static int digit_sum(int v)", "{", "    int s = 0;", "    if (v < 0)", "        v = -v;", "    while (v > 0) {", "        s += v % 10;", "        v /= 10;", "    }", "    return s;", "}"], 1, "digit_sum"),
        "sign": (["static int sign(int v)", "{", "    return (v > 0) - (v < 0);", "}"], 1, "sign"),
        "maxi": (["static int max_int(int a, int b)", "{", "    return a > b ? a : b;", "}"], 2, "max_int"),
        "mini": (["static int min_int(int a, int b)", "{", "    return a < b ? a : b;", "}"], 2, "min_int"),
        "iseven": (["static int is_even(int v)", "{", "    return v % 2 == 0;", "}"], 1, "is_even"),
    }
    keys = rng.sample(sorted(pool), rng.randint(2, 3))
    shape = rng.choice(["array", "range"])
    if shape == "array":
        a, n, et, ps, B = _arr(rng, True, et="int", rng_vals=rng.choice([(-100, 100), (-1000, 1000), (0, 99)]))
        elem = f"{a}[i]"
        loop_hdr = ("0", n)
    else:
        ps = [P("lo", "int", -100, 100), P("hi", "int", -100, 100)]
        elem = "i"
        loop_hdr = ("lo", "hi")
    stmts = []
    for kk in keys:
        txt, ar, nm = pool[kk]
        if ar == 1:
            call = f"{nm}({elem})"
        elif ar == 2:
            call = f"{nm}({elem}, {rng.randint(-20, 20)})"
        else:
            lo = rng.randint(-50, 0)
            call = f"{nm}({elem}, {lo}, {lo + rng.randint(1, 80)})"
        if nm == "is_even":
            stmts += [f"if ({call})", "    acc += 1;"]
        elif rng.random() < 0.4:
            stmts += [f"if ({call} > {rng.randint(0, 30)})", f"    acc += {call};", "else", f"    acc -= {rng.randint(1, 9)};"]
        else:
            stmts += [f"acc += {call};"]
    body = ["long acc = 0;"] + for_loop(rng, "i", loop_hdr[0], loop_hdr[1], stmts, cmp="<" if shape == "array" else "<=") + ["return acc;"]
    return fname(rng, "aggregate", "score_all", "evaluate_all", "process"), "long", ps, body, [pool[k][0] for k in keys]


@template("calls", "pipeline", 1.5)
def pipeline(rng):
    """caller runs a sequence of in-place array passes implemented as helpers."""
    a, n, et, ps, B = _arr(rng, False, et="int", rng_vals=(-100, 100))
    passes = {
        "negate_odd": (["static void negate_odd(int *a, int n)", "{"] + _ind(for_loop(rng, "i", "0", "n", [f"if (a[i] % {rng.randint(2, 5)} != 0)", "    a[i] = -a[i];"])) + ["}"]),
        "add_index": (["static void add_index(int *a, int n)", "{"] + _ind(for_loop(rng, "i", "0", "n", [rng.choice(["a[i] += i;", f"a[i] += i * {rng.randint(2, 5)};", f"a[i] -= i % {rng.randint(2, 7)};"])])) + ["}"]),
        "clip": (["static void clip(int *a, int n, int lim)", "{"] + _ind(for_loop(rng, "i", "0", "n", ["if (a[i] > lim)", "    a[i] = lim;", "else if (a[i] < -lim)", "    a[i] = -lim;"])) + ["}"]),
        "halve": (["static void halve(int *a, int n)", "{"] + _ind(for_loop(rng, "i", "0", "n", [f"a[i] /= {rng.randint(2, 9)};"])) + ["}"]),
        "prefix": (["static void prefix(int *a, int n)", "{"] + _ind(for_loop(rng, "i", "1", "n", ["a[i] += a[i - 1];"])) + ["}"]),
        "reverse": (["static void reverse(int *a, int n)", "{"] + _ind(block("for (int i = 0, j = n - 1; i < j; i++, j--)", ["int t = a[i];", "a[i] = a[j];", "a[j] = t;"])) + ["}"]),
    }
    keys = rng.sample(sorted(passes), rng.randint(2, 4))
    body = []
    for k in keys:
        body.append(f"clip({a}, {n}, {rng.randint(5, 90)});" if k == "clip" else f"{k}({a}, {n});")
    # bound: |a| <= 100 (+24 per add_index), prefix multiplies by <= 24: all tiny vs INT_MAX
    body += ["long chk = 0;"] + for_loop(rng, "i", "0", n, [f"chk = chk * 31 % 1000003 + {a}[i];"]) + ["return chk;"]
    return fname(rng, "run_passes", "pipeline", "transform_all"), "long", ps, body, [passes[k] for k in keys]


@template("calls", "mutual", 0.8)
def mutual(rng):
    kind = rng.choice(["evenodd", "hofstadter", "ackermann_small"])
    if kind == "evenodd":
        helpers = [["static int is_odd_r(int n);"], _helper_fn("static int is_even_r(int n)", ["if (n == 0)", "    return 1;", "return is_odd_r(n - 1);"]),
                   _helper_fn("static int is_odd_r(int n)", ["if (n == 0)", "    return 0;", "return is_even_r(n - 1);"])]
        body = ["if (n < 0)", "    n = -n;", "return is_even_r(n) * 2 + is_odd_r(n);"]
        return fname(rng, "parity_code", "even_odd"), "int", [P("n", "int", -500, 500)], body, helpers
    if kind == "hofstadter":
        helpers = [["static int male(int n);"], _helper_fn("static int female(int n)", ["return n == 0 ? 1 : n - male(female(n - 1));"]),
                   _helper_fn("static int male(int n)", ["return n == 0 ? 0 : n - female(male(n - 1));"])]
        return fname(rng, "hofstadter_fm", "female_male"), "int", [P("n", "int", 0, 25)], ["return female(n) * 100 + male(n);"], helpers
    helpers = [_helper_fn("static int ack(int m, int n)", ["if (m == 0)", "    return n + 1;", "if (n == 0)", "    return ack(m - 1, 1);", "return ack(m - 1, ack(m, n - 1));"])]
    return fname(rng, "ackermann", "ack_small"), "int", [P("m", "int", 0, 2), P("n", "int", 0, 6)], ["return ack(m, n);"], helpers


@template("arith", "fixed_point", 1.2)
def fixed_point(rng):
    kind = rng.choice(["lerp", "avg_round", "celsius", "percent", "scale_round", "dist2"])
    if kind == "lerp":
        ps = [P("a", "int", -10000, 10000), P("b", "int", -10000, 10000), P("t", "int", 0, 256)]
        body = ["long d = (long)b - a;", "return a + (d * t) / 256;"]
    elif kind == "avg_round":
        ps = [P("a", "int", -100000, 100000), P("b", "int", -100000, 100000), P("c", "int", -100000, 100000)]
        body = ["long s = (long)a + b + c;", "if (s >= 0)", "    return (s + 1) / 3;", "return (s - 1) / 3;"]
    elif kind == "celsius":
        ps = [P("f", "int", -500, 1000)]
        body = ["int c = (f - 32) * 5;", "if (c >= 0)", "    return (c + 4) / 9;", "return (c - 4) / 9;"]
    elif kind == "percent":
        ps = [P("part", "int", 0, 100000), P("whole", "int", 0, 100000)]
        body = ["if (whole == 0)", "    return 0;", "long p = (long)part * 1000 / whole;", "return (p + 5) / 10;"]
    elif kind == "scale_round":
        num, den = rng.randint(1, 50), rng.randint(2, 60)
        ps = [P("x", "int", -100000, 100000)]
        body = [f"long v = (long)x * {num};", f"long q = v / {den}, r = v % {den};", f"if (2 * (r < 0 ? -r : r) >= {den})", "    q += v < 0 ? -1 : 1;", "return q;"]
    else:
        ps = [P("x1", "int", -1000, 1000), P("y1", "int", -1000, 1000), P("x2", "int", -1000, 1000), P("y2", "int", -1000, 1000)]
        body = ["long dx = x2 - x1, dy = y2 - y1;", "long d2 = dx * dx + dy * dy;", "long r = 0;"] + block("while ((r + 1) * (r + 1) <= d2)", ["r++;"]) + ["return r;"]
    return fname(rng, kind, f"{kind}_fx"), "long", ps, body, []


def array_chars(rng):
    s = rng.choice(STR_NAMES)
    n = rng.choice(LEN_NAMES)
    ps = [P(s, "char", 32, 126, kind="array", const=True, len_=n), P(n, "int", 0, 24, kind="len")]
    kind = rng.choice(["vowels", "digits", "upper", "lower", "caesar", "hash", "palin", "words", "digitval", "replace"])
    x = f"{s}[i]"
    rt = "int"
    if kind == "vowels":
        vs = rng.choice(["aeiou", "aeiouAEIOU"])
        cond = " || ".join(f"c == '{v}'" for v in vs[:5]) if len(vs) == 5 else None
        body = ["int cnt = 0;"] + for_loop(rng, "i", "0", n, [f"char c = {x};"] + (
            [f"if ({cond})", "    cnt++;"] if cond else
            ["if (c >= 'A' && c <= 'Z')", "    c = c - 'A' + 'a';", "if (c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u')", "    cnt++;"])) + ["return cnt;"]
        name = ("count_vowels", "vowels")
    elif kind == "digits":
        body = ["int cnt = 0;"] + for_loop(rng, "i", "0", n, [f"if ({x} >= '0' && {x} <= '9')", "    cnt++;"]) + ["return cnt;"]
        name = ("count_digits", "digit_chars")
    elif kind in ("upper", "lower"):
        ps[0]["const"] = False
        lo, hi, d = ("'a'", "'z'", "-") if kind == "upper" else ("'A'", "'Z'", "+")
        body = for_loop(rng, "i", "0", n, [f"if ({x} >= {lo} && {x} <= {hi})", f"    {x} = {x} {d} ('a' - 'A');"])
        rt, name = "void", (f"to_{kind}", f"str_{kind}", f"make_{kind}")
    elif kind == "caesar":
        ps[0]["const"] = False
        ps.append(P("shift", "int", 0, 25))
        body = for_loop(rng, "i", "0", n, [f"if ({x} >= 'a' && {x} <= 'z')", f"    {x} = 'a' + ({x} - 'a' + shift) % 26;",
                                          f"else if ({x} >= 'A' && {x} <= 'Z')", f"    {x} = 'A' + ({x} - 'A' + shift) % 26;"])
        rt, name = "void", ("caesar", "rot_shift", "caesar_encode")
    elif kind == "hash":
        m = rng.choice(["31u", "33u", "131u", "16777619u"])
        init = rng.choice(["0u", "5381u", "2166136261u"])
        body = [f"unsigned int h = {init};"] + for_loop(rng, "i", "0", n, [rng.choice([f"h = h * {m} + (unsigned char){x};", f"h = (h ^ (unsigned char){x}) * {m};"])]) + ["return h;"]
        rt, name = "unsigned int", ("hash", "str_hash", "checksum")
    elif kind == "palin":
        ps[0]["lo"], ps[0]["hi"] = (97, 99)
        body = block(f"for (int i = 0, j = {n} - 1; i < j; i++, j--)", [f"if ({s}[i] != {s}[j])", "    return 0;"]) + ["return 1;"]
        name = ("is_palindrome", "palindrome")
    elif kind == "words":
        ps[0]["lo"], ps[0]["hi"] = (32, 34)
        body = ["int cnt = 0, in = 0;"] + for_loop(rng, "i", "0", n, [f"if ({x} == ' ')", "    in = 0;", "else if (!in) {", "    in = 1;", "    cnt++;", "}"]) + ["return cnt;"]
        name = ("count_words", "word_count")
    elif kind == "digitval":
        ps[0]["lo"], ps[0]["hi"] = (48, 57)
        ps[1]["hi"] = 9
        body = ["long v = 0;"] + for_loop(rng, "i", "0", n, [f"if ({x} < '0' || {x} > '9')", "    return -1;", f"v = v * 10 + ({x} - '0');"]) + ["return v;"]
        rt, name = "long", ("parse_uint", "atoi_n", "str_to_num")
    else:
        ps[0]["const"] = False
        ps += [P("from", "char", 97, 101), P("to", "char", 65, 90)]
        body = ["int c = 0;"] + for_loop(rng, "i", "0", n, [f"if ({x} == from) {{", f"    {x} = to;", "    c++;", "}"]) + ["return c;"]
        name = ("replace_char", "subst")
    return fname(rng, *name), rt, ps, body, []
