#!/usr/bin/env python3
"""
fidelity_checker.py · 忠实度硬校验（QA 门）
===========================================
交付前的 error/warning 门。
口述史最高原则是"存真"，所以这里专抓两类危险：
  · 添油加醋（整理稿显著长于原文 → 疑似捏造/过度改写）
  · 过度删削（整理稿显著短于原文 → 疑似删了实质内容）

逐块对比 原始正文 vs 整理稿 字数比，给出 error / warning / ok。
注意：字数比是启发式信号，不是判决；真正的语义忠实由 quality-guard
（agent 对照原文逐句审）确认。本脚本负责把"可疑块"挑出来送审。

用法：python3 fidelity_checker.py <name> [--projects-root DIR]
退出码：有 error → 1
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import config as C

# 整理后字数 / 原文字数 的合理区间。去口语化通常净减字，
# 但补全语法 + 〔说明〕会加字，故上限给到 1.08。
RATIO_HIGH = 1.08   # 超过 → error：疑似添油加醋
RATIO_WARN_HIGH = 1.00  # 1.00–1.08 → warning：略增，复核是否补过头
RATIO_LOW = 0.45    # 低于 → error：疑似过度删削


def _clean_len(text: str) -> int:
    """计有效字数：剥掉 〔说明〕、⚠、标签后的纯正文长度。"""
    text = re.sub(r"〔[^〕]*〕", "", text)
    text = text.replace(C.MARK_UNCERTAIN, "")
    text = re.sub(r"【[^】]*】", "", text)
    return len(re.sub(r"\s", "", text))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--projects-root")
    args = ap.parse_args()

    proj = C.resolve(args.name, args.projects_root)
    chunks_dir = proj / C.PROJECT_LAYOUT["chunks"]
    edited_dir = proj / C.PROJECT_LAYOUT["edited"]

    rows, errors, warns = [], 0, 0
    for cf in sorted(chunks_dir.glob("chunk_*.md")):
        cid = cf.stem
        ef = edited_dir / f"{cid}.edited.md"
        orig_len = _clean_len(C.chunk_body(cf.read_text(encoding="utf-8")))
        if not ef.exists():
            rows.append((cid, orig_len, "-", "·待整理", "pending")); continue
        ed_len = _clean_len(ef.read_text(encoding="utf-8"))
        ratio = ed_len / orig_len if orig_len else 0
        if ratio > RATIO_HIGH:
            verdict, level = f"❌ 偏长 {ratio:.2f}× 疑似添写", "error"; errors += 1
        elif ratio < RATIO_LOW:
            verdict, level = f"❌ 偏短 {ratio:.2f}× 疑似删过头", "error"; errors += 1
        elif ratio > RATIO_WARN_HIGH:
            verdict, level = f"⚠ 略增 {ratio:.2f}× 复核补全", "warn"; warns += 1
        else:
            verdict, level = f"✅ {ratio:.2f}×", "ok"
        rows.append((cid, orig_len, ed_len, verdict, level))

    out = ["# 忠实度校验报告", "",
           "| 块 | 原文字数 | 整理后 | 判定 |", "|---|---|---|---|"]
    for cid, o, e, v, _ in rows:
        out.append(f"| {cid} | {o} | {e} | {v} |")
    out += ["", f"**结果：{errors} error · {warns} warning**",
            "",
            "> error 必须返工：偏长 → 删掉添写的内容；偏短 → 找回被删的实质内容。",
            "> 字数比仅为信号，最终忠实度由 oral-history-quality-guard 对照原文逐句确认。"]
    (proj / "review" / "忠实度报告.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    if errors:
        print(f"\n✗ {errors} 个块未过忠实度门，必须返工后重跑。")
        return 1
    print("\n✅ 忠实度门通过（仍需 quality-guard 语义审）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
