"""
oral-history-master · 共享配置契约
=================================
所有脚本从这里读取目录结构、标记约定、分块参数，避免硬编码漂移。

设计原则：脚本只做"确定性机械活"（清洗 / 分块 / 一致性校验 / 对照 / 打包）；
真正的"去口语化判断"由主 agent（Editor 角色）按 references/editor.md + examples
逐块完成。脚本绝不替 agent 做语义改写。
"""
from __future__ import annotations

import re
from pathlib import Path

# ── 项目目录结构（每位受访人 / 每次访谈一个 project）────────────────────────
PROJECT_LAYOUT = {
    "sources": "sources",          # 原始转写稿 + ingest 后的归一稿
    "work": "work",                # 中间产物
    "chunks": "work/chunks",       # 分块输入  chunk_001.md ...
    "edited": "work/edited",       # Editor 逐块输出 chunk_001.edited.md ...
    "output": "output",            # 拼接后的整理稿
    "review": "review",            # 交付给"受访人审阅签字"的三件套
}

# project 根下的关键文件
FILE_RAW = "sources/raw.txt"               # 原始转写（ingest 前）
FILE_INGESTED = "sources/ingested.md"      # 清洗 / 说话人分离后
FILE_EDIT_SPEC = "edit_spec.md"            # 整理方针（人读，Surveyor 产出）
FILE_TERM_LOCK = "term_lock.md"            # 执行契约（机读，Editor 每块重读）
FILE_MANIFEST = "work/manifest.json"       # 分块清单 + 进度锚 + 状态
FILE_CLEAN = "output/整理稿.md"             # 拼接成品
FILE_COMPARE = "review/对照稿.md"           # 原始 vs 整理稿 逐块对照
FILE_TODO = "review/待核对清单.md"          # 所有 ⚠ 汇总
FILE_CONSISTENCY = "review/一致性报告.md"   # consistency_checker 产出

# ── 分块参数 ────────────────────────────────────────────────────────────────
CHUNK_TARGET_CHARS = 2400      # 每块目标字数（中文）
CHUNK_MAX_CHARS = 3200         # 硬上限，超过强制切
CHUNK_OVERLAP_SENTS = 2        # 与上一块重叠的句数（给 Editor 上下文）

# 分块文件内的哨兵行（chunker 写、Editor 读、diff/fidelity 据此取"正文"）
CHUNK_OVERLAP_HEAD = "〔上文回顾 · 勿整理，仅供衔接参考〕"
CHUNK_BODY_HEAD = "〔以下为本块正文 · 请整理〕"

# 句子边界（中文）
SENT_ENDINGS = "。！？…"
# 优先切分点：说话人轮次 > 段落 > 句子
SPEAKER_PREFIX_RE = r"^\s*(?:【[^】]+】|（[^）]+）|[A-Za-z一-鿿]{1,6}[:：])"

# ── 标记约定（与 references/shared-standards.md 必须一致）────────────────────
MARK_NOTE_OPEN = "〔"          # 影响意义/可争议改动的行内说明
MARK_NOTE_CLOSE = "〕"
MARK_UNCERTAIN = "⚠"           # 待核对（人名/专名/同音疑似转写错）
MARK_QUESTION = "【问】"        # 采访人的实质提问
# 这些标记在 fidelity_checker / consistency_checker / diff_reporter 中被统计、剥离

# ── 整理方针开关（term_lock 的 switches 段，Editor 据此调尺度）────────────────
DEFAULT_SWITCHES = {
    "fidelity": "中",            # 高 / 中 / 低 仿真度
    "interviewer": "保留",       # 保留 / 脚注 / 删除
    "dialect": "保留",           # 保留 / 标准化+原文括注
    "completion": "最小补全",    # 最小补全 / 仅标注不补
}

SKILL_DIR = Path(__file__).resolve().parent.parent


def project_path(projects_root: Path, name: str) -> Path:
    return Path(projects_root) / name


def resolve(name: str, projects_root=None) -> Path:
    """脚本统一入口：name + 可选 projects-root → project 路径。"""
    root = Path(projects_root) if projects_root else (SKILL_DIR / "projects")
    return root / name


def ensure_layout(proj: Path) -> None:
    """创建 project 子目录树（幂等）。"""
    for sub in PROJECT_LAYOUT.values():
        (proj / sub).mkdir(parents=True, exist_ok=True)


def chunk_body(text: str) -> str:
    """从分块文件内容中取出"正文"段（哨兵之后），剥掉上文回顾。"""
    idx = text.find(CHUNK_BODY_HEAD)
    body = text[idx + len(CHUNK_BODY_HEAD):] if idx >= 0 else text
    # 去掉注释行与首尾空白
    lines = [ln for ln in body.splitlines() if not ln.strip().startswith("<!--")]
    return "\n".join(lines).strip()


def parse_term_lock(path: Path) -> list[dict]:
    """
    解析 term_lock.md 的术语对照表。
    识别形如 | 规范写法 | 变体/别名 | 类别 | 备注 | 的 markdown 表行。
    返回 [{canonical, variants:[...], kind, note}]，未填充则返回 []。
    """
    if not path.exists():
        return []
    rows: list[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not (s.startswith("|") and s.count("|") >= 4):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        canonical = cells[0]
        # 跳过表头与分隔行
        if not canonical or canonical in ("规范写法", "规范", "canonical") or set(canonical) <= set("-: "):
            continue
        variants = [v.strip() for v in re.split(r"[;；,，/]", cells[1]) if v.strip()] if len(cells) > 1 else []
        rows.append({
            "canonical": canonical,
            "variants": [v for v in variants if v and v not in ("-", "—", "无")],
            "kind": cells[2] if len(cells) > 2 else "",
            "note": cells[3] if len(cells) > 3 else "",
        })
    return rows
