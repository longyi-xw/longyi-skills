# Developer Habits & Engineering Presets

Use these presets when generating prompts for software development, debugging, UI implementation, or system architecture. The user can add, modify, or remove items in this file at any time to match evolving workflow preferences.

## 1. Token Efficiency & Context Pinning (省 Token 与防盲搜约束)

- **Targeted File Reading (`[靶向读取]`)**: Explicitly list the target directories and files to read first. Forbid full-repository scanning when fixing localized bugs or optimizing specific views.
- **Incremental Code Review (`[增量代码审查]`)**: Perform code review and lint checks only on modified files and their direct dependents. Do not re-review unchanged modules across the entire project.
- **Context Compaction (`[上下文管理]`)**: Allow `/compact` when context grows large, and store agent planning/memory docs in git-ignored local folders so they do not pollute team repositories.

## 2. Code Modification & Architecture Boundaries (改动与架构红线)

- **Minimal Invasive Changes (`[最小侵入式改动]`)**: Prefer minimal, localized changes that do not break existing business logic or frontend-backend contracts.
- **Component Reuse Priority (`[公共组件库优先]`)**: Prioritize existing team UI component libraries (e.g., `@zcmit/ui` or shared component repos) and theme overrides before writing custom raw HTML/SCSS components.
- **Unified Event Semantics (`[事件名收敛]`)**: For WebSocket / Socket.IO push channels, prefer a single semantic event name per module (e.g., `xxx-state`) and distinguish states (`measuring`, `wait`, `completed`, `stopped`, `failed`) inside the payload object.
- **Offline / Hardware Fallback (`[离线与硬件兜底]`)**: When the backend server or embedded lower-machine is offline, implement the interface layer and mock/todo records (`INTEGRATION_TODO.md`) first without blocking on live hardware tests.

## 3. Verification & Sub-Agent Orchestration (验证与多智能体调度)

- **Controlled Visual Verification (`[按需视觉验证]`)**: Disable automated CDP/visual verification for minor logic or style fixes (rely on lint + manual verification). Enable automated visual comparison only when building full prototype pages from scratch or resolving complex visual discrepancies.
- **Sub-Agent Concurrency Cap (`[子智能体上限]`)**: When enabling multi-agent workflow orchestration for parallel tasks, cap sub-agents at **<= 4** and define clear task order and file ownership to prevent edit conflicts.

## 4. Git & Repository Hygiene (Git 与版本规范)

- **No AI Author Signature (`[禁AI签名]`)**: Disable AI co-author trailers or automated AI signatures in git commits. Keep git commit authorship strictly under the developer's configured git user.
- **Branch Protection (`[分支隔离]`)**: Never commit directly to `main`. Perform work on dedicated feature/personal branches and merge to `main` only after explicit user confirmation.
- **Modular Commits (`[分功能提交]`)**: Group git commits logically by feature or fix rather than dumping unrelated changes into a single commit.

## 5. Agent Usability & Non-Destructive Compliance (合规可用性与零阉割保真)

- **De-sensitize Without Amputation (`[合规去敏保真]`)**: For dual-use engineering tasks (security/audit CLI wrappers, network proxy/DNS/telemetry privacy tools, window/process customization, protocol fault testing, archive/HAR parsers), **preserve 100% of user-requested functional capabilities, CLI flags, modules, and presets**. Replace colloquial/adversarial slang with neutral software engineering mechanics, reference upstream source registries instead of hardcoding sensitive payload literals, and enforce safety via `--dry-run`, objective impact tags, parameter validation, and `127.0.0.1`/mock verification boundaries—never by deleting user features.
