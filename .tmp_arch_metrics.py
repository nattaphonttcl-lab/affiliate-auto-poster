import ast
from pathlib import Path

ROOT = Path("app")

py_files = [p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts]

funcs = []
classes = []
module_lines = []
imports = {}
modules = {}

for p in py_files:
    rel = p.as_posix()
    mod = rel[:-3].replace("/", ".")
    modules[mod] = rel

for p in py_files:
    rel = p.as_posix()
    src = p.read_text(encoding="utf-8")
    lines = src.count("\n") + 1
    module_lines.append((lines, rel))
    t = ast.parse(src)

    mod = rel[:-3].replace("/", ".")
    imports[mod] = set()

    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.end_lineno:
            funcs.append((n.end_lineno - n.lineno + 1, rel, n.name, n.lineno))
        elif isinstance(n, ast.ClassDef) and n.end_lineno:
            classes.append((n.end_lineno - n.lineno + 1, rel, n.name, n.lineno))

        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.startswith("app."):
                imports[mod].add(n.module)
        elif isinstance(n, ast.Import):
            for alias in n.names:
                if alias.name.startswith("app."):
                    imports[mod].add(alias.name)

adj = {m: set() for m in modules}
for src_mod, deps in imports.items():
    for d in deps:
        parts = d.split(".")
        while parts:
            cand = ".".join(parts)
            if cand in modules:
                adj[src_mod].add(cand)
                break
            parts = parts[:-1]

color = {}
stack = []
cycles = []

def dfs(u):
    color[u] = 1
    stack.append(u)
    for v in adj.get(u, set()):
        if v == u:
            continue
        c = color.get(v, 0)
        if c == 0:
            dfs(v)
        elif c == 1 and v in stack:
            i = stack.index(v)
            cyc = stack[i:] + [v]
            cycles.append(cyc)
    stack.pop()
    color[u] = 2

for m in sorted(adj):
    if color.get(m, 0) == 0:
        dfs(m)

# dedupe cycle text
cycle_text = []
seen = set()
for cyc in cycles:
    t = " -> ".join(cyc)
    if t not in seen:
        seen.add(t)
        cycle_text.append(t)

print("TOP_MODULES")
for ln, rel in sorted(module_lines, reverse=True)[:20]:
    print(f"{ln:4} {rel}")

print("TOP_FUNCTIONS")
for ln, rel, name, start in sorted(funcs, reverse=True)[:30]:
    print(f"{ln:4} {rel}:{start} {name}")

print("TOP_CLASSES")
for ln, rel, name, start in sorted(classes, reverse=True)[:20]:
    print(f"{ln:4} {rel}:{start} {name}")

print("CYCLES")
if cycle_text:
    for t in cycle_text[:30]:
        print(t)
else:
    print("none")
