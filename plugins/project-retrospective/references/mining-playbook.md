# 挖掘手册：从代码里挖出知识与证据

## 一、贡献识别：先划清「我做的」

```bash
git shortlog -sne --all | head -20                       # 谁提交了多少
git log --author="<邮箱>" --oneline | wc -l               # 我的提交数
git log --author="<邮箱>" --name-only --format='' \
  | sort | uniq -c | sort -rn | head -30                  # 我改得最多的文件 = 我的主战场
git log --author="<邮箱>" --format='%ad' --date=format:'%Y-%m' \
  | sort | uniq -c                                        # 我的投入时间分布
git log --format='%ad' --date=short | tail -1             # 项目起始
```

多邮箱时用 `--author` 的正则形式：`git log --author='alice@a.com\|alice@b.com'`。

**判读：**
- 提交占比 >70% 且时间跨度完整 → 可以说「主导 / 独立开发」
- 只集中在某几个目录 → 只对这些模块做深度挖掘，其余不写进档案
- 大量提交是 `chore`/`merge`/格式化 → 剔除后再看真实占比，别自欺
- 首个 commit 就是几万行 → 那是导入的既有代码或脚手架，**不是你写的**

```bash
git log --author="<邮箱>" --shortstat --format='%h' | \
  awk '/files? changed/ {f+=$1; i+=$4; d+=$6} END {print f" files, +"i" -"d}'
```

净增行数远小于总提交行数时，说明大量是重构与调整——这本身是可写的经历（「持续重构 X 模块」），但别按新增代码量吹。

## 二、难点雷达：扫描命令与判读

**1. 注释里的求救信号** —— 最直接的难点标记

```bash
grep -rniE "workaround|hack|兼容|踩坑|坑|注意|不能删|勿删|临时|todo|fixme|why|奇怪|居然|必须" \
  --include="*.{ts,tsx,js,jsx,vue,py,go,rs,java,kt,swift,c,cpp,cs}" \
  --exclude-dir={node_modules,dist,build,.git,vendor,target} . | head -60
```

判读：解释「为什么必须这么写」的注释 = 一个被解决过的问题。只是「TODO 优化」的忽略。

**2. 反复修改的文件** —— 一次没做对的地方

```bash
git log --pretty=format: --name-only \
  | grep -vE '^$|package-lock|pnpm-lock|yarn.lock|\.snap$' \
  | sort | uniq -c | sort -rn | head -25
```

判读：排除配置和入口文件后，top 的业务/核心文件就是复杂度沉积区。逐个 `git log -p --follow <文件>` 看它经历了什么。

**3. 自研而非用库** —— 现成轮子不够用才自己造

```bash
find . -type d \( -name core -o -name engine -o -name utils -o -name lib -o -name kernel \) \
  -not -path '*/node_modules/*' 2>/dev/null
```

对照 `package.json`/`requirements.txt`：项目装了某类库却又自己实现了一遍，**一定要问清为什么**——答案就是最好的 L2 材料。

**4. 性能与容错痕迹**

```bash
grep -rniE "worker|requestidlecallback|requestanimationframe|debounce|throttle|memo|cache|lru|\
virtual|lazy|chunk|defer|preload|批量|分片|节流" --include="*.{ts,js,vue,py,go,rs}" \
  --exclude-dir={node_modules,dist,.git} . | head -40

grep -rniE "retry|fallback|degrade|circuit|timeout|abort|cancel|signal|重试|降级|兜底|超时" \
  --include="*.{ts,js,vue,py,go,rs}" --exclude-dir={node_modules,dist,.git} . | head -40
```

判读：这些代码出现，说明碰到过真实的性能墙或不确定性。**去 git log 找它是哪个 commit 加的、commit message 说了什么**——那就是问题现场。

**5. commit message 里的历史**

```bash
git log --oneline --grep='fix\|perf\|refactor\|优化\|修复\|重构' -i | head -40
git log --oneline --grep='revert\|回滚' -i | head             # 回滚过的都是硬骨头
```

**6. 算法与复杂逻辑**

