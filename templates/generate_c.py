# generate c functions from templates
import hashlib
import random
import json
import sys

import templates as T

RESERVED = {"abs", "labs", "div", "select", "index", "random", "rand", "free", "exit", "printf",
            "malloc", "main", "time", "signal", "hash", "remove", "rename", "system"}


def _sample_seed(seed, k):
    h = hashlib.sha256(f"gen-2.0:{seed}:{k}".encode()).digest()
    return int.from_bytes(h[:8], "little")


def _render(name, ret, params, body, helpers, rng):
    allman = rng.random() < 0.6
    sig = ", ".join(
        (f"{'const ' if p['const'] else ''}{p['type']} *{p['name']}" if p["kind"] == "array"
         else f"{p['type']} {p['name']}") for p in params) or "void"
    head = f"{ret} {name}({sig})"
    lines = [head, "{"] if allman else [head + " {"]
    lines += ["    " + b for b in body if b.strip()] + ["}"]
    parts = ["\n".join(h) for h in helpers] + ["\n".join(lines)]
    return "\n\n".join(parts) + "\n"


def _pick(rng, families=None):
    reg = [r for r in T.REGISTRY if not families or r[0] in families]
    fam = rng.choice(sorted({r[0] for r in reg}))
    reg = [r for r in reg if r[0] == fam]
    tot = sum(w for *_, w in reg)
    x = rng.random() * tot
    for fam, tid, fn, w in reg:
        x -= w
        if x <= 0:
            return fam, tid, fn
    return reg[-1][:3]


def generate_one(seed, k, families=None):
    s = _sample_seed(seed, k)
    rng = random.Random(s)
    fam, tid, fn = _pick(rng, families)
    import re
    for _ in range(50):
        name, ret, params, body, helpers = fn(rng)
        text = "\n".join(body)
        # ensure every parameter is used
        if all(re.search(r"\b%s\b" % re.escape(p["name"]), text) for p in params):
            break
    hn = {h[0].split("(")[0].split()[-1] for h in helpers}
    if name in hn or name in {p["name"] for p in params} or name in RESERVED:
        name = name + "_main"
    c = _render(name, ret, params, body, helpers, rng)
    sig = {"name": name, "ret": ret, "static": False,
           "params": [dict(p) for p in params]}
    return {"id": f"gen-{seed}-{k:06d}", "source": "generated",
            "family": fam, "template": tid, "seed": s, "c": c, "sig": sig,
            "test_seed": s ^ 0x5EED}


def generate(n, seed=0, families=None):
    return [generate_one(seed, k, families) for k in range(n)]


def families():
    return sorted({f for f, *_ in T.REGISTRY})


def template_ids():
    return [t for _, t, *_ in T.REGISTRY]


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: python3 templates/generate_c.py N [seed]")
    count = int(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) == 3 else 0
    for index in range(count):
        example = generate_one(seed, index)
        print(json.dumps({"id": example["id"], "c": example["c"], "sig": example["sig"]}))
