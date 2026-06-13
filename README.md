# 口述史整理工具箱 · Oral History Toolkit

> 把录音转写稿，按口述史方法论，转换成**忠实、可读、可供受访人审阅签字**的整理稿。
> 专为长篇访谈（10 万字级）设计，**数据全程在本地，不外传**。

两个配套的 Claude Code / Agent Skill：

| Skill | 作用 |
|---|---|
| **`oral-history-master`** | 主流程：转写稿 → 整理稿（Pass 1 去口语化），多角色串行流水线 + 确定性脚本 |
| **`oral-history-quality-guard`** | 配套质量门：交付前对整理稿做**对抗式忠实度审计** |

## 设计立场

**存真 > 可读。** 录音才是史料，整理稿是对录音的"最小干预转写"。本工具：

- ✅ 去口语噪音（嗯/啊/重复/采访人插话）、纠显性口误与转写错、补最小语法、统一专名
- ✅ **完整保留**受访人的声音、叙事逻辑、主观判断、方言行话、前后矛盾、不确定表述
- ❌ 绝不添加受访人没说的信息、不伪造确定性、不替受访人圆场矛盾、不抹个性

方法论蒸馏自 11 部口述史文献（熊卫民、张藜、王扬宗、Ritchie、Portelli 等），
详见 [`oral-history-master/references/methodology.md`](oral-history-master/references/methodology.md)。

## 核心机制（为什么对长文也稳）

1. **范例驱动**：执行尺度向 [`references/examples.md`](oral-history-master/references/examples.md) 的金标准范例看齐，而非逐条套规则（规则清单会让 LLM 在长文里漂移）。
2. **term_lock 每块重读**：人名/机构/专名/语气/开关锁进机读契约，整理每块前重读，抗长文上下文压缩漂移。
3. **分块 + 全局术语锚定**：20 万字分块处理，跨块一致性由脚本校验。
4. **双硬门 + QA**：`consistency_checker`（术语一致）+ `fidelity_checker`（防添写/删过头）+ `quality-guard`（对照原文逐句审）。
5. **真·可追溯**：产出"原始 ⟷ 整理稿"对照稿，而非编造"改了 N 处"的假统计。

## 快速上手

核心流水线仅需 **Python 3.9+ 标准库**，开箱即跑（`.docx/.xlsx` 转写稿需 `pip install -r requirements.txt`）。

```bash
cd oral-history-master/scripts
python3 project_manager.py init  我的访谈
python3 project_manager.py import 我的访谈 /path/to/转写稿.txt --move
python3 transcript_ingest.py     我的访谈        # 清洗 + 说话人分离
python3 glossary_extractor.py    我的访谈        # 专名候选预扫
#  → 方针师（Surveyor）：通读，确认整理方针，填 edit_spec.md + term_lock.md
python3 chunker.py               我的访谈        # 分块
#  → 整理者（Editor）：逐块去口语化 → work/edited/chunk_NNN.edited.md
python3 consistency_checker.py   我的访谈
python3 fidelity_checker.py      我的访谈        # error 必须返工
python3 diff_reporter.py         我的访谈        # 对照稿
python3 package_review.py        我的访谈        # 整理稿 + 待核对清单
#  → 质量门（quality-guard）：对照原文逐句审忠实度
```

完整角色与门控流程见 [`oral-history-master/SKILL.md`](oral-history-master/SKILL.md)；脚本文档见
[`oral-history-master/scripts/README.md`](oral-history-master/scripts/README.md)。

## 看看效果

`oral-history-master/projects/demo/` 是一份跑通的合成样例（虚构内容）。对比：

- 输入 [`sources/raw.txt`](oral-history-master/projects/demo/sources/raw.txt)（带填充词/口误/方言/矛盾的口语转写）
- 输出 [`output/整理稿.md`](oral-history-master/projects/demo/output/整理稿.md)（去口语化整理稿）
- 复核 [`review/对照稿.md`](oral-history-master/projects/demo/review/对照稿.md) · [`待核对清单.md`](oral-history-master/projects/demo/review/待核对清单.md)

## 两道工序

- **Pass 1 · 去口语化**（本工具主流程）→ 整理稿，供受访人审阅签字
- **Pass 2 · 书面化**（[`workflows/pass2-bookify.md`](oral-history-master/workflows/pass2-bookify.md)）→ 发表级编辑，**须在签字后的整理稿上另起流程**

## 安装为 Skill

把 `oral-history-master/` 与 `oral-history-quality-guard/` 两个目录放入你的 skills 目录
（如 `~/.claude/skills/`）即可。触发词："口述史整理"、"转写稿去口语化"、"整理访谈记录"等。

## 伦理

整理稿须经受访人审阅签字方可使用；`⚠` 标记处须对录音/原始材料核查；无录音对照的转写稿，交付时提示核查。本工具在本地运行，**不外传任何数据**。
