# 工作流：resume-execute（20 万字续跑 / 换窗口）

> 长访谈（10 万字级）一次对话跑不完，或上下文变长后
> 整理质量下降时，用本工作流**分阶段、换窗口**续跑，每段都从 term_lock 重新锚定，
> 保证全篇一致。

## 何时用
- Surveyor 在 Step 2 估算规模"重"（长块数 / 大字数），建议跑完 Phase A 就停。
- 或整理到中途，担心上下文压缩导致漂移——换个干净窗口继续。

## 两阶段切分

**Phase A（窗口 1）**：Step 1 归一 + Step 2 方针师 + Step 3 分块。
完成后产物落盘：`edit_spec.md`、`term_lock.md`、`work/chunks/`、`work/manifest.json`。
输出交接卡后**停止本对话**：
```
## ✅ Phase A 完成
- [x] term_lock.md 已锁定
- [x] 已分 N 块 → work/chunks/
- [ ] 下一步：开新窗口，输入 `继续整理 projects/<name>` 进入 Phase B
```

**Phase B（窗口 2+）**：新窗口输入 `继续整理 projects/<name>`：
1. `read_file <proj>/term_lock.md` + `read_file <proj>/edit_spec.md` 恢复方针。
2. `python3 scripts/project_manager.py status <name>` 看进度（已整理 / 待整理）。
3. 读 `references/editor.md` + `references/examples.md`。
4. 从第一个 `status=pending` 的块继续，**每块重读 term_lock**，逐块整理 → `work/edited/`。
5. 全部整理完 → Step 5 一致性/忠实度门 → Step 6 复核包 → Step 7 QA 门。

## 分段续跑（超长，Phase B 也要分多窗口）
- 每个 Phase B 窗口整理一段（如 15–20 块），整理完更新 manifest，输出"已到 chunk_NNN，
  下一窗口 `继续整理 projects/<name>`"。
- **每个新窗口都重读 term_lock** —— 这是跨窗口一致性的保证，不可省。
- 全部块 `status=edited` 后，再统一跑 Step 5–7。

## 关键纪律
- 续跑不重置 term_lock：术语表、语气画像、开关全程唯一，谁都不许中途改尺度。
- 若续跑中发现新专名 → 先标 ⚠，集中回填 term_lock 后**重跑 consistency_checker**，不要边跑边改表。
