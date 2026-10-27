# Domain Plugin: Software Development & Integration

Load this domain guide when the user wants to implement features, fix bugs, integrate APIs/protocols (HTTP, WebSocket/Socket.IO, Modbus, Serial), or restore UI prototypes (MasterGo/Pen MCP).

## 1. Inquiry Dimensions for L2/L3 Tasks (`D-xx` Checklist)

Select only the questions that are still ambiguous after checking the user's message and host project memory:

- **D-01 [靶向文件与上下文锚定]**: Confirm the exact files/directories to read and modify (pre-fill from `<memory_dir>/projects/<project>.md`), and confirm whether to forbid scanning other directories.
- **D-02 [核心业务与数据契约]**: Clarify input/output payload shapes, register addresses, unit conversion rules, or state machine transitions (e.g., normal vs. edge/error/timeout states).
- **D-03 [外部依赖与联调环境]**: Confirm whether live hardware/backend/MCP links are online, or if the agent should write Mock data + update `INTEGRATION_TODO.md` without running live tests.
- **D-04 [UI与验证策略]** *(Ask only if frontend/UI is involved)*: Confirm whether to use shared UI components, layout constraints (e.g., fixed screen size / no page scroll), and whether to run CDP visual verification or manual check only.
- **D-05 [工程习惯与工作流挂载]**: Pre-select applicable switches from `presets/dev-habits.md` (e.g., `[最小侵入改动]`, `[禁AI签名]`, `[增量Review]`, `[合规去敏保真]` *(auto-enable for dual-use/security/system tools)*, `[先不提交代码 / 按功能提交]`, `[子Agent<=4]`).

## 2. Output Template: L1 Express Prompt (Simple Task)

For L1 tasks, output this compact card inside a markdown code block without asking questions:

```markdown
### 任务目标
[一句话明确要修复的问题或新增的小功能]

### 靶向文件与上下文（严禁全盘扫描无关目录）
- 目标文件：`[精确文件路径 1]`、`[精确文件路径 2]`
- 关联参考：`[协议/文档路径或无需额外读取]`

### 具体改动要求
1. [改动点 1：明确逻辑、字段名或样式调整]
2. [改动点 2：边界与异常处理]

### 执行约束与验收
- 约束：采用最小侵入式修改，不影响现有其他业务逻辑；[挂载的习惯如：不使用自动视觉验证 / 先不提交代码]。
- 验收：[1-2条直观的自测通过标准]。
```

## 3. Output Template: L2/L3 Standard Engineering Prompt

For L2 and L3 tasks, generate the prompt following this 5-section engineering blueprint inside a markdown code block:

```markdown
### 任务目标
完成 [模块/功能名称] 的以下核心任务：
1. 【[子目标 1 标题]】：[清晰描述预期达成的业务或技术效果]。
2. 【[子目标 2 标题]】：[清晰描述预期达成的业务或技术效果]。

---

### 核心上下文与数据契约（Token 靶向锚定）
1. **靶向读取清单（禁止盲目全局搜索）**：
   - 核心代码：`[精确文件路径与关键函数名]`
   - 参考文档/协议：`[文档路径 / MCP 链接 / 参考 Git Commit]`
   - **禁读与禁改范围**：禁止修改 `[受保护目录/分支]`，无需扫描与本模块无关的目录。
2. **数据契约 / 协议字段 / 原型规范**：
   - `[字段名 / 寄存器地址 / 事件名]`：`[类型、单位、取值范围与业务语义]`
   - `[状态流转与异常约定]`：`[如：超时返 500 不伪装状态码 / 统一使用 xxx-state 事件名通过 payload 区分状态]`

---

### 具体改动清单

#### 1. [模块/层级一，如：数据总线与协议解析层]
- **`[文件路径 1]`**：
  - [具体函数或位置的修改指令，说明替换还是追加]
  - [性能或状态保护要求，如防抖节流、Object.freeze、读写指针兜底]

#### 2. [模块/层级二，如：业务逻辑与视图交互层]
- **`[文件路径 2]`**：
  - [状态绑定、生命周期闭环、组件复用与样式边界要求]

#### 3. [文档与测试同步（如适用）]
- **`[文档或测试脚本路径]`**：
  - [更新联调记录 / 生成测试脚本要求]

---

### 执行红线与工作流约束
- **改动原则**：最小侵入式修改，优先复用项目公共组件库与既有通信封装。
- **验证策略**：[如：仅做增量代码审查与 lint 验证，不开启自动化视觉验证 / 使用 CDP 对照 MCP 设计稿验证]。
- **环境与联调兜底**：[如：真机已就位直接实测 / 后端离线仅完成代码对接并将待测项记入文档]。
- **Git 与 Agent 规范**：[如：开启不超过 4 个子智能体并发 / 禁止 AI 自动签名 / 完成后先不提交代码待人工确认]。

---

### 验收与自测标准
1. **正常流验证**：[启动命令与操作步骤] -> [预期界面表现、日志输出或接口响应]。
2. **边界与异常流验证**：[断开连接 / 超限位 / 停止并重置] -> [预期兜底表现与状态恢复]。
```
