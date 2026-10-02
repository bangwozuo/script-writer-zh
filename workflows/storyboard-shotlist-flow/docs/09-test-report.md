# 测试报告 —— storyboard-shotlist-flow

## 一、结构校验

| 项 | 结果 |
|---|---|
| 四件套齐全（SKILL.md / prompt.txt / schema.json / examples/input.json） | ✅ PASS |
| SKILL.md 九段齐全 + frontmatter + ID 行（`de_media_02_wf03`） | ✅ PASS |
| prompt.txt ≥ 1200 字（T3 标准，实测约 1600 字） | ✅ PASS |
| Mermaid DAG 节点 = 本仓真实技能 slug（script-structure-generate） | ✅ PASS |
| scripts/run_flow.py 存在且 --demo 退出码 0 | ✅ PASS |
| examples 无占位符（原「请提供工作流的初始输入数据」占位已清除） | ✅ PASS |
| 无 API Key / 无模型调用代码 | ✅ PASS |

## 二、脚本实跑记录

| 命令 | 退出码 | 产物 |
|---|---|---|
| `python scripts/run_flow.py --demo` | 0 | out/分镜拍摄清单.xlsx、out/分镜时长分布.png、out/storyboard_flow.json |
| `python scripts/run_flow.py --input examples/input.json --outdir out` | 0 | 同上 |
| 73s 错误时长版（对照实验，docs/04 示例 2） | 0（判打回重改） | 同上 |

## 三、校验正确性验证（examples/input.json 实跑数值）

| 检查项 | 期望 | 实跑 | 结果 |
|---|---|---|---|
| 汉字计数 | 标点不计 | 镜头 1 = 12 字、镜头 2 = 25 字 | ✅ |
| 语速区间 | 3.5-6.0 字/秒 | 全片 4.0-5.5 ✅ | ✅ |
| 时间轴连续 | 逐镜无重叠 | 0-3/3-9/9-12/…/54-60 | ✅ |
| 时长合计 | 60s ±2s | 60s = 0s 偏差 | ✅ |
| 景别合法 | 四选一 | 近景/中景/特写/全景 | ✅ |
| 字幕长度 | ≤15 字符 | 最长 14（60% 单量 → 20% 收入） | ✅ |
| 音效清单去重 | 全片去重 | 5 项（pop/whoosh/消息提示音/金句音效/键盘声） | ✅ |
| 平台上限 | 抖音 ≤60s | 60s = 上限 ✅ | ✅ |
| 判定逻辑 | 全过 → 通过 | 通过 | ✅ |
| 边界：shots 空 | 中止索要 | SystemExit 退出码非 0 | ✅ |

## 四、检出能力验证（对照实验）

| 场景 | 期望 | 实跑 |
|---|---|---|
| 时长虚标 73s（目标 60s） | 时长差 + 语速过稀连环检出 | 10 项问题（8 镜过稀 + 合计超差 + 平台超限）✅ |
| 超字数镜头（3s 配 20 字） | 🔴 给删字数 | 6.67 字/秒 >6，给「删约 2 字」等三条路 ✅ |
| 台词留空 | 🟡 B-roll 确认闸（不报错不放过） | docs/04 示例 4 ✅ |
| 景别非法 | 🔴 补字段 | 「景别「航拍」非法（特写/近景/中景/全景）」 ✅ |

## 五、结论

**通过。** 七字段校验（语速双向死线/时间轴/景别/画面/字幕/B-roll）全部量化，
demo 通过案例与 73s 对照实验共同证明检出与放行双向可靠，拍摄清单自动汇总可用。

---

*测试基于真实实跑（退出码 0），数值取自 out/storyboard_flow.json · 2026-09-30*
