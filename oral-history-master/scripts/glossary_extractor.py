#!/usr/bin/env python3
"""
glossary_extractor.py · 专名候选预扫
====================================
脚本做机械预处理，agent 做判断。

正则预扫 ingested.md，把"全篇需要统一写法"的专名候选捞出来：
  · 机构：…所/院/室/部/学部/大学/学院/委员会/中心/研究院
  · 项目：863 计划 / N 工程 / 攻关项目
  · 人名候选：称谓锚定（老X / X 所长 / X 院士 / X 先生 …）
  · 高频疑似专名（重复出现的 2–4 字非常用词）

⚠ 这只是"候选清单"，不是定稿。真正的规范写法、同音错字归一由 Surveyor
（主 agent）结合上下文判断后写进 term_lock.md。脚本绝不擅自认定。

用法：python3 glossary_extractor.py <name> [--projects-root DIR]
输出：<proj>/work/glossary_candidates.json（+ 打印 markdown 表）
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

# 候选清洗：剥离指示代词/人称等前缀噪音；含功能字的整段判为坏 span 丢弃
LEADING_JUNK = re.compile(r"^(?:那个|这个|那|这|我们|你们|您|我|他|她|就是|还是|是|到|的|个|有|在|和|跟)+")
STOP_CHARS = set("我你您他她们这那哪是了到就都也还和跟把被让给啊吗呢吧嗯哦呃问答年评像连")


def _clean_candidate(term: str) -> str | None:
    term = LEADING_JUNK.sub("", term).strip()
    if len(term) < 2 or (set(term) & STOP_CHARS):
        return None
    return term
PERSON_RE = re.compile(
    r"(?:老|小)([一-鿿]{1,2})"
    r"|([一-鿿]{1,2})(?:所长|院长|主任|书记|院士|教授|先生|女士|同志|老师|部长|司长|厂长)"
)


def _strip_markup(text: str) -> str:
    text = re.sub(r"〔[^〕]*〕", "", text)
    text = re.sub(r"【[^】]*】", "", text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--projects-root")
    ap.add_argument("--top", type=int, default=40, help="高频候选保留数")
    args = ap.parse_args()

    proj = C.resolve(args.name, args.projects_root)
    ing = proj / C.FILE_INGESTED
    if not ing.exists():
        sys.exit(f"✗ 没有 ingested.md，先跑 transcript_ingest.py：{args.name}")
    text = _strip_markup(ing.read_text(encoding="utf-8"))

    inst = Counter(filter(None, (_clean_candidate(m) for m in INST_RE.findall(text))))
    proj_terms = Counter(filter(None, (_clean_candidate(m) for m in PROJ_RE.findall(text))))
    persons: Counter = Counter()
    for a, b in PERSON_RE.findall(text):
        name = a or b
        if name:
            persons[name] += 1

    def rows(counter, kind, min_count=1):
        return [{"term": t, "count": n, "kind": kind, "canonical": "", "variants": []}
                for t, n in counter.most_common(args.top) if n >= min_count]

    candidates = (rows(inst, "机构", 1)
                  + rows(proj_terms, "项目", 1)
                  + rows(persons, "人名候选", 2))

    out = proj / "work" / "glossary_candidates.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    # 打印 markdown，方便 Surveyor 直接读
    print(f"## 专名候选（{len(candidates)} 条）→ {out}")
    print("\n| 类别 | 候选 | 出现次数 | 备注（Surveyor 填规范写法/变体） |")
    print("|---|---|---|---|")
    for c in candidates:
        print(f"| {c['kind']} | {c['term']} | {c['count']} | |")
    print("\n⚠ 以上为机械预扫，可能有噪音/漏网。Surveyor 必须人工核定后写入 term_lock.md。")
    print("   人名尤其不可靠（中文无称谓时难识别），务必结合上下文。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
