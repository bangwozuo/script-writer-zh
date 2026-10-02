# -*- coding: utf-8 -*-
"""
AI 痕迹检测与降 AI 味工作流 —— 端到端编排脚本（发布前强制闸门）。

流程（与 SKILL.md 的 DAG 一致）：
  S1 ai-trace-check          五维 AI 痕迹检测（衔接词/CV/均长连句/排比/抽象词）
  S2 colloquial-rewrite      降 AI 味改写（模型承担；本脚本生成逐处替换建议清单）
  S3 sensitive-word-precheck 敏感词扫描（极限词/导流词/诱导词）
  S4 人工复核                 复检确认后放行

本脚本承担 S1/S3 的确定性部分与 S2 的建议清单生成：
  S1 五维计分（0-100）：衔接词密度(35) / 句长CV(30) / 均长连句(16) / 抽象词(15) / 三段式(10)
  S2 对每处命中生成替换建议（衔接词→删除或口语替换；抽象词→人话对照）
  S3 极限词（广告法第九条口径）/ 导流词 / 诱导词 词表扫描
判定：AI 痕迹分 ≥55 或敏感词红线 ≥1 → 打回；分数 30-54 或仅警告 → 需微调；否则通过。

用法：
  python run_flow.py --input input.json --outdir out
  python run_flow.py --demo

产物：
  out/降AI味与合规检查表.xlsx  检测汇总 / 句段明细 / 改写清单 / 敏感词命中 4 sheet
  out/句长分布.png             逐句长度折线
  out/trace_reduce_flow.json   机器可读结果
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WF_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(WF_DIR))
sys.path.insert(0, os.path.join(REPO, "lib"))

try:
    import assettools as at
except ImportError:  # pragma: no cover
    print("[错误] 未找到 lib/assettools.py。请确认工作流位于 <repo>/workflows/<slug>/scripts/ 下，"
          "且 <repo>/lib/assettools.py 存在。", file=sys.stderr)
    sys.exit(2)

# S1 词表（与 skills/ai-trace-check 同口径）
CONNECTORS = ["首先", "其次", "再者", "此外", "另外", "总之", "综上", "综上所述",
              "总而言之", "值得注意的是", "需要注意的是", "由此可见", "总的来说",
              "与此同时", "换句话说", "换言之", "众所周知", "毋庸置疑", "一方面",
              "另一方面", "随着", "在当今", "事实上", "实际上", "然而", "因此"]
# 连接词 → 口语替换建议（降 AI 味直接可落笔）
CONN_FIX = {
    "首先": "（删除，直接说第一件事）或「先说」",
    "其次": "（删除）或「还有」",
    "再者": "（删除）或「再加上」",
    "此外": "（删除）或「对了」",
    "另外": "（删除）或「还有个事」",
    "总之": "（删除）或「所以你看」",
    "综上": "（删除整句总结，改结论前置）",
    "综上所述": "（删除整句总结，改结论前置）",
    "总而言之": "（删除）或「说白了」",
    "值得注意的是": "「划重点」或直接说重点本身",
    "需要注意的是": "「注意」",
    "由此可见": "（删除，因果让观众自己接上）",
    "总的来说": "（删除）",
    "与此同时": "「同时」或（删除）",
    "换句话说": "「也就是说」",
    "换言之": "「就是说」",
    "众所周知": "（删除——观众未必知道，装熟翻车）",
    "毋庸置疑": "（删除）",
    "一方面": "（删除，改直接对比）",
    "另一方面": "「反过来」",
    "随着": "（删除，直接说现象）",
    "在当今": "（删除，直接说现象）",
    "事实上": "「其实」",
    "实际上": "「其实」",
    "然而": "「但是」或「结果」",
    "因此": "「所以」或（删除）",
}
BUZZWORDS = ["赋能", "抓手", "闭环", "颗粒度", "底层逻辑", "顶层设计", "组合拳",
             "深度", "全面提升", "全链路", "一站式", "全方位", "多维", "助力",
             "打造", "涵盖", "旨在", "卓越", "极致体验", "重塑", "引领"]

# S3 敏感词词表（与 skills/sensitive-word-precheck 同口径）
RED_WORDS = [
    (r"最[好佳优强低便宜先进流行受欢迎档]|第一|TOP\s*1|唯一|独家|首创|首款|顶级|国家级|世界级",
     "绝对化用语", "《广告法》第九条", "改用具体描述或可溯源数据"),
    (r"稳赚|保本|零风险|保收益|日入过万|稳赚不赔|百分百回本",
     "收益承诺", "《广告法》第二十五条", "改「收益有波动，附本人真实记录」"),
    (r"100\s*%|彻底|根治|根除|永不|无任何副作用",
     "功效断言", "《广告法》第九条", "改「实测反馈良好（样本 n 人）」"),
]
WARN_WORDS = [
    (r"神器|天花板|绝绝子|史上最|爆款",
     "夸大词堆叠", "平台降推荐权重", "改具体描述"),
    (r"加微信|加VX|微信号|扫码|私信领|评论区扣1抽奖|点赞返现",
     "导流/诱导", "平台社区规范（限流/扣分）", "改平台内交付（主页橱窗/官方组件）"),
]
PUNCT = re.compile(
    r"[\uFF0C\u3002\uFF01\uFF1F\uFF1B\uFF1A\u3001\u201C\u201D\u2018\u2019\u300C\u300D"
    r"\u2026\u2014,.:;()()\s~\uFF5E\-\u2014\u00B7]")
SENT = re.compile(r"[。！？；!?;]")

DEMO = {
    "text": ("在当今数字化时代，副业已经成为很多人的选择。首先，我们要选对平台。"
             "其次，我们要坚持输出内容。此外，我们还要打造个人品牌。"
             "值得注意的是，副业不是躺赚。与此同时，我们也要保持学习。"
             "综上所述，这套方法堪称神器，帮你稳赚不赔。想要资料的加微信领取。"
             "只要坚持执行计划，副业收入就能稳步提升，最终实现个人价值的全面提升。"),
    "target_duration_s": 60,
}


def _hanzi(s: str) -> int:
    return len(PUNCT.sub("", s or ""))


def analyze(text):
    """S1 五维检测，返回 (metrics, sentences, issues, score)。"""
    n_chars = _hanzi(text)
    sents = [s for s in SENT.split(text) if _hanzi(s) > 0]
    lens = [_hanzi(s) for s in sents]
    n = len(sents)
    mu = sum(lens) / n if n else 0.0
    sigma = (sum((x - mu) ** 2 for x in lens) / n) ** 0.5 if n else 0.0
    cv = sigma / mu if mu else 0.0

    conn_hits = []
    for w in CONNECTORS:
        c = text.count(w)
        if c:
            conn_hits.append({"命中词": w, "次数": c,
                              "替换建议": CONN_FIX.get(w, "（删除）")})
    conn_total = sum(h["次数"] for h in conn_hits)
    conn_density = conn_total / n_chars * 1000 if n_chars else 0.0

    buzz_hits = [{"命中词": w, "次数": c}
                 for w in BUZZWORDS if (c := text.count(w)) > 0]
    buzz_total = sum(h["次数"] for h in buzz_hits)
    buzz_density = buzz_total / n_chars * 1000 if n_chars else 0.0

    flat_runs, run = [], []
    for i, L in enumerate(lens):
        if L > 18 and (not run or abs(L - run[-1][1]) <= 2):
            run.append((i, L))
        else:
            if len(run) >= 3:
                flat_runs.append(run)
            run = [(i, L)] if L > 18 else []
    if len(run) >= 3:
        flat_runs.append(run)

    has_perfect = text.count("首先") > 0 and text.count("其次") > 0 and \
        (text.count("最后") > 0 or text.count("总之") > 0 or text.count("综上") > 0)

    pts1 = min(35, conn_density * 12)
    pts2 = 0 if cv >= 0.5 else (10 if cv >= 0.4 else (20 if cv >= 0.3 else 30))
    pts3 = min(16, len(flat_runs) * 8)
    pts4 = min(15, buzz_density * 6)
    pts5 = 10 if has_perfect else 0
    score = round(min(100, pts1 + pts2 + pts3 + pts4 + pts5))

    metrics = {"字数": n_chars, "句数": n, "平均句长": round(mu, 1),
               "句长CV": round(cv, 2), "衔接词/千字": round(conn_density, 1),
               "抽象词/千字": round(buzz_density, 1), "均长连句组": len(flat_runs),
               "三段式": "是" if has_perfect else "否", "AI痕迹分": score}

    flat_idx = {i for run in flat_runs for i, _ in run}
    sentences = []
    for i, s in enumerate(sents):
        hits = [w for w in CONNECTORS if w in s[:8]]
        tags = ("衔接词:" + "/".join(hits[:2])) if hits else ""
        if i in flat_idx:
            tags = (tags + " 均长连句").strip()
        if _hanzi(s) > 30:
            tags = (tags + f" 长句{_hanzi(s)}字").strip()
        verdict = "🔴" if (hits or i in flat_idx) else "✅"
        sentences.append({"#": i + 1, "句长": _hanzi(s), "句子": s[:28],
                          "痕迹": tags or "—", "判定": verdict})

    issues = []
    if conn_density > 3:
        issues.append(f"🔴 衔接词密度 {conn_density:.1f}/千字 > 3（{conn_total} 处），逐处替换")
    if cv < 0.4:
        issues.append(f"🔴 句长 CV {cv:.2f} < 0.4，句长趋平需长短句交错")
    if flat_runs:
        issues.append(f"🔴 检出 {len(flat_runs)} 组连续 3 句同长 >18 字（AI 腔硬指标）")
    if buzz_density > 2:
        issues.append(f"🔴 抽象词密度 {buzz_density:.1f}/千字 > 2（汇报腔）")
    if has_perfect:
        issues.append("🔴 完美三段式（首先/其次/最后+总之），改结论前置")
    if not issues:
        issues.append("✅ 五维指标达标")

    return metrics, sentences, issues, score, conn_hits, buzz_hits, lens


def sensitive_scan(text):
    """S3 敏感词扫描，返回 (rows, n_red, n_warn)。"""
    rows = []
    n_red = n_warn = 0
    for pat, rule, basis, fix in RED_WORDS:
        for m in re.finditer(pat, text):
            rows.append({"级别": "🔴 红线", "原文片段": m.group(0), "命中规则": rule,
                         "依据": basis, "建议改法": fix})
            n_red += 1
    for pat, rule, basis, fix in WARN_WORDS:
        for m in re.finditer(pat, text):
            rows.append({"级别": "🟡 警告", "原文片段": m.group(0), "命中规则": rule,
                         "依据": basis, "建议改法": fix})
            n_warn += 1
    return rows, n_red, n_warn


def build(payload, outdir):
    text = payload.get("text", "")
    if _hanzi(text) < 50:
        raise SystemExit("[错误] 文稿不足 50 字（汉字实数），无法做统计检测")
    metrics, sentences, issues, score, conn_hits, buzz_hits, lens = analyze(text)
    sens_rows, n_red, n_warn = sensitive_scan(text)

    at.ensure_outdir(outdir)
    if score >= 55 or n_red >= 1:
        verdict = "打回重改（不得发布）"
    elif score >= 30 or n_warn >= 1:
        verdict = "需微调"
    else:
        verdict = "通过"
    summary = [
        {"项": "AI 痕迹分", "内容": f"{score}（≥55 高 / 30-54 中 / <30 正常）"},
        {"项": "敏感词", "内容": f"红线 {n_red} / 警告 {n_warn}"},
        {"项": "整体判定", "内容": verdict},
    ] + [{"项": f"问题{i+1}", "内容": it} for i, it in enumerate(issues)] + \
        [{"项": k, "内容": str(v)} for k, v in metrics.items()]

    xlsx = at.write_excel(
        os.path.join(outdir, "降AI味与合规检查表.xlsx"),
        {"检测汇总": summary,
         "句段明细": sentences or [{"#": "", "句长": "", "句子": "", "痕迹": "", "判定": ""}],
         "改写清单": conn_hits or [{"命中词": "（无）", "次数": "", "替换建议": ""}],
         "敏感词命中": sens_rows or [{"级别": "", "原文片段": "（无）", "命中规则": "",
                              "依据": "", "建议改法": ""}]},
        highlights={"句段明细": {"判定": "contains:🔴"},
                    "敏感词命中": {"级别": "contains:红线"},
                    "检测汇总": {"内容": "contains:🔴"}},
        widths={"句段明细": {"句子": 32, "痕迹": 22},
                "改写清单": {"替换建议": 40},
                "敏感词命中": {"建议改法": 36}})
    png = at.line_chart(
        os.path.join(outdir, "句长分布.png"),
        list(range(1, len(lens) + 1)),
        {"逐句字数": lens},
        title=f"逐句长度（AI 痕迹分 {score}）", xlabel="句序号", ylabel="字")
    js = at.write_json({
        "verdict": verdict, "score": score, "metrics": metrics, "issues": issues,
        "sentences": sentences, "rewrite_list": conn_hits,
        "sensitive_hits": sens_rows, "n_red": n_red, "n_warn": n_warn,
        "generated_at": at.stamp(),
        "note": "检测与词表扫描由脚本完成；语境判断（引用/有意排比）与实际改写由模型按 prompt.txt 复核，改后须复检"},
        os.path.join(outdir, "trace_reduce_flow.json"))
    print(f"闸门判定 —— {verdict}（AI 痕迹分 {score}，敏感词红线 {n_red} 警告 {n_warn}）")
    files = [xlsx, png, js]
    for f in files:
        print(" 产物:", f)
    at.emit({"verdict": verdict, "score": score, "n_red": n_red, "issues": issues,
             "files": files})
    return files


def main():
    ap = argparse.ArgumentParser(description="AI 痕迹检测与降 AI 味工作流 —— 发布闸门")
    ap.add_argument("--input", help="输入 JSON（text/target_duration_s）")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    payload = DEMO if a.demo else (at.read_json(a.input) if a.input else ap.error("需要 --input 或 --demo"))
    build(payload, a.outdir)


if __name__ == "__main__":
    main()
