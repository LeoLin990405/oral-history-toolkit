#!/usr/bin/env python3
"""
transcript_ingest.py · 转写稿清洗 / 说话人分离 / 格式归一
========================================================
把杂乱的录音转写稿整理成规范的
ingested.md，供 Surveyor 通读、chunker 分块。

只做"确定性预处理"，不做任何去口语化（那是 Editor 的活）：
  · 全角/半角、空白、换行归一
  · 识别并规范化说话人轮次：统一成 【受访人】/【采访人】 块
  · 时间戳归一成行首 〔时间 hh:mm:ss〕 锚点（供日后对录音）
  · 不删一个字、不改一个词

用法：python3 transcript_ingest.py <name> [--projects-root DIR]
输入：<proj>/sources/raw.{txt,md,docx,xlsx}
输出：<proj>/sources/ingested.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import config as C

TS_RE = re.compile(r"[\[\(（]?\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*[\]\)）]?")
# 说话人标签：受访人/采访人/问/答/被采访者/访谈者/Speaker N/姓名+：
SPEAKER_RE = re.compile(
    r"^\s*(?P<sp>"
    r"受访(?:人|者)|采访(?:人|者)|访谈(?:人|者)|被采访者|主持人|记者|"
    r"问|答|Q|A|Speaker\s*\d+|[A-Za-z]{1,12}|[一-鿿]{1,5}(?:先生|女士|老师|院士|所长|教授)?"
    r")\s*[:：]\s*"
)

CANON = {
    "受访人": "受访人", "受访者": "受访人", "被采访者": "受访人", "答": "受访人", "A": "受访人",
    "采访人": "采访人", "采访者": "采访人", "访谈人": "采访人", "访谈者": "采访人",
    "主持人": "采访人", "记者": "采访人", "问": "采访人", "Q": "采访人",
}


def _read_raw(proj: Path) -> str:
    src_dir = proj / "sources"
    for ext in (".txt", ".md"):
        f = src_dir / f"raw{ext}"
        if f.exists():
            return f.read_text(encoding="utf-8", errors="replace")
    docx = src_dir / "raw.docx"
    if docx.exists():
        try:
            from docx import Document  # python-docx, 可选
        except ImportError:
            sys.exit("✗ 需要 python-docx 读取 .docx：pip install python-docx")
        return "\n".join(p.text for p in Document(str(docx)).paragraphs)
    xlsx = src_dir / "raw.xlsx"
    if xlsx.exists():
        try:
            import openpyxl  # 可选
        except ImportError:
            sys.exit("✗ 需要 openpyxl 读取 .xlsx：pip install openpyxl")
        wb = openpyxl.load_workbook(str(xlsx), read_only=True)
        rows = []
        for ws in wb.worksheets:
            for r in ws.iter_rows(values_only=True):
                rows.append(" ".join(str(c) for c in r if c is not None))
        return "\n".join(rows)
    sys.exit(f"✗ 找不到 sources/raw.*，先 import：{proj.name}")


def _normalize(text: str) -> str:
    # 统一换行、压缩多余空白、全角空格→半角
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("　", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _segment(text: str) -> list[str]:
    """按说话人轮次切块；无标签则按段落保留。"""
    out: list[str] = []
    cur_sp: str | None = None
    buf: list[str] = []

    def flush():
        if buf:
            body = " ".join(s.strip() for s in buf if s.strip())
            if body:
                prefix = f"【{CANON.get(cur_sp, cur_sp)}】" if cur_sp else ""
                out.append(f"{prefix}{body}")
        buf.clear()

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 抽时间戳到行首锚点
        ts = TS_RE.match(line)
        ts_tag = ""
        if ts and (ts.end() < len(line) * 0.4):  # 仅当时间戳在行首
            ts_tag = f"〔时间 {ts.group(1)}〕"
            line = line[ts.end():].strip()
        m = SPEAKER_RE.match(line)
        if m:
            flush()
            cur_sp = m.group("sp").strip()
            rest = line[m.end():].strip()
            if ts_tag:
                rest = f"{ts_tag}{rest}"
            if rest:
                buf.append(rest)
        else:
            buf.append((ts_tag + line) if ts_tag else line)
    flush()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--projects-root")
    args = ap.parse_args()

    proj = C.resolve(args.name, args.projects_root)
    if not proj.exists():
        sys.exit(f"✗ 项目不存在：{args.name}")

    raw = _read_raw(proj)
    blocks = _segment(_normalize(raw))
    has_speakers = any(b.startswith("【") for b in blocks)

    md = ["# 归一稿（ingested）",
          "",
          f"> 原始字数约 {len(raw)} 字；切出 {len(blocks)} 个语段。"
          f"{'识别到说话人轮次。' if has_speakers else '未识别到说话人标签，按段落保留。'}",
          "> ⚠ 本文件只做格式归一，未做任何去口语化。",
          ""]
    md.extend(f"{b}\n" for b in blocks)

    out = proj / C.FILE_INGESTED
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"✅ 归一完成：{out}")
    print(f"   语段数 {len(blocks)}，说话人分离：{'是' if has_speakers else '否（无标签）'}")
    print(f"   下一步：python3 glossary_extractor.py {args.name}  → 再 chunker.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
