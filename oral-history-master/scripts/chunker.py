#!/usr/bin/env python3
"""
chunker.py · 分块（带重叠 + 进度锚）
====================================
把 ingested.md 切成 ≤ CHUNK_MAX_CHARS 的块，优先在说话人轮次 / 段落 /
句子边界切，绝不切句中。每块带"上文回顾"重叠，给 Editor 衔接上下文。

为什么要分块：20 万字塞不进一个上下文。分块 + term_lock 全局锚定，
是"长文整理稿一致性"的工程保证（见 SKILL.md）。

用法：python3 chunker.py <name> [--target N] [--max N] [--projects-root DIR]
输入：<proj>/sources/ingested.md
输出：<proj>/work/chunks/chunk_NNN.md + 更新 manifest.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import config as C

SENT_SPLIT = re.compile(rf"(?<=[{C.SENT_ENDINGS}])")


def split_sentences(text: str) -> list[str]:
    return [s for s in SENT_SPLIT.split(text) if s.strip()]


def paragraphs(md: str) -> list[str]:
    out = []
    for block in re.split(r"\n\s*\n", md):
        block = block.strip()
        if not block or block.startswith("#") or block.startswith(">"):
            continue
        out.append(block)
    return out


def chunk_units(units: list[str], target: int, hard_max: int) -> list[list[str]]:
    chunks: list[list[str]] = []
    cur: list[str] = []
    cur_len = 0
    for u in units:
        # 单段超过 hard_max → 句子级再切
        if len(u) > hard_max:
            if cur:
                chunks.append(cur); cur, cur_len = [], 0
            sent_buf, sent_len = [], 0
            for s in split_sentences(u):
                if sent_len + len(s) > hard_max and sent_buf:
                    chunks.append([" ".join(sent_buf)]); sent_buf, sent_len = [], 0
                sent_buf.append(s); sent_len += len(s)
            if sent_buf:
                chunks.append([" ".join(sent_buf)])
            continue
        if cur_len + len(u) > target and cur:
            chunks.append(cur); cur, cur_len = [], 0
        cur.append(u); cur_len += len(u)
    if cur:
        chunks.append(cur)
    return chunks


def overlap_tail(prev_chunk_text: str, n_sents: int) -> str:
    sents = split_sentences(prev_chunk_text)
    return "".join(sents[-n_sents:]).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--target", type=int, default=C.CHUNK_TARGET_CHARS)
    ap.add_argument("--max", type=int, default=C.CHUNK_MAX_CHARS)
    ap.add_argument("--projects-root")
    args = ap.parse_args()

    proj = C.resolve(args.name, args.projects_root)
    ing = proj / C.FILE_INGESTED
    if not ing.exists():
        sys.exit(f"✗ 没有 ingested.md，先跑 transcript_ingest.py：{args.name}")

    units = paragraphs(ing.read_text(encoding="utf-8"))
    groups = chunk_units(units, args.target, args.max)

    chunks_dir = proj / C.PROJECT_LAYOUT["chunks"]
    chunks_dir.mkdir(parents=True, exist_ok=True)
    for old in chunks_dir.glob("chunk_*.md"):
        old.unlink()

    manifest_chunks = []
    prev_body = ""
    for i, g in enumerate(groups, 1):
        cid = f"chunk_{i:03d}"
        body = "\n\n".join(g)
        parts = [f"<!-- {cid} | 约 {len(body)} 字 | 第 {i}/{len(groups)} 块 -->", ""]
        if prev_body:
            parts += [C.CHUNK_OVERLAP_HEAD, overlap_tail(prev_body, C.CHUNK_OVERLAP_SENTS), ""]
        parts += [C.CHUNK_BODY_HEAD, "", body, ""]
        (chunks_dir / f"{cid}.md").write_text("\n".join(parts), encoding="utf-8")
        manifest_chunks.append({"id": cid, "file": f"{C.PROJECT_LAYOUT['chunks']}/{cid}.md",
                                "chars": len(body), "status": "pending"})
        prev_body = body

    mf = proj / C.FILE_MANIFEST
    data = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {"project": args.name}
    data["chunks"] = manifest_chunks
    mf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ 分块完成：{len(groups)} 块 → {chunks_dir}")
    print(f"   平均 {sum(c['chars'] for c in manifest_chunks)//max(len(groups),1)} 字/块")
    print(f"   下一步：Editor 逐块整理 chunk_NNN.md → work/edited/chunk_NNN.edited.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
