# check assembly and c against saved tests 

import json
from pathlib import Path
import subprocess
import sys
import tempfile


def literal(value):
    # ensures correct handling of longs
    return str(value) + ("ULL" if value >= 0 else "LL")


def print_value(ctype, value):
    # ensures correct sign
    if "unsigned" in ctype:
        return f'printf("%llu", (unsigned long long){value});'
    return f'printf("%lld", (long long){value});'


def driver(example):
    # generates main() to run inputs and print results
    signature = example["sig"]
    lines = ["#include <stdio.h>", "#include <stdlib.h>", example["signature"] + ";", "int main(void) {"]
    for number, inputs in enumerate(example["tests"]["inputs"]):
        lines.append("{")
        arguments = []
        for param in signature["params"]:
            name = "arg_" + param["name"]
            value = inputs[param["name"]]
            if param["kind"] == "array":
                # match any original heap layout for tests that compare pointers
                lines.append(f'{param["type"]} *{name} = malloc({len(value)} * sizeof({param["type"]}));')
                for index, item in enumerate(value):
                    lines.append(f'{name}[{index}] = ({param["type"]}){literal(item)};')
            else:
                lines.append(f'{param["type"]} {name} = ({param["type"]}){literal(value)};')
            arguments.append(name)
        call = signature["name"] + "(" + ", ".join(arguments) + ")"
        lines.append(f'printf("t{number}");')
        if signature["ret"] == "void":
            lines.append(call + ";")
        else:
            lines.append('printf(" ret=");')
            lines.append(print_value(signature["ret"], call))
        # results may be array contents
        for param in signature["params"]:
            if param["kind"] == "array" and not param["const"]:
                lines.append(f'printf(" {param["name"]}=[");')
                length = len(inputs[param["name"]])
                lines.append(f'for (int j = 0; j < {length}; j++) {{')
                lines.append('if (j) printf(",");')
                lines.append(print_value(param["type"], "arg_" + param["name"] + "[j]"))
                lines.append('} printf("]");')
            if param["kind"] == "array":
                lines.append(f'free(arg_{param["name"]});')
        lines.append('printf("\\n"); }')
    return "\n".join(lines) + "\nreturn 0; }\n"


def run(command, path, timeout=30):
    # proper error handling
    return subprocess.run(command, cwd=path, capture_output=True, text=True,
                          check=True, timeout=timeout).stdout


def test(example):
    """run c and assembly separately with the same test driver."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)
        (path / "example.c").write_text(example["c"])
        (path / "example.s").write_text(example["asm"])
        (path / "driver.c").write_text(driver(example))
        # iso c avoids gnu header names colliding with 'select'
        run(["gcc", "-std=c11", "-O0", "-c", "driver.c", "-o", "driver.o"], path)
        expected = "\n".join(example["tests"]["expected"]) + "\n"
        for source in ["example.c", "example.s"]:
            run(["gcc", "-std=gnu11", "-O0", "-no-pie", "-Wa,--noexecstack",
                 source, "driver.o", "-o", "check"], path)
            if run(["./check"], path, timeout=3) != expected:
                raise ValueError(source + " output differs from saved tests")


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "data/dataset.jsonl"
    passed = total = 0
    with open(source) as inputs:
        for line in inputs:
            example = json.loads(line)
            total += 1
            try:
                test(example)
                passed += 1
            except (subprocess.SubprocessError, ValueError) as error:
                print("FAIL", example["id"], getattr(error, "stderr", None) or error, flush=True)
            if total % 100 == 0:
                print(f"{passed}/{total} passed", flush=True)
    print(f"{passed}/{total} passed", flush=True)
    sys.exit(passed != total)
