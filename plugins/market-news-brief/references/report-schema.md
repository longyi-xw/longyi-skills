# 报告数据规范

HTML 模板 `assets/report-template.html` 由一份 JSON 驱动。按本文件编写数据，再用 `scripts/build_report.py` 校验并注入。模板里自带的示例数据（`meta.demo: true`）展示了所有字段的完整用法，可以对照着看。

## 通用约定

- 编码 UTF-8，日期统一用 `YYYY-MM-DD`。
- **可选模块缺省即隐藏**：没有 `snapshot` 就不显示市场快照，以此类推。`disasters` 例外：给空数组 `[]` 会显示“本期未检索到……”，完全省略则整个模块隐藏。
- **文本里支持两种标记**，其余一律按纯文本显示（不解析 HTML）：
  - `**加粗**`
  - `[[条目id]]`：渲染成可点击的引用角标，指向 `news` 或 `disasters` 中的条目
- `refs` 字段是条目 id 数组，渲染为角标，效果同 `[[id]]`。
- `sources` 字段是来源 id 数组，指向顶层 `sources`。
- 条目 id 建议用有含义的短名，如 `us-fomc`、`cn-cpi-sep`，不要用中文或空格。

## 顶层结构

```json
{
  "meta": {},
  "highlights": [],
  "snapshot": {},
  "news": [],
  "disasters": [],
  "disastersNote": "",
  "analysis": {},
  "method": {},
  "sources": [],
  "disclaimer": ""
}
```

必填：`meta`、`news`、`sources`。其余可选，但一份完整报告应该都有。

## meta

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | 字符串，必填 | 报告标题，如“全球经济新闻周报” |
| `subtitle` | 字符串 | 副标题 |
| `kicker` | 字符串 | 标题上方的小字，默认“新闻总结 · 市场分析” |
| `period.start` / `period.end` | 日期，必填 | 统计区间，含首尾 |
| `period.days` | 日期数组 | 离散日期，如用户只要 10/1、10/3、10/5 三天；有值时优先于 start/end 判断条目是否在窗口内 |
| `period.label` | 字符串 | 用户口径的描述，如“近 7 天”“国庆假期” |
| `generatedAt` | 字符串 | 生成时间，如 `2026-10-08 09:30` |
| `timezone` | 字符串 | 如 `UTC+8` |
| `regions` | 字符串数组 | 覆盖的地区，同时决定新闻按地区分组时的顺序 |
| `colorConvention` | `cn` 或 `intl` | 涨跌配色：`cn` 红涨绿跌（默认），`intl` 绿涨红跌 |
| `demo` | 布尔 | 仅模板示例使用；正式报告不要出现，脚本见到 `true` 会报错 |

## highlights（核心要点）

```json
[{ "text": "美联储宣布将联邦基金利率目标区间下调 25 个基点至 X%–Y%。", "refs": ["us-fomc"] }]
```

也可以直接写字符串数组。4–8 条，只写事实。

## snapshot（市场快照）

