#!/usr/bin/env python3
"""
diff_reporter.py · 原始 vs 整理稿 对照稿
========================================
生成"对照稿"：逐块把【原始正文】和【整理稿】并排呈现，让受访人 / Kelvin
一眼扫出改了什么。这是替代 Kelvin 原版"假统计改动数"的真·可追溯。

用法：python3 diff_reporter.py <name> [--projects-root DIR]
输出：<proj>/review/对照稿.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import config as C


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--projects-root")
    args = ap.parse_args()

    proj = C.resolve(args.name, args.projects_root)
    chunks_dir = proj / C.PROJECT_LAYOUT["chunks"]
    edited_dir = proj / C.PROJECT_LAYOUT["edited"]
    chunk_files = sorted(chunks_dir.glob("chunk_*.md"))
    if not chunk_files:
        sys.exit(f"✗ 没有分块：{args.name}")

    out = ["# 对照稿（原始转写 ⟷ 整理稿）", "",
           "> 左为原始转写正文，右为去口语化整理稿。`〔说明〕` 标意义级改动，"
           "`⚠` 标待核对。受访人审阅时对照此稿即可。", ""]
    for cf in chunk_files:
        cid = cf.stem
        orig = C.chunk_body(cf.read_text(encoding="utf-8"))
        ef = edited_dir / f"{cid}.edited.md"
        edited = ef.read_text(encoding="utf-8").strip() if ef.exists() else "（未整理）"
        out += [f"## {cid}", "",
                "**【原始转写】**", "", "> " + orig.replace("\n", "\n> "), "",
                "**【整理稿】**", "", edited, "", "---", ""]

    dst = proj / C.FILE_COMPARE
    dst.write_text("\n".join(out), encoding="utf-8")
    print(f"✅ 对照稿 → {dst}（{len(chunk_files)} 块）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
