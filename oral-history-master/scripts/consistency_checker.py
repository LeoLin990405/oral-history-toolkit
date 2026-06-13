#!/usr/bin/env python3
"""
consistency_checker.py · 跨块一致性校验
========================================
结构性硬校验。

整篇整理完后，机械校验：
  1. 术语一致性：term_lock 里某规范写法的"变体"是否仍在整理稿里出现
     （= 该统一却没统一）；
  2. 说话人标签是否统一（【受访人】/【采访人】之外的杂标签）；
  3. 标记统计：⚠ 待核对数、〔说明〕数。

用法：python3 consistency_checker.py <name> [--projects-root DIR]
输入：<proj>/work/edited/*.edited.md + term_lock.md
输出：<proj>/review/一致性报告.md（+ 退出码：发现变体未统一→1）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import config as C


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--projects-root")
    args = ap.parse_args()

    proj = C.resolve(args.name, args.projects_root)
    edited_dir = proj / C.PROJECT_LAYOUT["edited"]
    files = sorted(edited_dir.glob("*.edited.md"))
    if not files:
        sys.exit(f"✗ 没有已整理的块（work/edited/*.edited.md）：{args.name}")

    terms = C.parse_term_lock(proj / C.FILE_TERM_LOCK)
    report = ["# 一致性报告", ""]
    problems = 0

    # 1) 术语变体未统一
    report.append("## 1. 术语一致性")
    if not terms:
        report.append("- ⚠ term_lock 未填充术语表，跳过术语校验（建议 Surveyor 补全）。")
    else:
        any_hit = False
        for t in terms:
            for v in t["variants"]:
                if not v or v in t["canonical"]:
                    # 变体是规范写法的子串（如「半导体所」⊂「中科院半导体所」）→ 无法靠子串区分，跳过
                    continue
                hits = []
                for f in files:
                    # 先抠掉规范写法本身，避免把 canonical 内部的子串误判为变体残留
                    masked = f.read_text(encoding="utf-8").replace(t["canonical"], "")
                    if v in masked:
                        hits.append(f"{f.stem}×{masked.count(v)}")
                if hits:
                    any_hit = True
                    problems += 1
                    report.append(f"- ❌「{t['canonical']}」的变体「{v}」仍出现在："
                                  f"{', '.join(hits)} → 应统一为「{t['canonical']}」")
        if not any_hit:
            report.append(f"- ✅ {len(terms)} 个规范术语，未发现变体残留。")

    # 2) 说话人标签
    report.append("\n## 2. 说话人标签")
    labels = set()
    for f in files:
        labels.update(re.findall(r"【([^】]+)】", f.read_text(encoding="utf-8")))
    odd = labels - {"受访人", "采访人", "问"}
    if odd:
        report.append(f"- ⚠ 出现非标准标签：{', '.join(sorted(odd))}（确认是否应归一）")
    else:
        report.append(f"- ✅ 标签规范：{', '.join(sorted(labels)) or '（无显式标签）'}")

    # 3) 标记统计
    report.append("\n## 3. 标记统计")
    total_warn = total_note = 0
    for f in files:
        txt = f.read_text(encoding="utf-8")
        w = txt.count(C.MARK_UNCERTAIN)
        n = len(re.findall(r"〔[^〕]*〕", txt))
        total_warn += w; total_note += n
    report.append(f"- ⚠ 待核对（{C.MARK_UNCERTAIN}）共 {total_warn} 处 → 见 待核对清单.md")
    report.append(f"- 〔说明〕共 {total_note} 处（意义级改动留痕）")

    out = proj / C.FILE_CONSISTENCY
    out.write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    print(f"\n→ 写入 {out}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
