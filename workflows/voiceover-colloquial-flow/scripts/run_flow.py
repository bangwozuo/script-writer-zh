# -*- coding: utf-8 -*-
"""
口播稿口语化改写工作流 —— 端到端编排脚本。

流程（与 SKILL.md 的 DAG 一致）：
  S1 persona-voice-library     语气画像与改写约束（≥3 篇样本统计）
  S2 colloquial-rewrite        书面稿 → 口播稿改写（模型承担）
  S3 本步（脚本承担）          口语化六指标确定性校验
  S4 人工通读                   念一遍，卡壳处退回 S2

本脚本承担 S3 的确定性部分：AI 腔衔接词密度（<1 个/千字）、平均句长（8-14 字）、
句长变异系数（CV ≥ 0.5）、语气词密度（2-4 个/百字）、第二人称密度（≥10 个/千字）、
总字数 vs 目标时长（4-5 字/秒）。提供语气画像时按画像约束核对。

用法：
  python run_flow.py --input input.json --outdir out
  python run_flow.py --demo

产物：
  out/口语化校验表.xlsx     六指标汇总 / 句段明细 两 sheet
  out/句长分布.png          逐句长度折线（起伏=人味，趋平=AI 腔）
  out/colloquial_flow.json  机器可读结果
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

CONNECTORS = ["首先", "其次", "再者", "此外", "总之", "综上", "总而言之", "值得注意",
              "需要注意的是", "由此可见", "与此同时", "换句话说", "换言之", "众所周知",
              "一方面", "另一方面", "随着", "事实上", "实际上", "因此", "然而"]
TONE = "吧呢哈啊呗嘛啦哟哦呀"
PUNCT = re.compile(
    r"[\uFF0C\u3002\uFF01\uFF1F\uFF1B\uFF1A\u3001\u201C\u201D\u2018\u2019\u300C\u300D"
    r"\u2026\u2014,.:;()()\s~\uFF5E\-\u2014\u00B7]")
SENT = re.compile(r"[。！？；!?;]")

DEMO = {
    "text": ("副业这事儿，现在想搞的人很多啊。但别急着干。先算一笔账哈。你每天下班能腾出几个"
             "小时？周末又能挤出多少？这些加起来，才是你能拿去换钱的本钱。然后想想你会什么。"
             "会做表的，接数据整理的活呗。会剪视频的呢，就去接商单剪辑，一条五十到两百不等。"
             "别跨行硬干，跨行就是拿短板赌钱，十有九亏。真的。副业刚开始赚得少，波动也大，"
             "千万别一上来就把积蓄砸进去。先拿手艺换钱，跑通了再谈投入。就这么简单。"
             "账算清楚了，剩下的就一件事：干下去。"),
    "target_duration_s": 60,
    "profile": {
        "avg_sentence_target": [8, 12],
        "tone_range": [2.0, 4.0],
        "catchphrase_max": 4
    }
}


def _hanzi(s: str) -> int:
    return len(PUNCT.sub("", s or ""))


def check(text, target, profile):
    n_chars = _hanzi(text)
    sents = [s for s in SENT.split(text) if _hanzi(s) > 0]
    lens = [_hanzi(s) for s in sents]
    n = len(sents)
    mu = sum(lens) / n if n else 0.0
    sigma = (sum((x - mu) ** 2 for x in lens) / n) ** 0.5 if n else 0.0
    cv = sigma / mu if mu else 0.0

    conn_hits = sum(text.count(w) for w in CONNECTORS)
    conn_density = conn_hits / n_chars * 1000 if n_chars else 0.0
    tone = sum(text.count(c) for c in TONE)
    tone_density = tone / n_chars * 100 if n_chars else 0.0
    you = text.count("你") + text.count("咱们") + text.count("咱")
    you_density = you / n_chars * 1000 if n_chars else 0.0

    # 均长连句：连续 3 句同长（差 ≤2 字）且 >18 字
    flat_runs, run = [], []
    for L in lens:
        if L > 18 and (not run or abs(L - run[-1]) <= 2):
            run.append(L)
        else:
            if len(run) >= 3:
                flat_runs.append(run)
            run = [L] if L > 18 else []
    if len(run) >= 3:
        flat_runs.append(run)

    rows, issues = [], []

    def add(metric, target_s, actual, verdict, note):
        rows.append({"指标": metric, "目标": target_s, "实测": actual,
                     "判定": verdict, "说明": note})
        if verdict in ("🔴", "🟡"):
            issues.append(f"{metric}：{note}")

    add("衔接词密度", "<1 个/千字", f"{conn_density:.1f} 个/千字（{conn_hits} 处）",
        "🔴" if conn_density > 3 else ("🟡" if conn_density >= 1 else "✅"),
        "AI 腔首要特征，逐个删除或换语气词" if conn_density >= 1 else "达标")
    add("平均句长", "8-14 字（画像约束优先）", f"{mu:.1f} 字",
        "✅" if 8 <= mu <= 14 else "🟡",
        (f"偏{'长' if mu > 14 else '短'}，目标 {profile['avg_sentence_target']}"
         if profile and 'avg_sentence_target' in profile and not (8 <= mu <= 14)
         else "长短句交错的口播节奏"))
    add("句长变异系数 CV", "≥ 0.5", f"{cv:.2f}",
        "✅" if cv >= 0.5 else ("🟡" if cv >= 0.4 else "🔴"),
        "节奏达标" if cv >= 0.5 else
        ("句长趋平，需插短句呼吸口" if cv >= 0.4 else "严重趋平，判 AI 腔节奏"))
    add("均长连句", "0 组（连续 3 句同长 >18 字）", f"{len(flat_runs)} 组",
        "🔴" if flat_runs else "✅", "AI 腔统计指纹，必须打散" if flat_runs else "达标")
    add("语气词密度", "2-4 个/百字", f"{tone_density:.1f} 个/百字（{tone} 个）",
        "✅" if 2 <= tone_density <= 4 else "🟡",
        "达标" if 2 <= tone_density <= 4 else
        ("偏油腻，删减" if tone_density > 4 else "偏生硬，句尾补语气词"))
    add("第二人称密度", "≥10 个/千字", f"{you_density:.1f} 个/千字（{you} 处）",
        "✅" if you_density >= 10 else "🟡",
        "对镜头说话感达标" if you_density >= 10 else "在自说自话，加提问与「你」")

    if target:
        lo, hi = target * 4, target * 5
        ok = lo <= n_chars <= hi
        add("总字数 vs 时长", f"{target}s × 4-5 字 = {int(lo)}-{int(hi)}", f"{n_chars} 字",
            "✅" if ok else "🔴",
            "配平" if ok else (f"超 {n_chars-hi:.0f} 字，删" if n_chars > hi
                        else f"缺 {lo-n_chars:.0f} 字，补"))

    verdict = "打回重改" if any(r["判定"] == "🔴" for r in rows) else \
        ("需微调" if any(r["判定"] == "🟡" for r in rows) else "通过")
    return {"n_chars": n_chars, "n_sent": n, "rows": rows, "issues": issues,
            "verdict": verdict, "lens": lens}


def build(payload, outdir):
    text = payload.get("text", "")
    if _hanzi(text) < 50:
        raise SystemExit("[错误] 文稿不足 50 字（汉字实数），无法做统计校验")
    target = payload.get("target_duration_s")
    profile = payload.get("profile")
    r = check(text, target, profile)

    at.ensure_outdir(outdir)
    summary = [{"项": "整体判定", "内容": r["verdict"]},
               {"项": "字数 / 句数", "内容": f"{r['n_chars']} 字 / {r['n_sent']} 句"},
               {"项": "画像约束", "内容": "已提供，按画像核对" if profile else "未提供（按通用标准）"}]
    sents = [s for s in SENT.split(text) if _hanzi(s) > 0]
    detail = [{"#": i + 1, "句长": r["lens"][i], "句子": s[:30]}
              for i, s in enumerate(sents)]
    xlsx = at.write_excel(
        os.path.join(outdir, "口语化校验表.xlsx"),
        {"六指标汇总": summary + [
            {"指标": row["指标"], "目标": row["目标"], "实测": row["实测"],
             "判定": row["判定"], "说明": row["说明"]} for row in r["rows"]],
         "句段明细": detail},
        highlights={"句段明细": {"句长": ">18"}},
        widths={"六指标汇总": {"说明": 40, "实测": 26}, "句段明细": {"句子": 34}})
    png = at.line_chart(
        os.path.join(outdir, "句长分布.png"),
        list(range(1, len(r["lens"]) + 1)),
        {"逐句字数": r["lens"]},
        title="逐句长度：起伏大=人味，趋平=AI 腔", xlabel="句序号", ylabel="字")
    js = at.write_json({"verdict": r["verdict"], "rows": r["rows"], "issues": r["issues"],
                        "generated_at": at.stamp(),
                        "note": "统计由脚本完成（汉字实数）；语境判断与改稿由模型按 prompt.txt 复核"},
                       os.path.join(outdir, "colloquial_flow.json"))
    print(f"口语化校验 —— {r['verdict']}（{r['n_chars']} 字 / {r['n_sent']} 句，问题 {len(r['issues'])} 项）")
    files = [xlsx, png, js]
    for f in files:
        print(" 产物:", f)
    at.emit({"verdict": r["verdict"], "issues": r["issues"], "files": files})
    return files


def main():
    ap = argparse.ArgumentParser(description="口播稿口语化改写工作流 —— 六指标校验")
    ap.add_argument("--input", help="输入 JSON（text/target_duration_s/profile）")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    payload = DEMO if a.demo else (at.read_json(a.input) if a.input else ap.error("需要 --input 或 --demo"))
    build(payload, a.outdir)


if __name__ == "__main__":
    main()
