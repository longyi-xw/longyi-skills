#!/usr/bin/env python3
"""把报告数据 JSON 注入 HTML 模板，并在注入前做结构校验与措辞检查。

用法：
    python build_report.py data.json -o report.html          # 校验 + 生成
    python build_report.py data.json --check                 # 只校验不生成
    python build_report.py data.json -o report.html --strict # 有告警也视为失败

退出码：0 通过；1 有错误（未生成）；2 --strict 下存在告警。
只依赖 Python 3.8+ 标准库。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = SKILL_DIR / "assets" / "report-template.html"
DATA_BLOCK = re.compile(
    r'(<script type="application/json" id="report-data">)(.*?)(</script>)', re.S
)
TITLE_TAG = re.compile(r"<title>.*?</title>", re.S)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REF_RE = re.compile(r"\[\[([A-Za-z0-9_.-]+)\]\]")

CATEGORIES = {
    "货币政策", "财政政策", "产业与监管", "发展战略", "经济数据", "金融市场",
    "贸易与制裁", "大宗商品与能源", "地缘政治", "自然灾害", "企业与行业", "其他",
}
VERIFICATION = {"official", "multi", "single"}
SOURCE_TYPES = {"official", "wire", "media", "data", "research", "other"}
DIRECTIONS = {"risk-on", "risk-off", "neutral", "mixed"}
LEVELS = {"高", "中", "低"}

# 新闻区（事实陈述）不应出现的情绪化 / 评价性 / 推断性措辞。命中只告警，由撰写者判断是否属于引语。
NEWS_SUBJECTIVE = [
    "暴跌", "暴涨", "狂飙", "狂泻", "崩盘", "血洗", "腰斩", "跳水", "闪崩", "井喷", "大涨特涨",
    "重磅", "炸裂", "震撼", "惊人", "惊呆", "疯狂", "史诗级", "里程碑式", "历史性利好",
    "利好", "利空", "好消息", "坏消息", "令人担忧", "令人振奋", "不幸的是", "可喜",
    "显然", "毫无疑问", "无疑", "必将", "势必", "注定", "意味着", "说明了", "标志着",
    "我们认为", "笔者认为", "值得肯定", "遗憾的是", "终于", "竟然", "居然",
]
# 分析区不应出现的投资建议 / 收益承诺类措辞。
ANALYSIS_ADVICE = [
    "建议买入", "建议卖出", "建议增持", "建议减持", "建议持有", "建议配置",
    "买入评级", "卖出评级", "目标价", "推荐买入", "推荐关注", "强烈推荐",
    "加仓", "减仓", "满仓", "清仓", "重仓", "轻仓", "抄底", "逃顶", "追高", "梭哈", "all in",
    "止盈", "必涨", "必跌", "稳赚", "保本", "翻倍", "躺赚", "闭眼买", "上车", "下车",
    "仓位配置为", "配置比例",
]


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def parse_day(s, where: str, rep: Report):
    if not isinstance(s, str) or not DATE_RE.match(s):
        rep.err(f"{where}：日期须为 YYYY-MM-DD，实际为 {s!r}")
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        rep.err(f"{where}：无效日期 {s!r}")
        return None


def walk_text(node, path: str):
    """遍历 JSON 中所有字符串，产出 (路径, 文本)。"""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_text(v, f"{path}[{i}]")
    elif isinstance(node, dict):
        for k, v in node.items():
            if k in {"id", "url", "sources", "refs", "date", "type", "verification", "direction"}:
                continue
            yield from walk_text(v, f"{path}.{k}")


def lint_words(node, path: str, words: list[str], kind: str, rep: Report) -> None:
    for p, text in walk_text(node, path):
        low = text.lower()
        hits = [w for w in words if w in low]
        if hits:
            rep.warn(f"{p}：{kind}「{'、'.join(hits)}」→ {text[:60]}{'…' if len(text) > 60 else ''}")


def validate(d: dict, rep: Report) -> None:
    if not isinstance(d, dict):
        rep.err("顶层必须是 JSON 对象")
        return

    # ---------- meta ----------
    meta = d.get("meta") or {}
    if meta.get("demo"):
        rep.err("meta.demo 为 true：这是模板示例数据，正式报告请删除该字段或设为 false")
    if not meta.get("title"):
        rep.err("缺少 meta.title")
    period = meta.get("period") or {}
    start = parse_day(period.get("start"), "meta.period.start", rep)
    end = parse_day(period.get("end"), "meta.period.end", rep)
    if start and end and start > end:
        rep.err(f"meta.period：start {start} 晚于 end {end}")
    days = set()
    for i, s in enumerate(as_list(period.get("days"))):
        dd = parse_day(s, f"meta.period.days[{i}]", rep)
        if dd:
            days.add(dd)
    if meta.get("colorConvention") not in (None, "cn", "intl"):
        rep.err("meta.colorConvention 只能是 cn 或 intl")

    def in_window(dd: date) -> bool:
        if days:
            return dd in days
        return bool(start and end and start <= dd <= end)

    # ---------- sources ----------
    src_ids: dict[str, int] = {}
    for i, s in enumerate(as_list(d.get("sources"))):
        where = f"sources[{i}]"
        sid = s.get("id")
        if not sid:
            rep.err(f"{where}：缺少 id")
            continue
        if sid in src_ids:
            rep.err(f"{where}：来源 id 重复 {sid!r}")
        src_ids[sid] = 0
        if not s.get("publisher"):
            rep.err(f"{where}（{sid}）：缺少 publisher")
        url = s.get("url")
        if not url:
            rep.warn(f"{where}（{sid}）：缺少 url，读者无法回溯原文")
        elif not re.match(r"^https?://", url):
            rep.err(f"{where}（{sid}）：url 须为 http(s) 链接，实际为 {url!r}")
        if s.get("type") and s["type"] not in SOURCE_TYPES:
            rep.err(f"{where}（{sid}）：type 须为 {sorted(SOURCE_TYPES)} 之一")
        if s.get("date"):
            parse_day(s["date"], f"{where}.date", rep)

    def check_sources(ids, where: str, required: bool) -> None:
        ids = as_list(ids)
        if required and not ids:
            rep.err(f"{where}：没有来源（每条事实必须可回溯）")
        for sid in ids:
            if sid not in src_ids:
                rep.err(f"{where}：引用了不存在的来源 {sid!r}")
            else:
                src_ids[sid] += 1

    # ---------- news / disasters ----------
    item_ids: set[str] = set()

    def check_item(n: dict, where: str, is_disaster: bool) -> None:
        nid = n.get("id")
        if not nid:
            rep.err(f"{where}：缺少 id")
        elif nid in item_ids:
            rep.err(f"{where}：条目 id 重复 {nid!r}")
        else:
            item_ids.add(nid)
        label = f"{where}（{nid}）"
        for key in ("title", "summary", "date"):
            if not n.get(key):
                rep.err(f"{label}：缺少 {key}")
        if not is_disaster:
            if not n.get("region"):
                rep.err(f"{label}：缺少 region")
            cat = n.get("category")
            if not cat:
                rep.err(f"{label}：缺少 category")
            elif cat not in CATEGORIES:
                rep.warn(f"{label}：category「{cat}」不在推荐列表中，将排在筛选器末尾")
        dd = parse_day(n.get("date"), f"{label}.date", rep) if n.get("date") else None
        if dd and (start and end or days) and not in_window(dd) and not n.get("background"):
            rep.warn(f"{label}：事件日期 {dd} 不在统计区间内——若是背景信息请加 \"background\": true，否则可能是旧闻")
        if n.get("background") and dd and in_window(dd):
            rep.warn(f"{label}：标记为背景，但事件日期 {dd} 在统计区间内")
        imp = n.get("importance")
        if imp is not None and imp not in (1, 2, 3):
            rep.err(f"{label}：importance 须为 1、2、3")
        if n.get("verification") and n["verification"] not in VERIFICATION:
            rep.err(f"{label}：verification 须为 {sorted(VERIFICATION)} 之一")
        if n.get("verification") == "multi" and len(as_list(n.get("sources"))) < 2:
            rep.warn(f"{label}：标记为多源交叉，但只引用了 {len(as_list(n.get('sources')))} 个来源")
        check_sources(n.get("sources"), label, required=True)

    news = as_list(d.get("news"))
    if not news:
        rep.err("news 为空：没有任何新闻条目")
    for i, n in enumerate(news):
        check_item(n, f"news[{i}]", False)
    for i, n in enumerate(as_list(d.get("disasters"))):
        check_item(n, f"disasters[{i}]", True)

    # ---------- snapshot ----------
    snap = d.get("snapshot")
    if snap:
        if not snap.get("asOf"):
            rep.warn("snapshot：缺少 asOf（数据截至时间）")
        for gi, g in enumerate(as_list(snap.get("groups"))):
            for ii, it in enumerate(as_list(g.get("items"))):
                where = f"snapshot.groups[{gi}].items[{ii}]（{it.get('name')}）"
                c = it.get("change")
                if c is not None and not isinstance(c, (int, float)):
                    rep.err(f"{where}：change 须为数字（不带 % 与正负号字符串），实际为 {c!r}")
                if it.get("source"):
                    check_sources([it["source"]], where, required=False)

    # ---------- analysis ----------
    a = d.get("analysis") or {}
    for i, g in enumerate(as_list(a.get("signals"))):
        where = f"analysis.signals[{i}]"
        if g.get("direction") and g["direction"] not in DIRECTIONS:
            rep.err(f"{where}：direction 须为 {sorted(DIRECTIONS)} 之一")
        if g.get("strength") not in (None, 1, 2, 3):
            rep.err(f"{where}：strength 须为 1、2、3")
        if not g.get("counterEvidence"):
            rep.warn(f"{where}（{g.get('title')}）：缺少 counterEvidence——每个信号都应给出反向证据或说明“暂未发现”")
        if not as_list(g.get("refs")) and not REF_RE.search(json.dumps(g, ensure_ascii=False)):
            rep.warn(f"{where}（{g.get('title')}）：没有关联任何新闻条目，判断依据无法回溯")
    for key in ("cycles", "signals"):
        for i, c in enumerate(as_list(a.get(key))):
            if c.get("confidence") and c["confidence"] not in LEVELS:
                rep.err(f"analysis.{key}[{i}]：confidence 须为 高/中/低")
    for i, r in enumerate(as_list(a.get("risks"))):
        for k in ("probability", "impact"):
            if r.get(k) and r[k] not in LEVELS:
                rep.err(f"analysis.risks[{i}]：{k} 须为 高/中/低")
    for i, w in enumerate(as_list(a.get("watchlist"))):
        if w.get("date"):
            parse_day(w["date"], f"analysis.watchlist[{i}].date", rep)

    # ---------- 交叉引用 ----------
    def check_refs(node, path: str) -> None:
        for p, text in walk_text(node, path):
            for rid in REF_RE.findall(text):
                if rid not in item_ids:
                    rep.err(f"{p}：[[{rid}]] 指向不存在的条目")

    def check_ref_lists(node, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "refs":
                    for rid in as_list(v):
                        if rid not in item_ids:
                            rep.err(f"{path}.refs：引用了不存在的条目 {rid!r}")
                else:
                    check_ref_lists(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                check_ref_lists(v, f"{path}[{i}]")

    for key in ("highlights", "analysis", "news", "disasters", "method"):
        check_refs(d.get(key), key)
        check_ref_lists(d.get(key), key)

    unused = [k for k, v in src_ids.items() if v == 0]
    if unused:
        rep.warn(f"以下来源未被任何条目引用：{', '.join(unused)}")

    # ---------- 措辞检查 ----------
    for key in ("highlights", "news", "disasters"):
        lint_words(d.get(key), key, NEWS_SUBJECTIVE, "事实区出现主观/情绪化措辞", rep)
    lint_words(d.get("analysis"), "analysis", ANALYSIS_ADVICE, "分析区出现投资建议类措辞", rep)

    if not a:
        rep.warn("缺少 analysis：报告将只有新闻部分")
    if not as_list(d.get("highlights")):
        rep.warn("缺少 highlights：报告开头没有核心要点")


def embed(template: str, d: dict) -> str:
    payload = json.dumps(d, ensure_ascii=False, indent=1)
    # 防止数据中的 < > & 提前结束 <script> 块或触发 HTML 解析
    payload = payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    if not DATA_BLOCK.search(template):
        raise SystemExit("模板中找不到 <script type=\"application/json\" id=\"report-data\"> 数据块")
    out = DATA_BLOCK.sub(lambda m: m.group(1) + "\n" + payload + "\n" + m.group(3), template, count=1)
    title = (d.get("meta") or {}).get("title") or "全球经济新闻总结与市场分析"
    title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return TITLE_TAG.sub(lambda m: f"<title>{title}</title>", out, count=1)


def main() -> int:
    ap = argparse.ArgumentParser(description="校验报告数据并生成 HTML 报告")
    ap.add_argument("data", help="报告数据 JSON 文件")
    ap.add_argument("-o", "--output", help="输出 HTML 路径（默认与数据文件同名 .html）")
    ap.add_argument("-t", "--template", default=str(DEFAULT_TEMPLATE), help="HTML 模板路径")
    ap.add_argument("--check", action="store_true", help="只校验，不生成文件")
    ap.add_argument("--strict", action="store_true", help="存在告警时以退出码 2 结束")
    args = ap.parse_args()

    data_path = Path(args.data)
    try:
        d = json.loads(data_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        print(f"[错误] JSON 解析失败：{e}")
        return 1

    rep = Report()
    validate(d, rep)

    for w in rep.warnings:
        print(f"[告警] {w}")
    for e in rep.errors:
        print(f"[错误] {e}")

    n_news = len(as_list(d.get("news"))) if isinstance(d, dict) else 0
    n_dis = len(as_list(d.get("disasters"))) if isinstance(d, dict) else 0
    n_src = len(as_list(d.get("sources"))) if isinstance(d, dict) else 0
    print(f"新闻 {n_news} 条 · 灾害/突发 {n_dis} 条 · 来源 {n_src} 个 · 错误 {len(rep.errors)} · 告警 {len(rep.warnings)}")

    if rep.errors:
        print("存在错误，未生成报告。")
        return 1
    if not args.check:
        out = Path(args.output) if args.output else data_path.with_suffix(".html")
        template = Path(args.template).read_text(encoding="utf-8")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(embed(template, d), encoding="utf-8", newline="\n")
        print(f"已生成：{out.resolve()}")
    if args.strict and rep.warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
