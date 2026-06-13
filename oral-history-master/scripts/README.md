# scripts/ · 确定性流水线工具

> 设计哲学：**脚本只做确定性机械活，语义判断留给主 agent。**
> 「去口语化」这一核心判断由 Editor 角色（主 agent）按 `references/editor.md`
> + `references/examples.md` + `term_lock.md` 逐块完成；脚本绝不替 agent 改写文字。

所有脚本仅依赖 Python 3.9+ 标准库（`.docx/.xlsx` 导入需可选依赖，见 `requirements.txt`）。
统一调用约定：`python3 <script>.py <project_name> [--projects-root DIR]`。

| 脚本 | 作用 | 输入 → 输出 |
|---|---|---|
| `config.py` | 共享契约：目录结构 / 标记约定 / 分块参数 / term_lock 解析 | （被其它脚本 import） |
| `project_manager.py` | 建项目 / 导入转写稿 / 校验 / 进度 | `init` `import` `validate` `status` |
| `transcript_ingest.py` | 清洗 + 说话人分离 + 时间戳归一（不改字） | `sources/raw.*` → `sources/ingested.md` |
| `glossary_extractor.py` | 专名候选预扫（机构/项目/人名候选） | `ingested.md` → `work/glossary_candidates.json` |
| `chunker.py` | 分块（边界切分 + 重叠 + 进度锚） | `ingested.md` → `work/chunks/chunk_NNN.md` |
| `consistency_checker.py` | 跨块术语 / 标签 / 标记一致性校验 | `work/edited/*` + `term_lock.md` → `review/一致性报告.md` |
| `fidelity_checker.py` | 忠实度硬门：字数比抓添写/删过头 | `chunks/` vs `edited/` → `review/忠实度报告.md` |
| `diff_reporter.py` | 对照稿（原始 ⟷ 整理稿，真·可追溯） | `chunks/` + `edited/` → `review/对照稿.md` |
| `package_review.py` | 拼接整理稿 + 汇总 ⚠ 待核对清单 | `edited/` → `output/整理稿.md` + `review/待核对清单.md` |

## 典型一次完整跑（单篇）

```bash
cd oral-history-master/scripts
python3 project_manager.py init  laozhang_interview
python3 project_manager.py import laozhang_interview /path/to/转写稿.txt --move
python3 transcript_ingest.py     laozhang_interview
python3 glossary_extractor.py    laozhang_interview      # → Surveyor 据此填 term_lock
#  〔Surveyor 阶段：主 agent 读 ingested.md，确认整理方针 + 填 edit_spec/term_lock〕
python3 chunker.py               laozhang_interview
#  〔Editor 阶段：主 agent 逐块整理 chunk_NNN.md → work/edited/chunk_NNN.edited.md〕
python3 consistency_checker.py   laozhang_interview
python3 fidelity_checker.py      laozhang_interview      # error → 返工
python3 diff_reporter.py         laozhang_interview
python3 package_review.py        laozhang_interview
#  〔QA 阶段：oral-history-quality-guard 对照原文逐句审忠实度〕
```

20 万字续跑 / 换窗口：见 `workflows/resume-execute.md`。
