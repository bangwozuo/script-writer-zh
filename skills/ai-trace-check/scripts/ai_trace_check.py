# -*- coding: utf-8 -*-
"""
AI 痕迹自检 —— 句长起伏（Burstiness）/ 衔接词 / 排比 / 抽象词五维量化检测器。

职责边界：本脚本只做**可量化的统计检测与产物生成**（句长方差、词表命中密度
是机器的强项）。语境判断（这句排比是不是有意的节奏设计）、改写方案由模型按
prompt.txt 完成（这是模型的强项）。

检测维度（五维，全部量化）：
  D1 衔接词密度   「首先/其次/总之/综上所述/值得注意的是」每千字命中数
  D2 句长起伏     句长变异系数 CV = σ/μ；人写 ≥0.5，AI 生成趋平 <0.4
  D3 均长连句     连续 3 句长度差 ≤2 字且 >18 字（AI 腔特征）
  D4 排比三连     连续 ≥3 句前 2 字相同
  D5 抽象高频词   「赋能/抓手/闭环/深度/全面提升」每千字密度

用法：
  python ai_trace_check.py --input input.json --outdir out
  python ai_trace_check.py --demo
  python ai_trace_check.py --text "要检测的文稿……"

产物：
  out/AI痕迹检测报告.xlsx   五维汇总 / 句段明细 / 命中词表 三 sheet
  out/句长分布.png          逐句长度折线（肉眼可见"趋平"还是"起伏"）
  out/ai_trace.json         机器可读结果（供工作流读取）
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(SKILL_DIR))
sys.path.insert(0, os.path.join(REPO, "lib"))

try:
    import assettools as at
except ImportError:  # pragma: no cover
    print("[错误] 未找到 lib/assettools.py。请确认技能位于 <repo>/skills/<slug>/scripts/ 下，"
          "且 <repo>/lib/assettools.py 存在。", file=sys.stderr)
    sys.exit(2)

# ---------------------------------------------------------------- 词表

# D1 AI 高频衔接词（书面/机器味：人写口播稿几乎不用这些起头）
CONNECTORS = [
    "首先", "其次", "再者", "再次", "此外", "另外", "总之", "综上", "综上所述",
    "总而言之", "值得注意的是", "需要注意的是", "由此可见", "总的来说", "与此同时",
    "不仅", "而且", "因此", "然而", "事实上", "实际上", "换句话说", "换言之",
    "众所周知", "册庸置疑", "毋庸置疑", "一方面", "另一方面", "随着", "在当今",
]

# D5 抽象高频词（互联网黑话 / 汇报腔，口播稿里出现即劝退）
BUZZWORDS = [
    "赋能", "抓手", "闭环", "颗粒度", "底层逻辑", "顶层设计", "组合拳", "对齐",
    "深度", "全面提升", "全链路", "一站式", "全方位", "多维", "助力", "打造",
    "涵盖", "旨在", "卓越", "极致体验", "领跑", "引领", "重塑", "格局",
]

# 人称/口语标志词（正面指标：命中越多越像人话）
ORAL_MARKS = ["我", "你", "咱们", "咱", "家人们", "兄弟们", "姐妹们", "说实话",
              "讲真", "你猜", "我跟你说", "别急", "注意", "记住了"]

# 停用片段：分句时按 。！？；切，但排除小数点等（简化处理，仅取整句）
SENT_SPLIT = re.compile(r"[。！？；!?;]")
PUNCT = re.compile(r"[，。！？；：、“”‘’「」…—,.:;()\uFF08\uFF09\s~～\-—·]")

DEMO = {
    "text": ("在当今数字化时代，掌握副业技能已经成为许多人的迫切需求。首先，我们需要明确副业的定位。"
             "其次，我们需要评估自己的时间分配。此外，我们还需要考虑技能的变现路径。"
             "值得注意的是，副业的选择必须与主业形成互补。与此同时，我们也要警惕副业对主业的影响。"
             "综上所述，副业的发展需要一个系统性的规划。首先，规划要考虑市场需求。"
             "其次，规划要考虑个人能力。最后，规划要考虑长期的成长空间。"
             "总而言之，只要坚持执行计划，副业收入就能稳步提升，最终实现个人价值的全面提升。"),
}


def _hanzi(s: str) -> int:
    return len(PUNCT.sub("", s or ""))


def split_sentences(text: str):
    sents = [s for s in SENT_SPLIT.split(text or "") if _hanzi(s) > 0]
    return sents


def _count(term: str, text: str) -> int:
    return text.count(term)


def analyze(text: str):
    """五维检测，返回 (metrics, sentence_rows, issue_rows)。"""
    n_chars = _hanzi(text)
    sents = split_sentences(text)
    lens = [_hanzi(s) for s in sents]
    n = len(sents)
    mu = sum(lens) / n if n else 0.0
    sigma = (sum((x - mu) ** 2 for x in lens) / n) ** 0.5 if n else 0.0
    cv = sigma / mu if mu else 0.0

    # D1 衔接词
    conn_hits = []
    for w in CONNECTORS:
        c = _count(w, text)
        if c:
            conn_hits.append({"命中词": w, "次数": c})
    conn_total = sum(h["次数"] for h in conn_hits)
    conn_density = conn_total / n_chars * 1000 if n_chars else 0.0

    # D5 抽象词
    buzz_hits = []
    for w in BUZZWORDS:
        c = _count(w, text)
        if c:
            buzz_hits.append({"命中词": w, "次数": c})
    buzz_total = sum(h["次数"] for h in buzz_hits)
    buzz_density = buzz_total / n_chars * 1000 if n_chars else 0.0

    # D3 均长连句：连续 3 句两两差 ≤2 字且 >18 字
    flat_runs = []
    run = []
    for i, L in enumerate(lens):
        if L > 18 and (not run or abs(L - run[-1][1]) <= 2):
            run.append((i, L))
        else:
            if len(run) >= 3:
                flat_runs.append(run)
            run = [(i, L)] if L > 18 else []
    if len(run) >= 3:
        flat_runs.append(run)

    # D4 排比三连：连续 ≥3 句前 2 字相同
    para_runs = []
    run = []
    for i, s in enumerate(sents):
        head = s[:2]
        if run and head != run[-1][1]:
            if len(run) >= 3:
                para_runs.append(run)
            run = []
        run.append((i, head))
    if len(run) >= 3:
        para_runs.append(run)

    # D2 完美三段式（首先…其次…最后/总之 同时出现）
    has_perfect = all(_count(w, text) > 0 for w in ("首先", "其次")) and \
        (_count("最后", text) > 0 or _count("总之", text) > 0 or _count("综上", text) > 0)

    # 计分（0-100，越高 AI 痕迹越重）
    pts1 = min(35, conn_density * 12)                       # 衔接词权重 35
    if cv >= 0.5:
        pts2 = 0
    elif cv >= 0.4:
        pts2 = 10
    elif cv >= 0.3:
        pts2 = 20
    else:
        pts2 = 30                                           # 句长趋平权重 30
    pts3 = min(16, len(flat_runs) * 8)                      # 均长连句权重 16
    pts4 = min(15, buzz_density * 6)                        # 抽象词权重 15
    pts5 = 10 if has_perfect else 0                         # 三段式权重 10
    score = round(min(100, pts1 + pts2 + pts3 + pts4 + pts5))

    oral_total = sum(_count(w, text) for w in ORAL_MARKS)
    oral_density = oral_total / n_chars * 1000 if n_chars else 0.0

    metrics = {
        "文稿字数": n_chars,
        "句数": n,
        "平均句长": round(mu, 1),
        "句长标准差": round(sigma, 1),
        "句长变异系数CV": round(cv, 2),
        "衔接词密度/千字": round(conn_density, 1),
        "抽象词密度/千字": round(buzz_density, 1),
        "口语标志词密度/千字": round(oral_density, 1),
        "均长连句组数": len(flat_runs),
        "排比三连组数": len(para_runs),
        "完美三段式": "是" if has_perfect else "否",
        "AI痕迹分": score,
    }

    # 句段明细
    flat_idx = {i for run in flat_runs for i, _ in run}
    para_idx = {i for run in para_runs for i, _ in run}
    rows = []
    for i, s in enumerate(sents):
        L = lens[i]
        tags = []
        hit_conn = [w for w in CONNECTORS if s.startswith(w) or (w in s[:8])]
        if hit_conn:
            tags.append("衔接词:" + "/".join(hit_conn[:2]))
        if i in flat_idx:
            tags.append("均长连句")
        if i in para_idx:
            tags.append("排比成员")
        if L > 30:
            tags.append(f"长句{L}字")
        verdict = "🔴" if (hit_conn or i in flat_idx) else ("🟡" if i in para_idx or L > 30 else "✅")
        rows.append({"#": i + 1, "句长": L, "句子": s[:30], "痕迹标记": " ".join(tags) or "—",
                     "判定": verdict})

    issues = []
    if conn_density > 3:
        issues.append(f"🔴 衔接词密度 {conn_density:.1f}/千字 > 3：AI 腔首要特征，逐个替换或直接删除")
    elif conn_density >= 1:
        issues.append(f"🟡 衔接词密度 {conn_density:.1f}/千字 在 1-3 区间，建议压到 1 以下")
    if cv < 0.4:
        issues.append(f"🔴 句长变异系数 {cv:.2f} < 0.4：句长趋平，人写文本 CV 通常 ≥0.5，需长短句交错改写")
    if flat_runs:
        issues.append(f"🔴 检出 {len(flat_runs)} 组连续 3 句同长(>18 字)：判「AI 腔」的硬指标，必须打散")
    if para_runs:
        issues.append(f"🟡 检出 {len(para_runs)} 组排比三连：口播排比是节奏手段，保留 ≤1 组，多余的换写法")
    if buzz_density > 2:
        issues.append(f"🔴 抽象词密度 {buzz_density:.1f}/千字 > 2：汇报腔，口播稿全部换成人话")
    if has_perfect:
        issues.append("🔴 「首先/其次/最后(总之)」完美三段式：机器味最重结构，改为结论前置+自然展开")
    if not issues:
        issues.append("✅ 五维指标全部达标，人味正常")

    return metrics, rows, issues, conn_hits, buzz_hits, lens


def verdict_of(score: int) -> str:
    if score >= 55:
        return "🔴 高 AI 痕迹（须降 AI 味改写后再发布）"
    if score >= 30:
        return "🟡 中度 AI 痕迹（建议按句段明细改写后复检）"
    return "✅ 人味正常（可直接进入发布流程）"


def build(payload, outdir):
    text = payload.get("text", "")
    if _hanzi(text) < 50:
        raise SystemExit("[错误] 文稿不足 50 字（按汉字实数计），无法做统计检测，请提供完整文稿")

    metrics, rows, issues, conn_hits, buzz_hits, lens = analyze(text)
    score = metrics["AI痕迹分"]
    verdict = verdict_of(score)

    at.ensure_outdir(outdir)
    summary_rows = [{"检测维度": k, "结果": str(v)} for k, v in metrics.items()]
    summary_rows.append({"检测维度": "整体判定", "结果": verdict})
    summary_rows += [{"检测维度": f"问题{i+1}", "结果": it} for i, it in enumerate(issues)]

    xlsx = at.write_excel(
        os.path.join(outdir, "AI痕迹检测报告.xlsx"),
        {
            "五维汇总": summary_rows,
            "句段明细": rows or [{"#": "", "句长": "", "句子": "", "痕迹标记": "", "判定": ""}],
            "衔接词命中": conn_hits or [{"命中词": "（无）", "次数": ""}],
            "抽象词命中": buzz_hits or [{"命中词": "（无）", "次数": ""}],
        },
        highlights={"句段明细": {"判定": "contains:🔴"},
                    "五维汇总": {"结果": "contains:🔴"}},
        widths={"句段明细": {"句子": 34, "痕迹标记": 24},
                "五维汇总": {"结果": 46}},
    )
    if lens:
        png = at.line_chart(
            os.path.join(outdir, "句长分布.png"),
            list(range(1, len(lens) + 1)),
            {"逐句字数": lens},
            title="逐句长度分布：起伏大=人写，趋平=AI 腔",
            xlabel="句序号", ylabel="句长（字）")
    else:
        png = None
    js = at.write_json({
        "verdict": verdict, "score": score, "metrics": metrics, "issues": issues,
        "sentences": rows, "generated_at": at.stamp(),
        "note": "统计检测由脚本完成；语境判断（有意排比、引用原文）与改写方案由模型按 prompt.txt 复核",
    }, os.path.join(outdir, "ai_trace.json"))

    print(f"AI 痕迹分 {score} —— {verdict}")
    files = [f for f in (xlsx, png, js) if f]
    for f in files:
        print(" 产物:", f)
    at.emit({"verdict": verdict, "score": score, "metrics": metrics,
             "issues": issues, "files": files})
    return files


def main():
    ap = argparse.ArgumentParser(description="AI 痕迹自检 —— 五维量化检测")
    ap.add_argument("--input", help="输入 JSON（含 text 字段）")
    ap.add_argument("--text", help="直接传文稿")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true", help="用内置 AI 腔样例跑一遍")
    a = ap.parse_args()

    if a.demo:
        payload = DEMO
    elif a.input:
        payload = at.read_json(a.input)
    elif a.text:
        payload = {"text": a.text}
    else:
        ap.error("需要 --input / --text / --demo 之一")

    build(payload, a.outdir)


if __name__ == "__main__":
    main()
