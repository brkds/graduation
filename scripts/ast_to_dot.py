#!/usr/bin/env python3
import argparse, itertools, subprocess, tempfile, os
from clang.cindex import Index

def escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\"", "\\\"")

def node_label(node, tu_main_path: str | None = None) -> str:
    name = node.spelling or node.displayname or ""
    # Special-case the translation unit to only show the filename (no absolute path)
    if node.kind.name == "TRANSLATION_UNIT":
        main_path = node.spelling or tu_main_path or ""
        filename_only = os.path.basename(main_path) if main_path else ""
        return f"{node.kind.name}{(': ' + filename_only) if filename_only else ''}"
    return f"{node.kind.name}{(': ' + name) if name else ''}"

def node_style(node) -> str:
    kind_name = node.kind.name
    # Category by suffix heuristic
    if kind_name.endswith("_DECL"):
        return "shape=box, style=filled, fillcolor=lightblue"
    if kind_name.endswith("_STMT"):
        return "shape=box, style=filled, fillcolor=lightgoldenrodyellow"
    if kind_name.endswith("_EXPR"):
        return "shape=box, style=filled, fillcolor=lightgreen"
    if kind_name.endswith("_LITERAL"):
        return "shape=ellipse, style=filled, fillcolor=lightcoral"
    if kind_name.endswith("_REF"):
        return "shape=ellipse, style=filled, fillcolor=khaki1"
    if kind_name == "TRANSLATION_UNIT":
        return "shape=oval, style=filled, fillcolor=lightgray"
    # Fallback
    return "shape=box, style=filled, fillcolor=white"

def walk(node, id_iter, nodes, edges, tu_main_path: str | None = None):
    my_id = next(id_iter)
    nodes.append((my_id, node_label(node, tu_main_path), node_style(node)))
    for child in node.get_children():
        child_id = walk(child, id_iter, nodes, edges, tu_main_path)
        edges.append((my_id, child_id))
    return my_id

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--out", default="/home/zwy/project2721707-302151/ast.svg")
    ap.add_argument("--std", default="c11")
    ap.add_argument("--clang-arg", action="append", default=[])
    args = ap.parse_args()

    index = Index.create()
    tu = index.parse(args.file, args=["-std="+args.std] + args.clang_arg)

    id_iter = itertools.count(1)
    nodes, edges = [], []
    walk(tu.cursor, id_iter, nodes, edges, tu_main_path=tu.spelling)

    graph_label = os.path.basename(tu.spelling) if tu.spelling else "AST"
    dot = [
        "digraph AST {",
        "  node [fontname=\"monospace\"];\n  rankdir=TB;\n  labelloc=t;\n  label=\"" + escape(graph_label) + "\";\n"
    ]
    for i, label, style in nodes:
        dot.append(f"  n{i} [label=\"{escape(label)}\", {style}];\n")
    for a, b in edges:
        dot.append(f"  n{a} -> n{b};\n")
    dot.append("}")

    dot_str = "".join(dot)
    if args.out.endswith(".dot"):
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(dot_str)
    else:
        with tempfile.NamedTemporaryFile("w", suffix=".dot", delete=False) as f:
            f.write(dot_str)
            tmp = f.name
        subprocess.check_call(["dot", "-T"+args.out.split(".")[-1], tmp, "-o", args.out])
        os.unlink(tmp)

if __name__ == "__main__":
    main()
