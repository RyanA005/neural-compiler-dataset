# make random expressions and track arithmetic bounds

INT_LIM = 2**31 - 1
PREC = {"*": 5, "/": 5, "%": 5, "+": 4, "-": 4, "<<": 3.5, ">>": 3.5,
        "&": 3, "^": 2, "|": 1}


class E:
    __slots__ = ("s", "b", "p", "k")

    def __init__(self, s, b, p=9, k=None):
        self.s, self.b, self.p = s, b, p   # text, |value| bound, precedence
        # k: mentions a variable (False => constant-only subexpression)
        self.k = (not s.lstrip("-(").replace(")", "").isdigit()) if k is None else k

    def wrap(self, p, right=False):
        if self.p < p or (right and self.p == p) or (p != self.p and self.p in (1, 2, 3) and p in (1, 2, 3)):
            return f"({self.s})"
        return self.s


def binop(op, l, r):
    p = PREC[op]
    return f"{l.wrap(p)} {op} {r.wrap(p, right=op not in '+*&|^')}", p


def _is_const(e):
    return not e.k


class ExprGen:
    def __init__(self, rng, vars_, lim=INT_LIM, ops="+-*/%", const_max=20, bitwise=False):
        self.rng = rng
        self.vars = vars_          # list of (name, bound)
        self.lim = lim
        self.ops = list(ops) + (["&", "|", "^"] if bitwise else [])
        self.const_max = const_max

    def const(self, lo=1):
        r = self.rng
        c = r.choice([r.randint(lo, 9), r.randint(lo, self.const_max), r.choice([2, 3, 4, 5, 7, 10])])
        return E(str(c), c, 9, False)

    def leaf(self):
        if self.vars and self.rng.random() < 0.75:
            n, b = self.rng.choice(self.vars)
            return E(n, b, 9, True)
        return self.const(1)

    def gen(self, depth):
        r = self.rng
        if depth <= 0 or r.random() < 0.25:
            e = self.leaf()
            if r.random() < 0.04 and e.s[0] != "-" and e.k:
                e = E(f"-{e.wrap(9)}", e.b, 8, True)
            return e
        op = r.choice(self.ops)
        l = self.gen(depth - 1)
        if op in "/%":
            if _is_const(l) and self.vars:
                n, b = self.rng.choice(self.vars)
                l = E(n, b, 9, True)
            if r.random() < 0.6:
                d = self.const(2)
                s, p = binop(op, l, d)
                return E(s, l.b if op == "/" else min(l.b, d.b - 1), p, True)
            d = self.gen(depth - 1)
            import re as _re
            def _shares(a, b):
                ta = set(_re.findall(r"[A-Za-z_]\w*(?:\[\w+\])?", a))
                return bool(ta & set(_re.findall(r"[A-Za-z_]\w*(?:\[\w+\])?", b)))
            for _ in range(6):
                if not _shares(d.s, l.s) and not _is_const(d):
                    break
                d = self.gen(depth - 1)
            if _shares(d.s, l.s) or _is_const(d):
                d = self.const(2)
                s, p = binop(op, l, d)
                return E(s, l.b if op == "/" else min(l.b, d.b - 1), p, True)
            if d.p == 9 and d.s.lstrip("-").isdigit():
                if d.s.lstrip("-") == "0":
                    d = E("1", 1)
                s, p = binop(op, l, d)
                return E(s, l.b, p)
            s, _ = binop(op, l, d)
            return E(f"{d.wrap(7)} != 0 ? {s} : {l.wrap(1)}", l.b, 0.5, True)
        rr = self.gen(depth - 1)
        for _ in range(4):
            if not ((_is_const(l) and _is_const(rr)) or (rr.s == l.s and op in "-^&|")):
                break
            rr = self.leaf() if self.vars else self.const()
        if rr.s == l.s and op in "-^&|":
            rr = self.const()
        if op in "+-":
            b = l.b + rr.b
        elif op == "*":
            b = l.b * rr.b
        else:
            b = 2 ** (max(l.b, rr.b).bit_length() + 1)
        if b > self.lim:
            # fall back to something that stays in range
            if l.b + rr.b <= self.lim:
                op, b = r.choice("+-"), l.b + rr.b
            else:
                return l if l.b <= self.lim else self.leaf()
        if op == "*" and (rr.s in ("1", "0") or l.s in ("1", "0")):
            op, b = "+", l.b + rr.b
        s, p = binop(op, l, rr)
        return E(s, b, p, l.k or rr.k)

    def gen_using(self, depth, names, tries=20):
        # expression that mentions one of 'names'
        import re
        e = None
        for _ in range(tries):
            e = self.gen(depth)
            if any(re.search(r"(?<![\w\[])" + re.escape(n) + r"(?![\w])", e.s) for n in names):
                return e
        n, b = next(v for v in self.vars if v[0] in names)
        return E(n, b)

    def cond(self):
        # boolean expression
        r = self.rng
        def atom():
            a = self.gen(1)
            k = r.random()
            if k < 0.6:
                b = self.leaf() if r.random() < 0.6 else self.const(0)
                if b.s == a.s:
                    b = self.const(0)
                return f"{a.wrap(4)} {r.choice(['<', '<=', '>', '>=', '==', '!='])} {b.wrap(4)}"
            if k < 0.85:
                m = r.randint(2, 5)
                return f"{a.wrap(5)} % {m} {r.choice(['==', '!='])} 0"
            return f"{a.wrap(4)} > {r.randint(-10, 30)}"
        c = atom()
        if r.random() < 0.3:
            c = f"{c} {r.choice(['&&', '||'])} {atom()}"
        return c


def uexpr(rng, names, depth):
    # unsigned expression in defined ranges
    if depth <= 0 or rng.random() < 0.25:
        if rng.random() < 0.8:
            return rng.choice(names)
        return rng.choice(["0xffu", "0x0f0fu", "1u", "3u", "7u", "0x55555555u", "31u", "1000003u"])
    k = rng.random()
    a = uexpr(rng, names, depth - 1)
    if k < 0.2:
        return f"({a} {rng.choice(['<<', '>>'])} {rng.randint(1, 15)})"
    if k < 0.27:
        return f"~{a}" if a.startswith("(") or a.isidentifier() else f"~({a})"
    b = uexpr(rng, names, depth - 1)
    for _ in range(4):
        if b != a:
            break
        b = uexpr(rng, names, depth - 1)
    if b == a or (not b.isidentifier() and not a.isidentifier() and "u" in a and "u" in b and a[-1] == "u" and b[-1] == "u"):
        b = rng.choice(names) if b != a and names else b
    if b == a:
        b = rng.choice(["0x9e3779b9u", "0xffu", "13u"])
    return f"({a} {rng.choice(['+', '-', '*', '^', '&', '|', '^', '+'])} {b})"
