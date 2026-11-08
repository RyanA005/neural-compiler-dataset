# v1 neural compiler dataset

c function and x86-64 assembly pairs. 9,752 pairs generated with gcc -O0.

## use

```sh
python3 generate.py data/dataset.jsonl generated.jsonl
python3 test.py generated.jsonl
```

`generate.py` compiles each saved c function, strips assembly metadata and writes the pairs to the output file. with no arguments it updates `data/dataset.jsonl`, using a temporary file first.
`test.py` builds a c driver from each example's saved inputs. it checks c and assembly against the same saved expected output, including changed arrays, and prints a pass count. compile/run failures or mismatches make it exit nonzero. compile timeout: 30 seconds; run timeout: 3 seconds. arrays use separate heap allocations, matching the saved tests.

## templates

```sh
python3 templates/generate_c.py 100 0 > out.jsonl
```

`templates/templates.py` defines 51 templates and basic shared helpers. 
`templates/exprs.py` generates random bounded expressions.
`templates/generate_c.py` generates a full example

generator does not compile, filter, deduplicate or make tests.

## methodology

7,159 generated functions from 51 templates. templates are small c function patterns covering arithmetic, conditionals, loops, helper calls, arrays and strings. filling them with different constants, operators and control flow produces different functions.

2,593 functions from [exebench](https://huggingface.co/datasets/jordiae/exebench)

only integer/character types and pointer/length array parameters. functions needing custom types, globals, io, floating point or unsupported libraries were thrown out.

inputs combine fixed edge cases and seeded random values within each function's saved ranges. gathered ranges were tried from wider to narrower. the exact ranges, inputs, expected returns and changed arrays are stored in `sig` and `tests`. 151,610 cases total, 5-17 per function.

## compilation

linux x86-64, ubuntu~24.04.1

```text
-O0 -std=gnu11 -S -masm=intel
-fno-asynchronous-unwind-tables -fno-pic -fno-stack-protector
-fcf-protection=none -fno-ident
```

blank lines, `.file`, `.ident` and note sections are stripped. tests link with `-no-pie -Wa,--noexecstack`.

## license

the scripts, templates and generated functions are mit.

the exebench rows come from [exebench](https://huggingface.co/datasets/jordiae/exebench). its i/o examples and boilerplate are mit, but the c functions keep the original license of their github repo, recorded in exebench's metadata.

citation: armengol-estapé et al., exebench, maps 2022. https://doi.org/10.1145/3520312.3534867