```json
{
  "asOf": "2026-10-07 收盘",
  "note": "变动为区间最后一个交易日收盘相对区间开始前最后一个交易日收盘；A 股 10/1–10/7 休市。",
  "groups": [
    {
      "name": "股票指数",
      "items": [
        { "name": "标普 500", "value": "5,812.34", "change": 1.25, "unit": "%", "source": "s3" },
        { "name": "美国 10 年期国债收益率", "value": "4.12%", "change": -8, "unit": "bp" }
      ]
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `value` | 字符串，按想要的格式写好（千分位、货币符号、百分号） |
| `change` | **数字**，带正负，不带单位；拿不到就省略，显示为“—” |
| `unit` | `%`（默认）、`bp`、`pt` 等 |
| `decimals` | 小数位数，默认 `%` 为 2、`bp` 为 0 |
| `note` | 备注，如“休市”“口径为中间价” |
| `source` | 单个来源 id |

同一组内的幅度条按组内最大绝对值等比例绘制，所以单位不同的品种（% 与 bp）放在不同的组里。

## news（新闻条目）

```json
{
  "id": "us-fomc",
  "date": "2026-10-07",
  "region": "美国",
  "category": "货币政策",
  "importance": 3,
  "verification": "official",
  "title": "美联储下调联邦基金利率 25 个基点",
  "summary": "美联储联邦公开市场委员会宣布将联邦基金利率目标区间下调 25 个基点至 X%–Y%……",
  "keyPoints": ["投票结果 10:2，两名委员主张维持不变", "点阵图中值显示年内还将降息 1 次"],
  "figures": [{ "label": "目标区间", "value": "X%–Y%" }],
  "sources": ["s1", "s2"]
}
```

| 字段 | 说明 |
|------|------|
| `id` | 必填，全报告唯一 |
| `date` | 必填，事件发生日期（不是报道日期） |
| `region` | 必填，与 `meta.regions` 用词一致；跨国事件用“全球” |
| `category` | 必填，推荐取值：货币政策、财政政策、产业与监管、发展战略、经济数据、金融市场、贸易与制裁、大宗商品与能源、地缘政治、自然灾害、企业与行业、其他 |
| `importance` | 1–3，标准见 SKILL.md 第 4 步 |
| `verification` | `official` 官方来源、`multi` 多源交叉（至少 2 个来源）、`single` 单一来源 |
| `title` | 必填，一句话事实标题，不带情绪词 |
| `summary` | 必填，1–3 句 |
| `keyPoints` | 字符串数组，补充细节 |
| `figures` | 2–4 个关键数字 |
| `sources` | 必填，来源 id 数组 |
| `background` | 布尔。事件发生在窗口之外、但理解本期事件必须知道的背景（如上月的加息决定），设为 `true`；卡片会显示“背景 · 窗口外”，脚本不再告警。背景条目宜少，只放分析要引用的 |

## disasters（自然灾害与突发事件）

```json
{
  "id": "tw-quake",
  "date": "2026-10-03",
  "type": "地震",
  "location": "某地",
  "importance": 2,
  "verification": "multi",
  "title": "某地发生 M7.0 地震",
  "summary": "当地时间 10 月 3 日……",
  "impacts": [{ "label": "人员伤亡", "value": "……（据当地政府通报）" }, { "label": "生产", "value": "……" }],
  "sectors": ["半导体", "航运"],
  "marketObservations": "次一交易日，当地半导体板块指数收跌 X%（据某某报道）。",
  "sources": ["s7", "s8"]
}
```

`marketObservations` 只写**已经观察到**的市场反应；后续影响的推测放到 `analysis.signals`。窗口内没有符合收录标准的灾害时，写 `"disasters": []`，可选用 `disastersNote` 自定义提示语。

## analysis（市场分析）

```json
{
  "overview": ["段落一，可用 [[us-fomc]] 引用", "段落二"],
  "state": [{ "label": "风险偏好", "value": "边际回落", "note": "依据：……", "refs": ["us-fomc"] }],
  "cycles": [{
    "economy": "美国", "growth": "放缓", "inflation": "回落", "monetary": "宽松周期", "fiscal": "扩张",
    "phase": "增长放缓、通胀回落", "evidence": "非农低于预期 [[us-nfp]]", "refs": [], "confidence": "中"
  }],
  "signals": [{
    "title": "美联储前瞻指引措辞变化", "category": "政策信号",
    "direction": "risk-on", "strength": 2, "confidence": "中",
    "observation": "……", "interpretation": "……", "counterEvidence": "……", "refs": ["us-fomc"]
  }],
  "scenarios": [{
    "name": "基准情景", "likelihood": "相对较高", "description": "……",
    "triggers": ["……"], "watch": ["……"]
  }],
  "risks": [{ "risk": "……", "probability": "中", "impact": "高", "description": "……", "refs": ["us-fomc"] }],
  "strategies": [{ "condition": "适用的环境特征", "approach": "风险管理思路" }],
  "watchlist": [{ "date": "2026-10-15", "region": "美国", "event": "9 月 CPI 发布", "why": "检验通胀回落趋势" }]
}
```

| 字段 | 取值约束 |
|------|---------|
| `signals[].direction` | `risk-on` / `risk-off` / `mixed` / `neutral` |
| `signals[].strength` | 1–3 |
| `confidence`、`probability`、`impact` | `高` / `中` / `低` |
| `scenarios[].likelihood` | 定性词，如“相对较高”“中等”“较低” |
| `watchlist[].date` | 日期；日期未定时省略，显示为“待定” |

## method（方法说明）

```json
{
  "window": "2026-10-01 至 2026-10-07（含首尾），按 UTC+8 计",
  "scope": "美国、中国、俄罗斯、欧元区、日本、英国、印度及全球性事件",
  "searchCount": 32,
  "notes": ["关键数据以官方发布为准，或经两个独立来源核对"],
  "limitations": ["俄罗斯 9 月部分经济数据尚未发布", "印度窗口内未检索到重要动态"]
}
```

`limitations` 要如实写：哪些经济体没查到重要动态、哪些数据拿不到、哪些条目只有单一来源。

## sources（来源）

```json
{ "id": "s1", "publisher": "美联储", "title": "FOMC 声明", "url": "https://www.federalreserve.gov/...", "date": "2026-10-07", "type": "official" }
```

| 字段 | 说明 |
|------|------|
| `id` | 必填，唯一 |
| `publisher` | 必填，媒体或机构名 |
| `title` | 原文标题 |
| `url` | 原文链接，必须是 http(s) |
| `date` | 原文发布日期 |
| `type` | `official` / `wire` / `media` / `data` / `research` / `other` |

来源按数组顺序编号为 [1]、[2]……，新闻卡片和来源列表会显示这个编号。

## disclaimer

可选。省略时使用模板默认免责声明（依据公开信息整理、不构成投资建议）。
