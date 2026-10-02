# -*- coding: utf-8 -*-
"""
选题转脚本工作流 —— 端到端编排脚本。

流程（与 SKILL.md 的 DAG 一致）：
  S1 hook-copy-craft            黄金 3 秒钩子候选（模型产出，钩子 ≤15 字）
  S2 script-structure-generate  四段式结构成稿（模型产出：钩子/痛点/主体/CTA）
  S3 本步（脚本承担）           段落预算/字数/语速/时间轴确定性校验
  S4 人工确认                    逐段念一遍

本脚本承担 S3 的确定性部分：四段式时间轴（60s 基准 钩子3s/痛点12s/主体35s/CTA10s，
其他时长等比缩放 ±2s）、语速 3.5-6.0 字/秒双死线、钩子 ≤3s ≤15 字、
全文总字数落在 时长×4-5 字 区间、平台时长上限核对。

用法：
  python run_flow.py --input input.json --outdir out
  python run_flow.py --demo

产物：
  out/脚本结构校验表.xlsx   逐段校验 / 段落预算 / 平台核对 三 sheet
  out/段落字数分布.png      各段字数 vs 预算柱状图
  out/topic_flow.json       机器可读结果
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

SEG_BUDGET = {"钩子": 3, "痛点": 12, "主体": 35, "CTA": 10}  # 60s 基准
SEG_ORDER = list(SEG_BUDGET)
PLATFORM_MAX = {"抖音": 60, "小红书": 240, "视频号": 60, "B站": 600}
PUNCT = re.compile(
    r"[\uFF0C\u3002\uFF01\uFF1F\uFF1B\uFF1A\u3001\u201C\u201D\u2018\u2019\u300C\u300D"
    r"\u2026\u2014,.:;()()\s~\uFF5E\-\u2014\u00B7]")

DEMO = {
    "topic": "副业避坑：新人最容易踩的三个坑",
    "duration_s": 60,
    "platform": "抖音",
    "hook": "副业第一个月，我踩了三个坑",
    "segments": [
        {"seg": "钩子", "dur_s": 3, "line": "副业第一个月，我踩了三个坑"},
        {"seg": "痛点", "dur_s": 12, "line": "别急着学人家月入过万。先听我说说我怎么亏的。这三个坑，每一个都花过我真金白银。你要是一个都没踩过，那是老天爷赏饭吃。"},
        {"seg": "主体", "dur_s": 35, "line": "先说结论：新人的钱和力气，多半耗在三个坑上。坑一，低价单接太多。我头一个月六成的单是低价单，忙得要死，只贡献两成收入，低价的客户还最难伺候。坑二，没谈改稿次数。有个甲方拖了我整整两周，改了八稿，最后用的还是第一稿。所以接单前，改稿三次封顶，白纸黑字写进聊天记录。坑三，工具买齐了，单没来。设备是干了才配的，不是配好了才开干。记住：先跑通，再升级。"},
        {"seg": "CTA", "dur_s": 10, "line": "这三个坑你踩过哪个？评论区见。"},
    ],
}


def _hanzi(s: str) -> int:
    return len(PUNCT.sub("", s or ""))


def check(segments, target, platform, hook):
    rows, issues = [], []
    cursor = 0
    scale = target / 60.0
    for seg in segments:
        name = seg.get("seg", "")
        dur = seg.get("dur_s", 0)
        line = seg.get("line", "")
        n = _hanzi(line)
        start, end = cursor, cursor + dur
        cursor = end
        if name not in SEG_BUDGET:
            issues.append(f"段落「{name}」不在四段结构内（{'/'.join(SEG_ORDER)}）")
        speed = n / dur if dur else 999
        budget = round(SEG_BUDGET.get(name, dur) * scale)
        if n == 0:
            verdict, note = "🔴", "无台词：口播稿每段都要有话"
        elif speed > 6.0:
            verdict = "🔴"
            over = int(n - dur * 6.0)
            note = f"{speed} 字/秒念不完，{dur}s 最多 {int(dur*6)} 字，删约 {over} 字"
        elif speed < 3.5:
            verdict = "🟡"
            note = f"{speed} 字/秒过稀（<3.5 掉完播），补 {max(0, int(dur*4.5 - n))} 字左右"
        else:
            verdict, note = "✅", f"{speed} 字/秒（预算 {budget}s ±10%）"
        if name == "钩子":
            if dur > 3:
                verdict, note = "🔴", f"钩子 {dur}s > 3s，黄金 3 秒红线"
            if n > 15:
                verdict, note = "🔴", f"钩子 {n} 字 > 15 字，3 秒念不完，退回 hook-copy-craft"
        rows.append({"段落": name, "时间轴": f"{start}-{end}s", "时长s": dur,
                     "预算s": budget, "台词字数": n, "语速": round(speed, 2),
                     "判定": verdict, "台词": line[:20], "说明": note})
        if verdict in ("🔴", "🟡"):
            issues.append(f"{name}（{start}-{end}s）：{note}")
    total = cursor
    if abs(total - target) > 2:
        issues.append(f"时间轴合计 {total}s ≠ 目标 {target}s（允许 ±2s）")
    total_chars = sum(r["台词字数"] for r in rows)
    lo, hi = target * 4, target * 5
    if not (lo <= total_chars <= hi):
        issues.append(f"全文 {total_chars} 字不在 {target}×4-5 字（{int(lo)}-{int(hi)}）区间")
    # 平台上限
    plat_row = {"平台": platform, "时长上限": "待核对官方", "判定": "🔵",
                "说明": "不在常量表，发布前查官方"}
    mx = PLATFORM_MAX.get(platform)
    if mx is not None:
        ok = target <= mx
        plat_row = {"平台": platform, "时长上限": f"{mx}s", "判定": "✅" if ok else "🔴",
                    "说明": f"{target}s 成片" + ("" if ok else
                            f" 超上限 {target-mx}s：抖音需中视频计划，或剪短重排")}
        if not ok:
            issues.append(f"{platform}：{plat_row['说明']}")
    if hook:
        hn = _hanzi(hook)
        if hn > 15:
            issues.append(f"上游钩子 {hn} 字 > 15 字：与正稿钩子段冲突，退回 hook-copy-craft")
    return total, total_chars, rows, issues, plat_row


def build(payload, outdir):
    segments = payload.get("segments") or []
    if not segments:
        raise SystemExit("[错误] segments 为空：需要四段式逐段稿（seg/dur_s/line），不能为空")
    target = payload.get("duration_s", 60)
    platform = payload.get("platform", "抖音")
    total, total_chars, rows, issues, plat_row = check(
        segments, target, platform, payload.get("hook"))

    at.ensure_outdir(outdir)
    summary = [
        {"项": "选题", "内容": payload.get("topic", "（未填）")},
        {"项": "目标时长", "内容": f"{target}s"},
        {"项": "平台", "内容": platform},
        {"项": "全文台词字数", "内容": f"{total_chars} 字（目标 {int(target*4)}-{int(target*5)}）"},
        {"项": "问题数", "内容": str(len(issues))},
        {"项": "整体判定", "内容": "打回重改" if any(i.startswith("🔴") or "🔴" in i for i in issues)
                        else ("需微调" if issues else "通过")},
    ] + [{"项": f"问题{i+1}", "内容": it} for i, it in enumerate(issues)]

    share = []
    agg = {}
    for r in rows:
        agg.setdefault(r["段落"], {"dur": 0, "n": 0})
        agg[r["段落"]]["dur"] += r["时长s"]
        agg[r["段落"]]["n"] += r["台词字数"]
    for seg in SEG_ORDER:
        a = agg.get(seg, {"dur": 0, "n": 0})
        budget = round(SEG_BUDGET[seg] * target / 60.0)
        dev = a["dur"] - budget
        share.append({"段落": seg, "实际时长s": a["dur"], "预算s(等比)": budget,
                      "偏差": f"{dev:+g}s", "台词字数": a["n"],
                      "判定": "✅" if abs(dev) <= max(3, budget * 0.1) else "🔴"})

    xlsx = at.write_excel(
        os.path.join(outdir, "脚本结构校验表.xlsx"),
        {"校验汇总": summary, "逐段校验": rows, "段落预算": share,
         "平台核对": [plat_row]},
        highlights={"逐段校验": {"判定": "contains:🔴"},
                    "段落预算": {"判定": "contains:🔴"},
                    "校验汇总": {"内容": "contains:🔴"}},
        widths={"逐段校验": {"台词": 26, "说明": 40}})
    png = at.bar_chart(
        os.path.join(outdir, "段落字数分布.png"),
        [s["段落"] for s in share],
        [s["台词字数"] for s in share],
        title=f"四段台词字数（全文 {total_chars} 字 / 目标 {int(target*4)}-{int(target*5)}）",
        ylabel="字")
    verdict = summary[-1]["内容"] if issues else "通过"
    verdict = "打回重改" if any("🔴" in i for i in issues) else ("需微调" if issues else "通过")
    js = at.write_json({"verdict": verdict, "total_s": total, "total_chars": total_chars,
                        "rows": rows, "share": share, "issues": issues,
                        "platform_check": plat_row, "generated_at": at.stamp(),
                        "note": "字数由脚本按汉字实数（标点不计）；语境判断与改稿由模型按 prompt.txt 完成"},
                       os.path.join(outdir, "topic_flow.json"))
    print(f"校验完成 —— {verdict}（合计 {total}s / {total_chars} 字，问题 {len(issues)} 项）")
    files = [xlsx, png, js]
    for f in files:
        print(" 产物:", f)
    at.emit({"verdict": verdict, "issues": issues, "files": files})
    return files


def main():
    ap = argparse.ArgumentParser(description="选题转脚本工作流 —— 四段结构确定性校验")
    ap.add_argument("--input", help="输入 JSON（topic/duration_s/platform/hook/segments）")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    payload = DEMO if a.demo else (at.read_json(a.input) if a.input else ap.error("需要 --input 或 --demo"))
    build(payload, a.outdir)


if __name__ == "__main__":
    main()
