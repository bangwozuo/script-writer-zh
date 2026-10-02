# -*- coding: utf-8 -*-
"""
分镜与拍摄清单工作流 —— 端到端编排脚本。

流程（与 SKILL.md 的 DAG 一致）：
  S1 script-structure-generate   四段式脚本成稿（模型产出，storyboard 模式）
  S2 本步（脚本承担）            分镜七字段校验：台词字数=时长×语速、时间轴连续、
                                 景别合法、字幕 ≤15 字、时长合计=目标 ±2s
  S3 本步（脚本承担）            拍摄清单汇总：音效清单 / 收音要点 / 待补项
  S4 人工逐镜对稿                 念台词卡秒表

分镜字段（七项缺一不可）：镜头号/景别/时长/画面/台词/字幕/音效。
核心死线：台词字数 = 时长 × 语速，超字数必超时——3s 镜头最多 13-14 字（4.5 字/秒），
任何镜头台词语速 >6 字/秒直接判「念不完」。

用法：
  python run_flow.py --input input.json --outdir out
  python run_flow.py --demo

产物：
  out/分镜拍摄清单.xlsx   逐镜校验 / 拍摄要点 两 sheet
  out/分镜时长分布.png    各镜头时长柱状图
  out/storyboard_flow.json 机器可读结果
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

SCENES = {"特写", "近景", "中景", "全景"}
PLATFORM_MAX = {"抖音": 60, "小红书": 240, "视频号": 60, "B站": 600}
PUNCT = re.compile(
    r"[\uFF0C\u3002\uFF01\uFF1F\uFF1B\uFF1A\u3001\u201C\u201D\u2018\u2019\u300C\u300D"
    r"\u2026\u2014,.:;()()\s~\uFF5E\-\u2014\u00B7]")

DEMO = {
    "title": "副业避坑：新人最容易踩的三个坑",
    "target_duration_s": 60,
    "platform": "抖音",
    "shots": [
        {"shot_no": 1, "scene": "近景", "dur_s": 3, "visual": "对镜头开口，手比「三」",
         "line": "副业第一个月，我踩了三个坑", "subtitle": "我踩了三个坑", "sfx": "whoosh"},
        {"shot_no": 2, "scene": "中景", "dur_s": 6, "visual": "摇头摆手，止住冲动",
         "line": "别急着学人家月入过万。先听我说说我这三个坑是怎么亏的", "subtitle": "先听我怎么亏的", "sfx": "—"},
        {"shot_no": 3, "scene": "近景", "dur_s": 3, "visual": "手指镜头，逐个屈指数",
         "line": "这三个坑，每一个都花过我真金白银", "subtitle": "每一个都花过钱", "sfx": "pop"},
        {"shot_no": 4, "scene": "中景", "dur_s": 4, "visual": "摊手",
         "line": "你要是一个都没踩过，那是老天爷赏饭吃", "subtitle": "—", "sfx": "—"},
        {"shot_no": 5, "scene": "中景", "dur_s": 7, "visual": "切记账本与接单截图",
         "line": "先说结论：新人的钱和力气，多半耗在三个坑上。坑一，低价单接太多",
         "subtitle": "结论：钱耗在三个坑", "sfx": "键盘声"},
        {"shot_no": 6, "scene": "特写", "dur_s": 6, "visual": "接单记录滚动，低价单高亮",
         "line": "我头一个月六成的单是低价单，忙得要死，只贡献两成收入",
         "subtitle": "60% 单量 → 20% 收入", "sfx": "—"},
        {"shot_no": 7, "scene": "近景", "dur_s": 6, "visual": "无奈看手机聊天记录",
         "line": "坑二，没谈改稿次数。有个甲方拖了我整整两周，改了八稿",
         "subtitle": "改了 8 稿", "sfx": "消息提示音"},
        {"shot_no": 8, "scene": "中景", "dur_s": 5, "visual": "对镜头竖三根手指",
         "line": "所以接单前，改稿三次封顶，白纸黑字写进聊天记录", "subtitle": "改稿 3 次封顶", "sfx": "pop"},
        {"shot_no": 9, "scene": "全景", "dur_s": 2, "visual": "扫过吃灰的设备架",
         "line": "坑三，工具买齐了，单没来", "subtitle": "—", "sfx": "—"},
        {"shot_no": 10, "scene": "近景", "dur_s": 4, "visual": "对镜头笃定",
         "line": "设备是干了才配的，不是配好了才开干", "subtitle": "先开干", "sfx": "—"},
        {"shot_no": 11, "scene": "近景", "dur_s": 2, "visual": "停顿看镜头",
         "line": "记住：先跑通，再升级", "subtitle": "先跑通 再升级", "sfx": "金句音效"},
        {"shot_no": 12, "scene": "中景", "dur_s": 6, "visual": "手势下指评论区",
         "line": "这三个坑，你踩过哪个？评论区告诉我，我看看谁最惨", "subtitle": "你踩过哪个？", "sfx": "—"},
        {"shot_no": 13, "scene": "近景", "dur_s": 6, "visual": "指向关注位",
         "line": "下期讲防跑单话术，三句话让定金到账，想看的点个关注", "subtitle": "点关注", "sfx": "whoosh"},
    ],
}


def _hanzi(s: str) -> int:
    return len(PUNCT.sub("", s or ""))


def check(shots, target, platform):
    rows, issues = [], []
    cursor = 0
    for shot in shots:
        no = shot.get("shot_no", "")
        scene = shot.get("scene", "")
        dur = shot.get("dur_s", 0)
        visual = shot.get("visual", "")
        line = shot.get("line", "")
        subtitle = shot.get("subtitle", "")
        sfx = shot.get("sfx", "")
        start, end = cursor, cursor + dur
        cursor = end

        problems = []
        if scene not in SCENES:
            problems.append(f"景别「{scene}」非法（特写/近景/中景/全景）")
        if not visual:
            problems.append("画面缺失——写不出画面的镜头不可拍")
        if subtitle not in ("", "—") and _hanzi(subtitle) > 15:
            problems.append(f"字幕超 15 字符（{len(subtitle)}），一屏放不下")
        n = _hanzi(line)
        if n == 0:
            speed, verdict, note = "—", "🟡", "无台词：确认是否纯 B-roll（纯画面镜头要标记）"
        else:
            speed = round(n / dur, 2) if dur else 999
            if speed > 6.0:
                verdict = "🔴"
                note = f"语速 {speed} 字/秒念不完：{dur}s 最多 {int(dur*6)} 字，删约 {int(n - dur*6)} 字"
            elif speed < 3.5:
                verdict = "🟡"
                note = f"语速 {speed} 字/秒过稀：台词与时长不匹配，补台词或缩时长"
            else:
                verdict, note = "✅", f"语速 {speed} 字/秒"
        if problems:
            verdict = "🔴"
            note = ("；".join(problems) + "；" + note) if note else "；".join(problems)
        rows.append({"镜头号": no, "景别": scene, "时间轴": f"{start}-{end}s",
                     "时长s": dur, "台词字数": n, "语速": speed,
                     "字幕": subtitle if subtitle else "—", "音效": sfx if sfx else "—",
                     "画面": visual[:18], "判定": verdict, "说明": note})
        if verdict in ("🔴", "🟡"):
            issues.append(f"镜头 {no}（{start}-{end}s）：{note}")

    total = cursor
    if abs(total - target) > 2:
        issues.append(f"分镜时长合计 {total}s ≠ 目标 {target}s（允许 ±2s）")
    # 时间轴连续性（cursor 递增已保证无重叠，检查跳秒）
    if shots:
        expect = sum(s.get("dur_s", 0) for s in shots)
        if expect != total:
            issues.append(f"存在无效时长字段：合计 {expect}s ≠ 累计 {total}s")

    plat_row = {"平台": platform, "时长上限": "待核对官方", "判定": "🔵",
                "说明": "不在常量表，发布前查官方"}
    mx = PLATFORM_MAX.get(platform)
    if mx is not None:
        ok = total <= mx
        plat_row = {"平台": platform, "时长上限": f"{mx}s", "判定": "✅" if ok else "🔴",
                    "说明": f"{total}s 成片" + ("" if ok else f" 超上限 {total-mx}s，需剪短重排")}
        if not ok:
            issues.append(f"{platform}：{plat_row['说明']}")
    return total, rows, issues, plat_row


def build(payload, outdir):
    shots = payload.get("shots") or []
    if not shots:
        raise SystemExit("[错误] shots 为空：需要七字段分镜表（shot_no/scene/dur_s/visual/line/subtitle/sfx）")
    target = payload.get("target_duration_s", 60)
    platform = payload.get("platform", "抖音")
    total, rows, issues, plat_row = check(shots, target, platform)

    at.ensure_outdir(outdir)
    verdict = "打回重改" if any("🔴" in i for i in issues) else ("需微调" if issues else "通过")
    summary = [
        {"项": "片名", "内容": payload.get("title", "（未填）")},
        {"项": "镜头数 / 成片时长", "内容": f"{len(shots)} 镜 / {total}s（目标 {target}s）"},
        {"项": "平台", "内容": platform},
        {"项": "整体判定", "内容": verdict},
    ] + [{"项": f"问题{i+1}", "内容": it} for i, it in enumerate(issues)]

    # 拍摄要点：音效清单 / 纯画面镜头 / 待补项
    sfx_list = sorted({r["音效"] for r in rows if r["音效"] not in ("—", "")})
    broll = [str(r["镜头号"]) for r in rows if r["台词字数"] == 0]
    todo = [it for it in issues if it.startswith("镜头")]
    shooting = [
        {"要点": "音效清单", "内容": "、".join(sfx_list) if sfx_list else "（无音效需求）"},
        {"要点": "纯画面镜头", "内容": f"镜头 {'、'.join(broll)}（B-roll，无台词）" if broll else "（无）"},
        {"要点": "收音要点", "内容": "口播镜头用领夹麦；环境音单独收一条底，后期垫回"},
        {"要点": "大数字镜头", "内容": "含数字的台词留 1-2s 余量（人工对稿卡秒表）"},
        {"要点": "待修问题数", "内容": f"{len(todo)} 镜（详见逐镜校验 🔴/🟡）"},
    ]

    xlsx = at.write_excel(
        os.path.join(outdir, "分镜拍摄清单.xlsx"),
        {"校验汇总": summary, "逐镜校验": rows, "拍摄要点": shooting, "平台核对": [plat_row]},
        highlights={"逐镜校验": {"判定": "contains:🔴"},
                    "校验汇总": {"内容": "contains:🔴"}},
        widths={"逐镜校验": {"画面": 26, "说明": 38}})
    png = at.bar_chart(
        os.path.join(outdir, "分镜时长分布.png"),
        [f"镜头{r['镜头号']}" for r in rows],
        [r["时长s"] for r in rows],
        title=f"各镜头时长（合计 {total}s / 目标 {target}s）", ylabel="秒")
    js = at.write_json({"verdict": verdict, "total_s": total, "rows": rows,
                        "shooting": shooting, "issues": issues,
                        "platform_check": plat_row, "generated_at": at.stamp(),
                        "note": "台词字数由脚本按汉字实数（标点不计）；画面具体化与改稿由模型按 prompt.txt 复核"},
                       os.path.join(outdir, "storyboard_flow.json"))
    print(f"分镜校验 —— {verdict}（{len(shots)} 镜 / {total}s，问题 {len(issues)} 项）")
    files = [xlsx, png, js]
    for f in files:
        print(" 产物:", f)
    at.emit({"verdict": verdict, "issues": issues, "files": files})
    return files


def main():
    ap = argparse.ArgumentParser(description="分镜与拍摄清单工作流 —— 七字段校验")
    ap.add_argument("--input", help="输入 JSON（title/target_duration_s/platform/shots）")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    payload = DEMO if a.demo else (at.read_json(a.input) if a.input else ap.error("需要 --input 或 --demo"))
    build(payload, a.outdir)


if __name__ == "__main__":
    main()
