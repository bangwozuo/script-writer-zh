# -*- coding: utf-8 -*-
"""
人设语气库 —— 从历史稿件样本统计语气画像与改写约束。

职责边界：本脚本只做**可量化的风格统计与产物生成**（句长分布、语气词密度、
人称习惯、口头禅候选 n-gram 频次是机器的强项）。把候选口头禅判断成「人设梗」
还是「偶然重复」、生成改写约束的措辞由模型按 prompt.txt 完成。

统计口径（全部量化）：
  S1 句长习惯     平均句长 / CV / 短句占比（口播稿按句号分句、标点不计）
  S2 语气词密度   吧/呢/哈/啊/呗/嘛/啦/哟 每百字个数（人设感指标，2-4 最佳）
  S3 人称习惯     我/你/咱们/咱/家人们/兄弟们/姐妹们 每千字频次
  S4 句式习惯     疑问句占比 / 感叹句占比
  S5 口头禅候选   2-3 字高频片段（过滤停用片段，频次 ≥2 才入围）

样本量要求：≥3 篇且合计 ≥800 字才有统计意义；不足时输出「样本不足清单」。

用法：
  python voice_profile.py --input input.json --outdir out
  python voice_profile.py --demo

产物：
  out/语气画像.xlsx       画像汇总 / 逐篇统计 / 口头禅候选 / 改写约束 4 sheet
  out/逐篇句长分布.png    各篇平均句长 vs 整体
  out/voice_profile.json  机器可读画像
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter

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

SENT_SPLIT = re.compile(r"[。！？；!?;]")
PUNCT = re.compile(
    r"[\uFF0C\u3002\uFF01\uFF1F\uFF1B\uFF1A\u3001\u201C\u201D\u2018\u2019\u300C\u300D"
    r"\u2026\u2014,.:;()\uFF08\uFF09\s~\uFF5E\-\u2014\u00B7]")

TONE_WORDS = ["吧", "呢", "哈", "啊", "呗", "嘛", "啦", "哟", "哦", "呀"]
PERSON_WORDS = ["我", "你", "咱们", "咱", "家人们", "兄弟们", "姐妹们", "宝子们",
                "老铁", "各位"]

# 口头禅候选的停用片段（2-3 字高频但无风格信息）
STOP_GRAMS = set(
    "我们|你们|他们|自己|可以|这个|那个|就是|所以|但是|因为|如果|现在|这样|那样|"
    "什么|没有|还是|已经|而且|不是|真的|可能|觉得|知道|开始|最后|这么|那么|为什么|"
    "怎么样|大家|一样|时候|今天|明天|昨天|东西|地方|问题|方法|其实|应该|必须|一下|"
    "一些|一点|非常|直接|进行|通过|一个|不然|要不|第一|第二|第三|来看看|的话|这个|"
    "咱们算|你自己|算笔账|什么是|为什么|怎么样|评论区|平台|要不|还是说".split("|"))

DEMO = {
    "creator": "阿栋聊副业",
    "samples": [
        {"title": "第12期：下班摊摊卖柠檬茶", "text": (
            "家人们，咋就是说，下班搞副业没那么玄。我第一个月摊摊卖柠檬茶。"
            "毛利四千二，落袋三千八。你别一上来就问我赚不赚。先问问自己，"
            "能不能站四个小时。咋们算笔账啊。一杯成本三块二，卖十块。"
            "一晚上六十杯。你自己算。但冰块是隐形成本。一袋冰八块。"
            "天热化得快，下午备的冰撑不到收摊。城管这块你别侥幸。"
            "我吃了两百块罚单才长记性。现在固定在夜市交摊位费，一天三十。"
            "心疼，但是踏实。哪行不是这样呢？看着热闹，干着腰疼。"
            "收摊回家还要洗桶切柠檬。第二天六点半起床。真的靠意志力。"
            "上上周我算过一笔账，摆摊的时薪刨掉通勤和备料，其实就二十六块。"
            "想入行的，评论区扣个1。我把避坑清单发你。在哪进货、怎么定价，"
            "全在里面。咋就是说，副业的第一桶金，都是辛苦钱。")},
        {"title": "第13期：闲鱼卖二手的三个坑", "text": (
            "兄弟们，闲鱼卖二手，三个坑你别踩。第一坑，验货宝免不开。"
            "二十块起收。你就当买平安。不然扯皮扯到你怀疑人生。"
            "第二坑呢，物流砸价。寄之前拍视频。六个面都得拍清楚。"
            "磨破了嘴也得拍。不然对方说本来就花了。你哭都没地方哭。"
            "第三个，低价单别接。三十块的包裹。包装加运费就去掉十二。"
            "白忙活一晚上。所以接单前先算包装加运费，算完还不赚的直接拒。"
            "咱就是说，闲鱼赚的是辛苦钱。想躺赚的，出门左转。"
            "还有个隐藏坑。代发地址别写家里。用驿站中转，安全第一。"
            "别问我为什么知道这些，问就是都交过学费。"
            "问题来了。你们卖过最离谱的东西是啥？我先说。我卖过一台"
            "用了一年的足浴盆。买家愣是让我保三个月。离谱吧？"
            "评论区聊聊呗。让我看看还有谁比我惨。")},
        {"title": "第14期：接单平台抽成对比", "text": (
            "姐妹们，接单平台抽成我替你们试了一遍。三个月，六十多单。"
            "数据都在这了。A平台抽百分之十。结款快，T加三到账。"
            "但是单子少，得自己抢。B平台不抽成。可是你得防跑单。"
            "我上个月被跑了两单。八百块，打水漂。所以B平台的规矩是，"
            "四成定金不到账就不动手，这规矩救过我好几次。C平台抽百分之五。"
            "单子多，但是审核严。图片不清晰直接拒。咋就是说，"
            "没有完美的平台。只有合不合适。手艺硬就走B。想省心就选A。"
            "走量的话，C合适。对了，签合同记得写改稿次数。三次封顶。"
            "我见过最夸张的甲方，一张封面改了十一稿，最后又改回第一稿。"
            "不然遇到无限改的甲方，你会怀疑人生。行吧，今天就啰到这儿。"
            "下期教你们防跑单话术。三句话把定金谈下来。想要的，"
            "评论区蹲一个。咋就是说，蹲到了就是缘分。")},
    ],
}


def _hanzi(s: str) -> int:
    return len(PUNCT.sub("", s or ""))


def _sentences(text: str):
    return [s for s in SENT_SPLIT.split(text or "") if _hanzi(s) > 0]


def sample_stats(sample):
    text = sample.get("text", "")
    sents = _sentences(text)
    lens = [_hanzi(s) for s in sents]
    n_chars = _hanzi(text)
    n = len(sents)
    mu = sum(lens) / n if n else 0.0
    sigma = (sum((x - mu) ** 2 for x in lens) / n) ** 0.5 if n else 0.0
    cv = sigma / mu if mu else 0.0
    short_ratio = (sum(1 for L in lens if L <= 8) / n) if n else 0.0

    tone = sum(text.count(w) for w in TONE_WORDS)
    tone_density = tone / n_chars * 100 if n_chars else 0.0
    person = sum(text.count(w) for w in PERSON_WORDS)
    person_density = person / n_chars * 1000 if n_chars else 0.0

    # 疑问/感叹句以全文句尾标点计数（分句会吞掉结尾标点，不能用分句结果判断）
    q = text.count("？") + text.count("?")
    ex = text.count("！") + text.count("!")

    return {
        "篇名": sample.get("title", ""),
        "字数": n_chars,
        "句数": n,
        "平均句长": round(mu, 1),
        "句长CV": round(cv, 2),
        "短句占比(≤8字)": f"{short_ratio:.0%}",
        "语气词/百字": round(tone_density, 1),
        "人称词/千字": round(person_density, 0),
        "疑问句占比": f"{q / n:.0%}" if n else "—",
        "感叹句占比": f"{ex / n:.0%}" if n else "—",
    }, lens


def gram_candidates(samples, top=10):
    """2-3 字高频片段：频次 ≥2 且至少跨 2 篇出现，过滤停用片段。

    口头禅的定义是「跨稿复现的个人语言习惯」，只在单篇出现的重复不算。
    """
    cnt = Counter()          # 片段 -> 总频次
    df = {}                  # 片段 -> 出现过的篇索引集合
    for si, sample in enumerate(samples):
        text = PUNCT.sub(" ", sample.get("text", ""))
        text = re.sub(r"\s", "", text)
        text = re.sub(r"\d+", "", text)
        for size in (3, 2):  # 3 字优先，避免把「咱就是说」拆成「咱就」「是说」
            for i in range(len(text) - size + 1):
                g = text[i:i + size]
                if g in STOP_GRAMS:
                    continue
                cnt[g] += 1
                df.setdefault(g, set()).add(si)  # set 自动按篇去重
    out = []
    items = [(g, c) for g, c in cnt.items() if c >= 2 and len(df.get(g, ())) >= 2]
    items.sort(key=lambda x: (-len(df[x[0]]), -x[1]))
    for g, c in items:
        if any(g in o["口头禅候选"] for o in out):
            continue
        out.append({"口头禅候选": g, "频次": c, "出现篇数": len(df[g])})
        if len(out) >= top:
            break
    return out


def build(payload, outdir):
    samples = payload.get("samples") or []
    if len(samples) < 3:
        raise SystemExit(
            "[错误] 样本不足 3 篇，语气画像不稳定。请提供至少 3 篇历史稿件"
            "（合计 ≥800 字），缺失清单：" + str(3 - len(samples)) + " 篇")

    per_sample, all_lens = [], []
    for s in samples:
        st, lens = sample_stats(s)
        per_sample.append(st)
        all_lens += lens

    total_chars = sum(r["字数"] for r in per_sample)
    if total_chars < 800:
        print(f"[警告] 样本合计 {total_chars} 字 < 800 字，画像仅供参考，"
              f"建议再补 {(800 - total_chars + 99) // 100} 百字样本")

    mu = sum(all_lens) / len(all_lens)
    sigma = (sum((x - mu) ** 2 for x in all_lens) / len(all_lens)) ** 0.5
    cv = sigma / mu if mu else 0.0
    avg_tone = sum(r["语气词/百字"] for r in per_sample) / len(per_sample)
    avg_person = sum(r["人称词/千字"] for r in per_sample) / len(per_sample)
    grams = gram_candidates(samples)

    # 改写约束：由统计值反推，供口语化改写（colloquial-rewrite）调用
    tone_lo, tone_hi = 2.0, 4.0
    constraints = [
        {"约束项": "平均句长", "目标值": f"{max(6, round(mu - 2))}-{min(16, round(mu + 2))} 字",
         "依据": f"样本均值 {mu:.1f} 字 ±2"},
        {"约束项": "句长变异系数 CV", "目标值": f"≥ {max(0.5, round(cv - 0.05, 2))}",
         "依据": f"样本 CV {cv:.2f}，保持长短句交错的个人节奏"},
        {"约束项": "语气词密度", "目标值": f"{tone_lo}-{tone_hi} 个/百字",
         "依据": f"样本均值 {avg_tone:.1f}；<2 生硬、>4 油腻"},
        {"约束项": "人称习惯", "目标值": "高频人称词按样本沿用（见口头禅候选表）",
         "依据": f"样本人称密度 {avg_person:.0f} 个/千字"},
        {"约束项": "口头禅", "目标值": "每篇 ≤4 次，防油腻",
         "依据": "候选来自 n-gram 频次统计，需人工确认是否人设梗"},
        {"约束项": "句式", "目标值": "每篇至少 1 个提问式结尾 + 2-3 个感叹句",
         "依据": "样本疑问/感叹句占比见逐篇统计"},
    ]

    at.ensure_outdir(outdir)
    profile_rows = [
        {"画像项": "创作者", "值": payload.get("creator", "（未命名）")},
        {"画像项": "样本量", "值": f"{len(samples)} 篇 / {total_chars} 字"},
        {"画像项": "平均句长", "值": f"{mu:.1f} 字"},
        {"画像项": "句长 CV", "值": f"{cv:.2f}（≥0.5 节奏感强）"},
        {"画像项": "语气词密度", "值": f"{avg_tone:.1f} 个/百字（目标区间 2-4）"},
        {"画像项": "人称词密度", "值": f"{avg_person:.0f} 个/千字"},
        {"画像项": "口头禅候选", "值": "、".join(g["口头禅候选"] for g in grams[:6])},
    ]
    xlsx = at.write_excel(
        os.path.join(outdir, "语气画像.xlsx"),
        {
            "画像汇总": profile_rows,
            "逐篇统计": per_sample,
            "口头禅候选": grams or [{"口头禅候选": "（频次≥2 的候选不足）", "频次": ""}],
            "改写约束": constraints,
        },
        highlights={"逐篇统计": {"语气词/百字": ">4"},
                    "口头禅候选": {"频次": ">=4"}},
        widths={"逐篇统计": {"篇名": 26}, "改写约束": {"依据": 40, "目标值": 30}},
    )
    png = at.bar_chart(
        os.path.join(outdir, "逐篇句长分布.png"),
        [r["篇名"] or f"样本{i+1}" for i, r in enumerate(per_sample)],
        [r["平均句长"] for r in per_sample],
        title=f"各篇平均句长（整体 {mu:.1f} 字 / CV {cv:.2f}）", ylabel="字")
    js = at.write_json({
        "creator": payload.get("creator", ""), "profile": profile_rows,
        "per_sample": per_sample, "gram_candidates": grams,
        "constraints": constraints, "generated_at": at.stamp(),
        "note": "口头禅候选为 n-gram 统计结果，是否人设梗由模型/人工按 prompt.txt 确认",
    }, os.path.join(outdir, "voice_profile.json"))

    print(f"画像完成：{len(samples)} 篇 / {total_chars} 字，平均句长 {mu:.1f}，"
          f"CV {cv:.2f}，口头禅候选 {len(grams)} 个")
    for f in (xlsx, png, js):
        print(" 产物:", f)
    at.emit({"profile": profile_rows, "constraints": constraints, "files": [xlsx, png, js]})


def main():
    ap = argparse.ArgumentParser(description="人设语气库 —— 语气画像统计")
    ap.add_argument("--input", help="输入 JSON（creator/samples[{title,text}]）")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    payload = DEMO if a.demo else (at.read_json(a.input) if a.input else ap.error("需要 --input 或 --demo"))
    build(payload, a.outdir)


if __name__ == "__main__":
    main()
