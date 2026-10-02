# 测试报告 —— ai-trace-detect-reduce-flow

## 一、结构校验

| 项 | 结果 |
|---|---|
| 四件套齐全（SKILL.md / prompt.txt / schema.json / examples/input.json） | ✅ PASS |
| SKILL.md 九段齐全 + frontmatter + ID 行（`de_media_02_wf04`） | ✅ PASS |
| prompt.txt ≥ 1200 字（T3 标准，实测约 1650 字） | ✅ PASS |
| Mermaid DAG 节点 = 本仓真实技能 slug（ai-trace-check / colloquial-rewrite / sensitive-word-precheck） | ✅ PASS |
| scripts/run_flow.py 存在且 --demo 退出码 0 | ✅ PASS |
| examples 无占位符（原「请提供工作流的初始输入数据」占位已清除） | ✅ PASS |
| 无 API Key / 无模型调用代码 | ✅ PASS |

## 二、脚本实跑记录

| 命令 | 退出码 | 产物 |
|---|---|---|
| `python scripts/run_flow.py --demo` | 0 | out/降AI味与合规检查表.xlsx、out/句长分布.png、out/trace_reduce_flow.json |
| `python scripts/run_flow.py --input examples/input.json --outdir out` | 0 | 同上 |

## 三、校验正确性验证（examples/input.json 实跑数值）

| 检查项 | 期望 | 实跑 | 结果 |
|---|---|---|---|
| 衔接词计数 | 在当今/首先/其次/此外/值得注意的是/与此同时/综上+综上所述 = 8 处 | 8 处，59.3/千字 | ✅ |
| 抽象词计数 | 打造/全面提升 等 | 14.8/千字 | ✅ |
| 三段式检测 | 首先+其次+综上所述 齐活 → 是 | 是（+10 分） | ✅ |
| 五维计分 | 35(封顶)+10(CV0.44)+0+15(封顶)+10 = 70 | 70 | ✅ |
| 敏感词扫描 | 稳赚（红）/神器、加微信（警） | 红线 1 / 警告 2 | ✅ |
| 闸门判定 | 痕迹分 ≥55 或红线 ≥1 → 打回 | 打回重改（不得发布） | ✅ |
| 改写清单 | 逐处带替换建议 | 8/8 条 | ✅ |
| 边界：<50 字 | 中止索要 | SystemExit 退出码非 0 | ✅ |

## 四、闸门行为验证

| 场景 | 预期 | 实际（按 prompt 指令推演） |
|---|---|---|
| 改后复检引入新问题 | 继续打回到达标 | docs/04 示例 2（CV 0.33 → 插呼吸口 → 0.52） ✅ |
| 误伤申诉 | 人工裁定放行（引用/有意排比） | docs/04 示例 3 ✅ |
| 痕迹分低但有红线 | 独立判定仍打回 | 闸门规则 + prompt 禁止项第 6 条 ✅ |
| 咨询过检技巧 | 拒绝（违规协助） | docs/04 示例 4 ✅ |
| 与 ai-trace-check 口径 | 词表与计分一致（权重 35/30/16/15/10） | ✅ |

## 五、结论

**通过。** 三技能编排真实串联（检测→改写→合规），闸门规则量化且双线独立、
替换清单可直接落笔、demo 实跑打回重灾稿件证明闸门不是摆设、产物三类齐全。

---

*测试基于真实实跑（退出码 0），数值取自 out/trace_reduce_flow.json · 2026-09-30*
