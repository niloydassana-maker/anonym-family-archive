import io
p = r"D:\anonym\delivery\kilo-bridge-setup\scripts\prove_lane.py"
lines = open(p, encoding="utf-8").read().split("\n")
# line 115 (1-indexed) lost its indent and broke main() in half
i = 114
if lines[i].startswith("live_n ="):
    lines[i] = "    " + lines[i]
    print("re-indented line 115")
open(p, "w", encoding="utf-8").write("\n".join(lines))
import ast
try:
    ast.parse(open(p, encoding="utf-8").read())
    print("SYNTAX OK")
except SyntaxError as e:
    print("SYNTAX ERROR:", e.lineno, e.msg)
