# 脚本创作师

> **从选题到过检成稿的脚本流水线，写得快且不被限流**

[![Stage](https://img.shields.io/badge/stage-P0-orange)](https://github.com/bangwozuo)
[![Assets](https://img.shields.io/badge/assets-10%20(6%20skills%20%2B%204%20flows)-blueviolet)](#资产矩阵)
[![NoKey](https://img.shields.io/badge/API%20Key-not%20required-success)](#资产形态)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

---

## 它是谁

面向 **自媒体创作者** 的数字员工资产包。

| 项目 | 内容 |
|------|------|
| 目标用户 | 短视频/直播创作者（亿级账号池），日更/隔日更口播类作者 |
| 交付物 | 单脚本产出时长 ≤15 分钟（原 3-6h 创作环节中的写作段）；AI 检测通过率 ≥90%；成片采用率 ≥60% |
| 资产数 | 10（6 技能 + 4 工作流），其中 6 个带确定性脚本、可实跑出 Excel/PNG 产物 |
| 旧名存档 | `短视频脚本创作师` |

### 数字员工总览：一条脚本流水线

「脚本创作师」不是一个工具，而是一条**从选题到过检出稿的完整链路**——10 个资产各守一段，量化标准互相咬合：

```text
选题 ──▶ 钩子锻造（首句≤15字·3s出信息差）
     ──▶ 结构成稿（四段式·语速3.5-6字/秒·60s=240-300字）
     ──▶ 口语化改写（衔接词<1/千字·句长8-14字·CV≥0.5）
     ──▶ 人设语气（五维画像·脚本实跑 voice_profile.py）
     ──▶ 发布前闸门（五维AI痕迹分<30 + 敏感词零红线，才放行）
```

每个环节「该用什么数字卡、卡不住怎么办」见下方[资产矩阵](#资产矩阵)。

## 20 秒看真实执行

[![演示视频：5 个资产的真实执行截图](skills/ai-trace-check/docs/assets/run-terminal.png)](https://cdn.jsdelivr.net/gh/bangwozuo/script-writer-zh@main/docs/demo.mp4)

*点击观看 20 秒演示（`docs/demo.mp4`，1180×1080，每帧 4 秒）：选题转脚本 → 分镜清单 → 敏感词扫描 → AI 痕迹检测 → 降 AI 味闸门，全部为脚本 `--run` 真实执行截图，非摆拍。*

---

## 资产形态

**T1/T2/T3 分层** —— 这是理解本仓库的关键：

| 层 | 形态 | 数量 | 说明 |
|------|------|------|------|
| T1 产物型 | 技能 + 脚本 | 2 | 脚本实跑出 Excel/PNG/JSON 产物（ai-trace-check、persona-voice-library） |
| T2 纯提示词 | 仅提示词 | 4 | 复制粘贴即用，零脚本零依赖（钩子/结构/口语化/敏感词） |
| T3 编排型 | 工作流 + 脚本 | 4 | 编排 T1/T2 资产成链路，校验环节脚本确定性执行 |

| 特性 | 说明 |
|------|------|
| ✅ 无需 API Key | 一个 Key 都不需要 |
| ✅ 无需部署 | 脚本只依赖 Python 标准库 + openpyxl，纯提示词资产零依赖 |
| ✅ 平台无关 | 提示词粘贴到任何 AI 工具即可使用 |
| ✅ 用户自备算力 | 模型来自你自己的订阅 |
| ✅ 校验不靠口算 | 凡是数字判定（字数/语速/痕迹分/词表），一律脚本实跑 |

---

## 快速开始

```text
1. 打开 skills/script-structure-generate/prompt.txt
2. 全文复制
3. 粘贴到你常用的 AI 工具（Coze / WorkBuddy / Dify / Claude / ChatGPT）
4. 按 SKILL.md 的输入规格提供数据
```

就这四步。完整指引见 [使用手册](docs/04-usage.md)。带脚本的资产可直接实跑演示：

```bash
python skills/ai-trace-check/scripts/ai_trace_check.py --demo
python workflows/topic-to-script-flow/scripts/run_flow.py --demo
```

---

## 资产矩阵

| # | 资产 | 层 | 核心量化规则（来自各资产自己的文件） | 脚本 | 实跑产物 | README |
|---|------|---|------|------|------|------|
| 1 | [脚本结构生成](skills/script-structure-generate/README.md) | T2 | 四段式时间轴（钩子0-3s/痛点3-15s/主体15-50s/CTA50-60s）；钩子 ≤15 字 ≤3s；语速 3.5-6 字/秒；60s=240-300 字 | — | — | ✓ |
| 2 | [钩子文案锻造](skills/hook-copy-craft/README.md) | T2 | 5 类型公式（悬念/反差/利益/提问/热点借势）；首句 ≤15 字；3s 内出信息差；正文能兑现 | — | — | ✓ |
| 3 | [口语化改写](skills/colloquial-rewrite/README.md) | T2 | 六指标自查：衔接词 <1/千字、句长 8-14 字、句长 CV≥0.5、均长连句 0 组、语气词 2-4/百字、总字数=时长×4-5 字 | — | — | ✓ |
| 4 | [人设语气库](skills/persona-voice-library/README.md) | T1 | 五维语气画像（句长/词汇/标点/节奏/口头禅）+ 6 项改写约束 | [voice_profile.py](skills/persona-voice-library/scripts/voice_profile.py) | 语气画像.xlsx / 逐篇句长分布.png | ✓ |
| 5 | [AI 痕迹自检](skills/ai-trace-check/README.md) | T1 | 五维计分（权重 35/30/16/15/10）：≥55 高痕迹 / 30-54 灰区 / <30 过检 | [ai_trace_check.py](skills/ai-trace-check/scripts/ai_trace_check.py) | AI痕迹检测报告.xlsx / 句长分布.png | ✓ |
| 6 | [敏感词预审](skills/sensitive-word-precheck/README.md) | T2 | 四组词表（极限词/收益承诺/导流诱导/夸大词）；红线=必改，警告=建议改；判定依据《广告法》 | — | — | ✓ |
| 7 | [选题转脚本](workflows/topic-to-script-flow/README.md) | T3 | 3 步编排 + 人工对稿；6 项校验（钩子/语速/时间轴/字数/预算/平台上限） | [run_flow.py](workflows/topic-to-script-flow/scripts/run_flow.py) | 脚本结构校验表.xlsx / 段落字数分布.png | ✓ |
| 8 | [口播稿口语化改写](workflows/voiceover-colloquial-flow/README.md) | T3 | S1-S4 链路；六指标逐项复检，不达标退回重改 | [run_flow.py](workflows/voiceover-colloquial-flow/scripts/run_flow.py) | 口语化改写检查表.xlsx / 句长分布.png | ✓ |
| 9 | [分镜与拍摄清单](workflows/storyboard-shotlist-flow/README.md) | T3 | 分镜七字段校验；单镜时长与台词配平，超时逐镜检出 | [run_flow.py](workflows/storyboard-shotlist-flow/scripts/run_flow.py) | 分镜拍摄清单.xlsx / 分镜时长分布.png | ✓ |
| 10 | [AI 痕迹检测与降 AI 味](workflows/ai-trace-detect-reduce-flow/README.md) | T3 | 发布前强制闸门：痕迹分 <30 且敏感词零红线才放行；两条线独立判定，任一红线即打回 | [run_flow.py](workflows/ai-trace-detect-reduce-flow/scripts/run_flow.py) | 降AI味与合规检查表.xlsx / 句长分布.png | ✓ |

---

## 仓库结构

```text
script-writer-zh/
├── README.md / employee.md / package.yaml     # 入口与 12 字段定义卡
├── docs/01~07 + demo.mp4                      # 员工级文档（架构/流程/场景/手册/示例/录像/测试）+ 演示视频
├── skills/                                    # 6 个原子技能（2 个带脚本）
│   └── <skill>/
│       ├── README.md  SKILL.md  prompt.txt  schema.json  examples/
│       ├── scripts/                           # （部分资产）确定性脚本
│       ├── out/                               # （部分资产）脚本实跑产物
│       └── docs/                              # 该技能自己的文档 + assets/ 实跑截图
├── workflows/                                 # 4 条工作流（复合技能，均带脚本）
│   └── <workflow>/
│       ├── README.md  SKILL.md  prompt.txt  schema.json  examples/
│       ├── scripts/run_flow.py                # 链路校验脚本（确定性执行）
│       ├── out/                               # 实跑产物（xlsx / png / json）
│       └── docs/                              # 该工作流自己的文档 + assets/ 实跑截图
├── knowledge/                                 # RAG wiki 知识库
├── connectors/                                # 连接器说明 + 合规红线
├── quality/                                   # 效果基线与追踪日志
└── tests/                                     # 资产校验测试（离线，无需密钥）
```

---

## 交付物导航

| 文档 | 内容 |
|------|------|
| [业务架构](docs/01-architecture.md) | 四层架构 + 数据流 + 能力边界 |
| [工作流流程](docs/02-workflow.md) | 4 条工作流的 DAG 可视化 |
| [使用场景](docs/03-scenarios.md) | 3 个真实场景（含前后对比） |
| [使用手册](docs/04-usage.md) | 各平台导入指引 + 常见问题 |
| [示例库](docs/05-examples.md) | 6 组输入输出示例 |
| [录像脚本](docs/06-recording-script.md) | 7 镜头分镜 + 旁白稿 |
| [校验报告](docs/07-test-report.md) | 资产质量校验结果 |
| [演示视频](https://cdn.jsdelivr.net/gh/bangwozuo/script-writer-zh@main/docs/demo.mp4) | 5 个资产真实执行截图串编（20s） |

---

## 知识库与连接器

| 目录 | 说明 |
|------|------|
| [`knowledge/`](knowledge/README.md) | RAG wiki 知识库：填入业务信息可显著提升输出质量 |
| [`connectors/`](connectors/README.md) | 连接器说明：数据从哪来、怎么合规地来 |

---

## 资产校验

```bash
pip install -r requirements.txt
pytest tests/ -v
```

校验技能完整性、提示词结构、契约一致性、工作流 DAG、技能级与工作流级 docs 完整性、知识库 wiki 与连接器结构。
**不需要任何 API Key。**

---

## 合规声明

- ✅ 所有输出为 **AI 辅助生成**，交付前须人工审核
- ✅ 提示词内置**违禁词禁止清单**，符合《广告法》要求
- ✅ 遵循《人工智能生成合成内容标识办法》
- ✅ 连接器只走**官方 API** 或**用户导出数据**
- ✅ 所有对外发布动作**保留人工确认环节**（工作流 #10 的人工签发闸门不可跳过）

---

## 许可

[Apache-2.0](LICENSE) — 可自由使用、修改、商用

---

*由 bangwozuo 业务库自动生成 · 2026-09-29 · README 投产级改造 2026-10-03*
