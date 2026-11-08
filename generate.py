# compile c and strip assembly metadata

import json
from pathlib import Path
import subprocess
import sys
import tempfile

FLAGS = "-O0 -std=gnu11 -S -masm=intel -fno-asynchronous-unwind-tables -fno-pic -fno-stack-protector -fcf-protection=none -fno-ident".split()
VERSION = subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0]


def generate(example):
    # compile one example and save cleaned assembly
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)
        (path / "example.c").write_text(example["c"])
        subprocess.run(["gcc", *FLAGS, "example.c", "-o", "example.s"],
                       cwd=path, capture_output=True, check=True, timeout=30)
        lines = []
        in_note = False
        for line in (path / "example.s").read_text().splitlines():
            text = line.strip()
            if not text or text.startswith((".file", ".ident")):
                continue
            # skip note section
            if text.startswith((".section", ".text", ".data", ".bss")):
                in_note = text.startswith(".section") and ".note." in text
            if in_note:
                continue
            lines.append(line.rstrip())
        example["asm"] = "\n".join(lines) + "\n"
        example["compiler"] = {"cc": "gcc", "version": VERSION, "profile": "O0", "flags": FLAGS}
    return example


if __name__ == "__main__":
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "data/dataset.jsonl")
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else source
    # replace the output after every example completes
    pending = output.with_suffix(".tmp")
    with source.open() as inputs, pending.open("w") as results:
        for count, line in enumerate(inputs, 1):
            results.write(json.dumps(generate(json.loads(line))) + "\n")
            if count % 1000 == 0:
                print(f"generated {count}", flush=True)
    pending.replace(output)
    print(f"generated {count} -> {output}")
