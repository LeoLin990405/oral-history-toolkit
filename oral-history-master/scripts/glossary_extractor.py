#!/usr/bin/env python3
"""
glossary_extractor.py · 专名候选预扫 + 变体聚类
================================================
脚本做机械预处理，agent 做判断。

正则预扫 ingested.md，把"全篇需要统一写法"的专名候选捞出来：机构 / 项目 / 人名候选；
并把**疑似同一实体的不同写法聚成一组**（如 半导体所 ⊂ 中科院半导体所），
直接产出可粘贴进 term_lock 的术语表草稿，平滑 Surveyor 回填。

⚠ 仅"候选+聚类草稿"，非定稿。规范写法、同音错字归一由 Surveyor 结合上下文核定。

用法：python3 glossary_extractor.py <name> [--projects-root DIR] [--top N]
输出：work/glossary_candidates.json + work/term_table_draft.md（可粘贴）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import config as C

INST_RE = re.compile(r"[一-鿿]{2,6}?(?:研究所|研究院|学部|委员会|大学|学院|中心|课题组|实验室|所|院|室|部|厂|局|司)")
PROJ_RE = re.compile(r"(?:\d{2,3}\s*(?:计划|工程|项目)|[一-鿿]{2,6}?(?:工程|计划|攻关|项目|专项))")
PERSON_RE = re.compile(
    r"(?:老|小)([一-鿿]{1,2})"
    r"|([一-鿿]{1,2})(?:所长|院长|主任|书记|院士|教授|先生|女士|同志|老师|部长|司长|厂长)"
)

LEADING_JUNK = re.compile(r"^(?:那个|这个|那|这|我们|你们|您|我|他|她|就是|还是|是|到|的|个|有|在|和|跟)+")
STOP_CHARS = set("我你您他她们这那哪是了到就都也还和跟把被让给啊吗呢吧嗯哦呃问答年评像连")


def _clean_candidate(term: str):
    term = LEADING_JUNK.sub("", term).strip()
    if len(term) < 2 or (set(term) & STOP_CHARS):
        return None
    return term


def _cluster(cands: list[dict]) -> list[list[str]]:
    """把疑似同一实体的写法聚到一组：子串包含，或同类+同前两字。"""
    by = {c["term"]: c for c in cands}
    terms = list(by)
    used, clusters = set(), []
    for i, a in enumerate(terms):
        if a in used:
            continue
        group = [a]; used.add(a)
        for b in terms[i + 1:]:
            if b in used:
                continue
            same_kind = by[a]["kind"] == by[b]["kind"]
            if (a in b or b in a) or (same_kind and len(a) >= 3 and len(b) >= 3 and a[:2] == b[:2]):
                group.append(b); used.add(b)
        clusters.append(group)
    return clusters


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--projects-root")
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()

    proj = C.resolve(args.name, args.projects_root)
    ing = proj / C.FILE_INGESTED
    if not ing.exists():
        sys.exit(f"✗ 没有 ingested.md，先跑 transcript_ingest.py：{args.name}")
    text = re.sub(r"〔[^〕]*〕|【[^】]*】", "", ing.read_text(encoding="utf-8"))

    inst = Counter(filter(None, (_clean_candidate(m) for m in INST_RE.findall(text))))
    proj_terms = Counter(filter(None, (_clean_candidate(m) for m in PROJ_RE.findall(text))))
    persons: Counter = Counter()
    for a, b in PERSON_RE.findall(text):
        if a or b:
            persons[a or b] += 1

    def rows(counter, kind, min_count=1):
        return [{"term": t, "count": n, "kind": kind, "canonical": "", "variants": []}
                for t, n in counter.most_common(args.top) if n >= min_count]

    candidates = rows(inst, "机构") + rows(proj_terms, "项目") + rows(persons, "人名候选", 2)
    by = {c["term"]: c for c in candidates}

    out = proj / "work" / "glossary_candidates.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    # 聚类 → 可粘贴 term_lock 表块
    clusters = _cluster(candidates)
    draft = ["# term_lock 术语表草稿（自动聚类，⚠ 人工核定后粘贴进 term_lock.md）", "",
             "| 规范写法 | 变体/别名（分号隔） | 类别 | 备注 |", "|---|---|---|---|"]
    multi = 0
    for g in clusters:
        canonical = max(g, key=len)
        variants = [x for x in g if x != canonical]
        if variants:
            multi += 1
        kind = by[canonical]["kind"]
        note = "⚠ 待核定：疑似同一实体多种写法" if variants else "⚠ 待核定"
        draft.append(f"| {canonical} | {'；'.join(variants)} | {kind} | {note} |")
    draft_path = proj / "work" / "term_table_draft.md"
    draft_path.write_text("\n".join(draft) + "\n", encoding="utf-8")

    print(f"## 专名候选 {len(candidates)} 条 → {out}")
    print(f"## 聚类 {len(clusters)} 组（其中 {multi} 组疑似同一实体多写法）→ 可粘贴草稿 {draft_path}")
    if multi:
        print("\n⚠ 疑似不一致写法（同一实体被写成多种）——优先在 term_lock 统一：")
        for g in clusters:
            if len(g) > 1:
                print(f"   · {'  /  '.join(g)}")
    print("\n⚠ 机械预扫+聚类，可能有噪音/漏网/误并。Surveyor 必须人工核定后写入 term_lock.md（人名尤其不可靠）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