```bash
# 长文件（复杂度的粗略代理）
find . -name "*.ts" -o -name "*.vue" -o -name "*.py" 2>/dev/null \
  | grep -vE 'node_modules|dist' | xargs wc -l 2>/dev/null | sort -rn | head -20
# 数学/几何/编解码痕迹
grep -rniE "Math\.(sin|cos|atan|sqrt|pow)|matrix|quaternion|vector3|crc|base64|encode|decode|\
状态机|state machine" --include="*.{ts,js,py,rs}" --exclude-dir=node_modules . | head -30
```

## 三、技术主题的取舍

**值得写进档案的：**
- 有约束冲突的取舍（性能 vs 可维护、体积 vs 功能、实时性 vs 一致性）
- 现成方案失效、需要自己设计的机制
- 跨边界的通信/协议设计（IPC、Worker、SSE、WebSocket、插件系统）
- 数据结构或算法选择显著影响了结果
- 出过问题并被修复的（有前因后果的完整故事）
- 工程化投入带来可量化收益的（构建、发布、监控、类型体系）

**不值得写的（写了反而暴露水平）：**
- 「实现了 20 个 CRUD 页面」——数量不是能力
- 「使用了 Vue3 + Pinia + Element Plus」——这是技术栈清单，不是经历
- 「熟练掌握 X」——没有场景和代价的形容词
- 脚手架默认配置、复制来的模板
- 代码行数、页面数、组件数这类体量指标

数量指标只在能说明规模压力时才有意义（「单页 3 万节点的渲染」有意义，「写了 3 万行代码」没意义）。

## 四、四层阶梯：正反例

### 反例（只到 L0/L1，简历里随处可见）

> 使用 Web Worker 优化了 3D 场景的渲染性能，提升了用户体验。

问题：没说难在哪、为什么是 Worker、代价是什么、能不能迁移。面试官追问两句就空了。

### 正例（爬到 L3）

> **L0** Vue3 + Three.js + Web Worker + Comlink
>
> **L1（机制）** 场景变更走增量 diff：编辑器每次操作产出一份 patch 描述，Worker 内维护场景影子树、计算需要重建的最小子树，回传 patch 指令数组；主线程只做 `applyPatch`，不参与 diff 计算。
>
> **L2（决策）** 最初尝试主线程内 `requestIdleCallback` 分片，但复杂场景下单次 diff 就超过一帧预算，仍然掉帧。也评估过整棵树 postMessage，结构化克隆的序列化成本反而更高。最终选择「Worker 内算 diff、只回传指令」，代价是：影子树需要在两端保持一致，引入了状态同步复杂度，并且首帧多一次全量克隆。为此加了版本号校验，不一致时回退全量重建。
>
> **L3（可迁移）** 抽象出的模式是「**重计算下沉 + 结构化增量回传**」：只要出现「主线程被长任务阻塞，但结果可以描述成增量指令」的场景就适用——大表格的排序过滤、富文本的排版计算、图编辑器的布局。判断能否套用的关键是**增量描述的体积是否显著小于全量结果**；否则序列化成本会吃掉收益。
>
> **证据** `src/core/worker/diff.ts:45-160`、commit `a1b2c3d`（「perf: diff 下沉 Worker」）
>
> **成果** 复杂场景交互帧率 24fps → 58fps（`user_stated`，未留测量脚本）

注意正例里的三件事：**说了放弃的方案和原因**、**主动交代了代价**、**给出了适用边界判据**。这三点是 L2/L3 的实质。

## 五、注水陷阱清单

| 陷阱 | 为什么危险 | 正确写法 |
|------|-----------|----------|
| 把依赖当能力 | 面试官问原理就穿帮 | 只写你调过参、读过源码、踩过坑的 |
| 把团队成果写成个人成果 | 背景调查一问就露 | 写清「我负责其中的 X」 |
| 编造性能数字 | 追问测量方法必崩 | 没测过就写「未量化」，或补一次测量再写 |
| 把脚手架算成架构设计 | 一看仓库首个 commit 就知道 | 写你在其上做的改造 |
| 术语堆砌（微服务/高并发/大数据） | 与项目真实规模不符 | 用真实数量级描述 |
| 「优化了性能」不说怎么优化 | 等于没写 | 一定要有机制层描述 |

**当用户希望写得更漂亮但证据不足时**：如实告诉他缺口在哪、可以补什么（补一次基准测量、翻一下当时的聊天记录/文档找数据），而不是替他润色成一句站不住的话。
