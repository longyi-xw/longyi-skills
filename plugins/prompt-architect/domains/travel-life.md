# Domain Plugin: Travel & Lifestyle Planning

Load this domain guide when the user wants to plan a travel itinerary, photography route, fitness/recovery schedule, or lifestyle arrangement.

## 0. Domain Isolation Rule (物理隔离铁律)

When this domain is active:
- **Never** run `ls`, `glob`, `grep`, or file reads on any local software repository or current workspace directory.
- Read only `<memory_dir>/domains/travel.md` (if present) and `presets/life-preferences.md`.

## 1. Inquiry Dimensions for L2/L3 Tasks (`D-xx` Checklist)

Present all clarifying questions in a single numbered list with sensible defaults:

- **D-01 [时间窗口与往返锚点]**: Confirm exact dates/duration, departure city, arrival/departure hubs (flights/high-speed rail), and whether tickets are already booked.
- **D-02 [同行画像与节奏偏好]**: Confirm number of travelers, physical stamina / altitude tolerance, and preferred pacing (e.g., relaxed vacation, landscape/night photography focus, or outdoor hiking).
- **D-03 [核心必去与排雷清单]**: Confirm must-visit spots or experiences, plus negative constraints (e.g., no crowded网红 spots, no early morning rush, dietary restrictions).
- **D-04 [住宿与交通方式]**: Confirm transit mode at destination (self-drive, chartered car, or public transit) and hotel style/budget range.
- **D-05 [预设偏好挂载]**: Confirm applying defaults from `presets/life-preferences.md` (`[不走回头路]`, `[摄影黄金光线窗口]`, `[恶劣天气Plan B]`).

## 2. Output Template: Structured Travel & Lifestyle Prompt

Output the final prompt inside a markdown code block:

```markdown
### 规划目标与核心画像
- **目的地与天数**：`[目的地名称，X天X晚，具体日期或季节特征]`
- **出行人群与节奏**：`[人数、体力状况、核心诉求如：雪山与夜景摄影 / 轻松慢节奏度假]`
- **往返大交通锚点**：`[去程抵达时间与站点 / 返程离开时间与站点]`

---

### 硬性约束与排雷红线（负向约束）
1. **动线要求**：严格按地理位置顺向串联，不走回头路；每日核心景点控制在 2-3 个，预留充足的休息与机动时间。
2. **排雷避坑**：拒绝纯商业化网红打卡点与笼统的营销套话；标注真实车程耗时、海拔变化（如涉及高原）及门票预约提前量。
3. **个人禁忌与偏好**：`[饮食偏好 / 住宿安静度要求 / 预算上限]`。

---

### 期望输出结构（请按以下模块生成方案）

#### 1. 每日详细动线表（按 Day 1 ~ Day N 展开）
- 包含：时间段 | 地点/活动 | 交通衔接与耗时 | 核心看点/机位建议（含日出日落或夜景时间窗） | 餐饮与住宿建议。

#### 2. 关键后勤与预约清单
- 必抢门票/观景台预约渠道与放票时间。
- 住宿片区推荐理由（兼顾交通便利性与环境）。

#### 3. 应急备选方案（Plan B）
- 针对恶劣天气（降雨/大雾封山）、交通延误或体力透支的同日替代方案。

#### 4. 行前物品与装备核对单
- 结合当地气候与活动类型（如摄影器材参数准备、防寒/防晒/高反物资）列出精简必带清单。
```
