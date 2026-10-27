# Domain Plugin: System Architecture & Project Porting

Load this domain guide when the user wants to design a new system architecture, scaffold a new project (e.g., Tauri, Electron, FastAPI/Flask, Vue 3), port an existing backend/frontend across languages, or orchestrate a multi-phase project plan.

## 1. Inquiry Dimensions for L2/L3 Tasks (`D-xx` Checklist)

Ask all unresolved architectural questions in a single numbered list with recommended defaults:

- **D-01 [基准工程与参考文档]**: Confirm existing reference projects (e.g., legacy codebase path, template repo path) and requirement/protocol documents (`PDF / Markdown / MCP`) to ingest first.
- **D-02 [技术栈与兼容性锁定]**: Confirm core framework versions, dependency stability priorities, and target runtime constraints (e.g., Windows + Linux dual compatibility, Android WebView / Chrome low-version fallback, local storage engine).
- **D-03 [核心业务边界（做与不做）]**: Clarify what belongs in the current phase vs. deferred to future phases (e.g., "framework + layout only without detailed business UI", or "implement HTTP/DB layer first to decouple from lower-machine hardware").
- **D-04 [外部接口与 Mock 策略]**: Identify internal vs. third-party integrations and confirm whether missing protocols should be mocked first or recorded in a hardware debug plan.
- **D-05 [交付物与工作流编排]**: Confirm expected deliverables (architecture design doc, weekly/overall task schedule `.md`, or scaffolded git tag) and whether this turn is **plan/doc-only (no code changes)** or actual scaffolding.

## 2. Output Template: Architecture & Porting Blueprint Prompt

Output the assembled prompt inside a markdown code block:

```markdown
### 架构与工程任务目标
1. **总体目标**：[如：完成 XX 项目从 Node.js 到 Python 的后端移植规划 / 搭建基于 Tauri+Vue3 的手持端基础工程]。
2. **当前阶段边界（明确做与不做）**：
   - **本次必做**：[如：深度扫描基准项目算法与协议、输出架构方案与分阶段实施计划]。
   - **本次不做**：[如：不修改原项目任何代码 / 暂不实现开始-暂停逻辑 / 不做具体业务页面编码]。

---

### 前置信息与基准工程锚定
1. **参考工程与目标目录**：
   - 基准/旧版参考目录：`[路径 1，说明只读属性与重点分析的子目录如 src/main]`
   - 新工程目标目录：`[路径 2，说明分支要求如 develop/xxx]`
   - 需求与协议源：`[需求 PDF 路径 / 腾讯文档或 Apifox MCP 索引]`
2. **技术路线与环境红线**：
   - 核心技术栈：`[框架、UI库、状态管理、数据库与打包工具]`
   - 兼容性与稳定性要求：`[如：优先保证依赖版本对齐防白屏 / 兼容 Windows 与 Linux 命令行参数启动 / 适配低版本 WebView]`

---

### 核心架构与任务编排要求

#### 1. 业务对齐与差异梳理
- 对照基准工程与最新协议，梳理完整的模块映射关系。
- 明确标注**旧版逻辑与新版协议的差异点**以及**新增业务需求**（如：`[具体新增模式或接口]`）。

#### 2. 解耦与联调策略
- **优先级编排**：优先完成可独立闭环的层级（如 HTTP 路由层、本地数据库持久化、前端 Mock 链路），降低对嵌入式下位机或第三方未就绪接口的阻塞依赖。
- **联调文档沉淀**：将需要真机验证或第三方确认的协议疑点单独输出至 `[如：docs/hardware-debug.md]`。

#### 3. 工程规范与模板化要求
- `[如：建立公共静态资源目录、替换旧版组件库为团队公共组件仓、配置 Git 忽略规则隔离本地 Agent 记忆文件]`。

---

### 产出物与执行约束
1. **交付物清单**：
   - 输出目录：`[指定文档或工程输出路径]`
   - 输出文件：`[1. 技术架构设计方案.md  2. 整体与本周开发计划.md]`
2. **Agent 调度与安全红线**：
   - 使用工作流模式，开启子智能体不超过 4 个，自动分析并编排任务顺序。
   - `[如：本次对话仅输出规划文档，严禁修改任何业务代码 / 测试通过后打上基础模板 Git Tag]`。
```
