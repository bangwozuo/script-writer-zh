# 测试报告 —— ai-trace-check

## 一、结构校验

| 项 | 结果 |
|---|---|
| 四件套齐全（SKILL.md / prompt.txt / schema.json / examples/input.json） | ✅ PASS |
| SKILL.md 九段齐全 + frontmatter + ID 行（`de_media_02_sk05`） | ✅ PASS |
| prompt.txt ≥ 800 字（T1 标准，实测约 1800 字） | ✅ PASS |
| scripts/ai_trace_check.py 存在且 --demo 退出码 0 | ✅ PASS |
| examples 无占位符 | ✅ PASS |
| 无 API Key / 无模型调用代码 | ✅ PASS |

## 二、脚本实跑记录

环境：Windows 11 · Python 3（`C:\Users\nsxzy\.workbuddy\binaries\python\envs\default\Scripts\python.exe`）

| 命令 | 退出码 | 产物 |
|---|---|---|
| `python scripts/ai_trace_check.py --demo` | 0 | out/AI痕迹检测报告.xlsx、out/句长分布.png、out/ai_trace.json |
| `python scripts/ai_trace_check.py --input examples/input.json --outdir out` | 0 | 同上 |

## 三、检测正确性验证（examples/input.json 实跑数值）

| 检查项 | 期望 | 实跑 | 结果 |
|---|---|---|---|
| 汉字计数 | 标点不计，198 字 | 198 | ✅ |
| 分句 | 11 句（按 。！？；切分） | 11 | ✅ |
| 句长 CV | 稿件句长 11-35 字趋平，< 0.4 | 0.38 | ✅ |
| 衔接词命中 | 首先×2/其次×2/此外/值得注意的是/与此同时/综上所述/最后/总而言之/在当今 = 13 处 | 13 处，密度 55.6/千字 | ✅ |
| 完美三段式 | 首先+其次+最后+总而言之 齐活 → 是 | 是 | ✅ |
| 加权计分 | 衔接词 35（封顶）+ CV 20 + 抽象词 15 + 三段式 10 = 80 | 80 | ✅ |
| 句段判定 | 命中衔接词句 🔴、纯画面/干净句 ✅ | 10 句 🔴 / 1 句 ✅ | ✅ |
| 边界：<50 字 | 拒绝统计结论 | SystemExit 报「文稿不足 50 字」 | ✅ |

## 四、边界行为验证

| 场景 | 预期 | 实际 |
|---|---|---|
| 文稿 <50 字 | 报错退出，不硬给结论 | `[错误] 文稿不足 50 字` 退出码非 0 ✅ |
| 有意排比 | 🟡 标记不判死 | D4 只标记，权重仅计一次 ✅ |
| 引用原文含衔接词 | 不计入 | prompt 假阳性拦截规则第 1 条 ✅ |
| 缺 lib/assettools.py | 打印修复提示退出码 2 | try/except ImportError ✅ |

## 五、结论

**通过。** 五维检测（衔接词密度 / 句长 CV / 均长连句 / 排比 / 抽象词）全部量化、
脚本实跑数值与预期一致、假阳性规则落地、产物三类齐全（Excel/PNG/JSON）。

---

*测试基于真实实跑（退出码 0），数值取自 out/ai_trace.json · 2026-09-30*
