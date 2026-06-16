#!/usr/bin/env python3
"""
fidelity_checker.py · 忠实度硬校验（QA 门）
===========================================
交付前的 error/warning 门。口述史最高原则是"存真"，本脚本逐块对比
原始正文 vs 整理稿，给三类信号（机械启发式，最终语义忠实仍由 quality-guard
对照原文逐句确认；本脚本负责把"可疑块"挑出来送审）：

  ① 字数比（error 门）   偏长→疑似添写；偏短→疑似删过头
  ② 新增数字/专名（warn）原文没有的年份/数字/人名/机构 = 疑似捏造
  ③ 不确定表述删除（warn）大概/记不清在原文有、整理稿大幅丢失 = 伪造确定性风险

用法：python3 fidelity_checker.py <name> [--projects-root DIR]
退出码：有 error → 1
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import config as C

RATIO_HIGH = 1.08       # 超过 → error：疑似添油加醋
RATIO_WARN_HIGH = 1.00  # 1.00–1.08 → warn：略增，复核是否补过头
RATIO_LOW = 0.45        # 低于 → error：疑似过度删削

# 轻量专名抽取（仅多字机构 + 称谓锚定人名，避免单字噪音）
_PERSON_RE = re.compile(r"(?:老|小)([一-鿿]{1,2})|([一-鿿]{1,2})(?:所长|院长|主任|书记|院士|教授|先生|女士|同志|部长|司长|厂长)")
_INST_RE = re.compile(r"[一-鿿]{2,6}?(?:研究所|研究院|学部|委员会|大学|学院|课题组|实验室)")
_SEV = {"ok": 0, "warn": 1, "error": 2}


def _clean(text: str) -> str:
    text = re.sub(r"〔[^〕]*〕", "", text)
    text = text.replace(C.MARK_UNCERTAIN, "")
    return re.sub(r"【[^】]*】", "", text)


def _clean_len(text: str) -> int:
    return len(re.sub(r"\s", "", _clean(text)))


def _entities(text: str) -> set:
    ents = {m for m in _INST_RE.findall(_clean(text))}
    for a, b in _PERSON_RE.findall(text):
        if a or b:
            ents.add(a or b)
    return ents


def _num_is_new(n: str, orig: set) -> bool:
    # 容忍年份补全：62↔1962、59↔1959 不算新增
    return not any(n == m or n.endswith(m) or m.endswith(n) for m in orig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--projects-root")
    args = ap.parse_args()

    proj = C.resolve(args.name, args.projects_root)
    chunks_dir = proj / C.PROJECT_LAYOUT["chunks"]
    edited_dir = proj / C.PROJECT_LAYOUT["edited"]

    # term_lock 里的合法专名当作"已知名"允许清单
    known = set()
    for t in C.parse_term_lock(proj / C.FILE_TERM_LOCK):
        known.add(t["canonical"]); known.update(t["variants"])

    rows, errors, warns = [], 0, 0
    for cf in sorted(chunks_dir.glob("chunk_*.md")):
        cid = cf.stem
        orig = C.chunk_body(cf.read_text(encoding="utf-8"))
        ef = edited_dir / f"{cid}.edited.md"
        if not ef.exists():
            rows.append((cid, "·待整理", ["尚未整理"])); continue
        edited = ef.read_text(encoding="utf-8")

        o_len, e_len = _clean_len(orig), _clean_len(edited)
        ratio = e_len / o_len if o_len else 0
        level, reasons = "ok", []

        # ① 字数比
        if ratio > RATIO_HIGH:
            level = "error"; reasons.append(f"偏长 {ratio:.2f}× 疑似添写")
        elif ratio < RATIO_LOW:
            level = "error"; reasons.append(f"偏短 {ratio:.2f}× 疑似删过头")
        elif ratio > RATIO_WARN_HIGH:
            level = "warn"; reasons.append(f"略增 {ratio:.2f}× 复核补全")

        # ② 新增数字/专名
        o_nums, e_nums = C.extract_number_values(orig), C.extract_number_values(edited)
        new_nums = sorted(n for n in e_nums if _num_is_new(n, o_nums))
        if new_nums:
            level = "warn" if _SEV[level] < 1 else level
            reasons.append(f"新增数字/年份 {new_nums}（也可能是合理年份补全，人工确认）")
        o_ents = _entities(orig)
        new_ents = sorted(e for e in _entities(edited)
                          if e not in o_ents and e not in known and e not in orig)
        if new_ents:
            level = "warn" if _SEV[level] < 1 else level
            reasons.append(f"新增专名 {new_ents}（原文/术语表均无 → 疑似捏造，核对）")

        # ③ 不确定表述删除
        o_unc = sum(orig.count(m) for m in C.UNCERTAINTY_MARKERS)
        e_unc = sum(edited.count(m) for m in C.UNCERTAINTY_MARKERS)
        if o_unc >= 2 and e_unc <= o_unc * 0.5:
            level = "warn" if _SEV[level] < 1 else level
            reasons.append(f"不确定表述疑似删除（原文 {o_unc}→整理 {e_unc}，伪造确定性风险）")

        if level == "error":
            errors += 1
        elif level == "warn":
            warns += 1
        rows.append((cid, {"ok": f"✅ {ratio:.2f}×", "warn": f"⚠ {ratio:.2f}×",
                           "error": f"❌ {ratio:.2f}×"}[level], reasons or ["ok"]))

    out = ["# 忠实度校验报告", "",
           "| 块 | 判定 | 信号 |", "|---|---|---|"]
    for cid, verdict, reasons in rows:
        out.append(f"| {cid} | {verdict} | {'；'.join(reasons)} |")
    out += ["", f"**结果：{errors} error · {warns} warning**", "",
            "> error（字数比异常）必须返工。warning（新增数字/专名、不确定删除）逐条送 "
            "`oral-history-quality-guard` 对照原文确认——多为捏造/伪造确定性的早期信号。",
            "> 所有判定均为机械启发式，非最终结论。"]
    (proj / "review" / "忠实度报告.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    if errors:
        print(f"\n✗ {errors} 个块未过字数比硬门，必须返工后重跑。")
        return 1
    print(f"\n✅ 字数比门通过；{warns} 处 warning 待 quality-guard 语义审。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
