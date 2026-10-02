# 测试报告 —— voiceover-colloquial-flow

## 一、结构校验

| 项 | 结果 |
|---|---|
| 四件套齐全（SKILL.md / prompt.txt / schema.json / examples/input.json） | ✅ PASS |
| SKILL.md 九段齐全 + frontmatter + ID 行（`de_media_02_wf02`） | ✅ PASS |
| prompt.txt ≥ 1200 字（T3 标准，实测约 1600 字） | ✅ PASS |
| Mermaid DAG 节点 = 本仓真实技能 slug（persona-voice-library / colloquial-rewrite） | ✅ PASS |
| scripts/run_flow.py 存在且 --demo 退出码 0 | ✅ PASS |
| examples 无占位符（原「请提供工作流的初始输入数据」占位已清除） | ✅ PASS |
| 无 API Key / 无模型调用代码 | ✅ PASS |

## 二、脚本实跑记录

| 命令 | 退出码 | 产物 |
|---|---|---|
| `python scripts/run_flow.py --demo` | 0 | out/口语化校验表.xlsx、out/句长分布.png、out/colloquial_flow.json |
| `python scripts/run_flow.py --input examples/input.json --outdir out` | 0 | 同上 |

## 三、校验正确性验证（examples/input.json 实跑数值）

| 检查项 | 期望 | 实跑 | 结果 |
|---|---|---|---|
| 衔接词计数 | 20 词表扫描 | 0 处 ✅ | ✅ |
| 平均句长 | 15 句 181 字 → 12.1 | 12.1 字 ✅ | ✅ |
| 句长 CV | 长短句交错样本 | 0.52 ✅ | ✅ |
| 语气词密度 | 4 个/181 字 → 2.2/百字 | 2.2 ✅ | ✅ |
| 第二人称 | 你×2 + 咱×1 → 16.6/千字 | 16.6 ✅ | ✅ |
| 均长连句检测 | 无 3 连 >18 字 | 0 组 ✅ | ✅ |
| 总字数死线 | 60s = 240-300 字 | 181 字 🔴 缺 59 字 | ✅ |
| 判定逻辑 | 有 🔴 → 打回重改 | 打回重改 | ✅ |
| 边界：<50 字 | 中止索要 | SystemExit 退出码非 0 | ✅ |

## 四、边界行为验证

| 场景 | 预期 | 实际（按 prompt 指令推演） |
|---|---|---|
| 无历史样本 | 降级通用标准 + 标注 | docs/04 示例 2 ✅ |
| AI 腔初稿 | 🔴 打回 + 按级别排序问题清单 | docs/04 示例 3 ✅ |
| 800 字改 60s | 骤降 >30% 触发取舍清单 | docs/04 示例 4 ✅ |
| 合规豁免 | 不豁免，过 sensitive-word-precheck | prompt 编排禁止项第 6 条 ✅ |

## 五、结论

**通过。** DAG 引用真实 slug、六指标 + 总字数七项校验全部量化、demo 实跑证明
「指标全过也会因字数死线打回」的严格性、产物三类齐全。

---

*测试基于真实实跑（退出码 0），数值取自 out/colloquial_flow.json · 2026-09-30*
