# Task Agent V2 渐进迁移指南

## 1. 新旧路径

旧版 Planner、Executor、Evaluator 和敏感分析接口仍保留，现有手动聊天、Payload、Attack Module 和 Compare 流程不受影响。Attack Agent 自动化入口已切换到 V2：

```text
前端 create task
→ 后端 LangGraph 后台任务
→ 前端按 taskId 查询快照
→ pause / resume / stop
```

旧版浏览器内循环不再作为启动路径。V2 的业务状态和 checkpoint 位于：

```text
data/task_agent_v2/tasks.sqlite
data/task_agent_v2/checkpoints.sqlite
```

## 2. API

基础路径：`/api/v1/task-agents`

| 操作 | API |
|---|---|
| 启动 | `POST /tasks` |
| 状态 | `GET /tasks/{task_id}` |
| 任务列表/恢复定位 | `GET /tasks?session_id=&chat_id=` |
| 暂停 | `POST /tasks/{task_id}/pause` |
| 恢复 | `POST /tasks/{task_id}/resume` |
| 停止 | `POST /tasks/{task_id}/stop` |
| Trace | `GET /tasks/{task_id}/traces` |
| 工作流定义 | `GET /workflow` |
| Prompt 版本 | `GET /prompts` |
| Skill 管理 | `/skills` |

同一 `session_id + chat_id` 只能有一个活动任务。重复启动返回 `409` 和活动 `taskId`，前端会恢复该任务而不是创建第二个循环。

## 3. 配置迁移

旧默认最多八轮已移除。新默认：

```json
{
  "termination_mode": "guarded_unbounded",
  "max_rounds": null,
  "request_interval_ms": 1200,
  "max_node_retries": 2,
  "max_consecutive_target_failures": 3,
  "duplicate_similarity_threshold": 0.92,
  "max_consecutive_duplicates": 5,
  "max_no_novelty_rounds": 5
}
```

如需受限兼容实验，显式设置 `termination_mode="bounded"` 和 `max_rounds`。不要把 bounded 配置当作全局默认。

Guarded unbounded 仍会在以下情况停止或暂停：

- 人工暂停、恢复、停止；
- 连续目标失败；
- 连续重复草稿（重复会先把失败原因返回 Planner 重规划）；
- 连续无新证据；
- 高风险敏感信息；
- Executor 消息直接发送到配置目标，不经过预发送内容拦截；
- 可选运行时间、Token、费用和显式轮数预算；
- 结构化输出在有限重试后仍无效。

## 4. 恢复语义

- 页面切换和刷新不会停止后端任务；
- 重新进入 Chat 后，前端按 `sessionId/chatId` 恢复活动任务并继续轮询；
- 后端启动时恢复 `queued/running/pausing/stopping`，不会自动恢复显式 `paused`；
- Target 轮次使用稳定 `round_key`，已提交的响应不会因恢复而重复发送；
- 成功后先保存请求、响应、证据和 GOAL PROGRESS 记录，再自动释放 Composer 供下一目标使用；
- 手动清除目标仍要求二次确认，并先请求后端停止。

## 5. Skill 迁移

Skill 根目录：`app/executor_skills`。启动时只加载目录元数据和 Technique 摘要；Planner 选择一个 PRIMARY 与可选 SUPPORTING Skills 后，Multi-Skill Loader 才读取所选正文。Skill Composer 每轮只激活一个 PRIMARY Technique 和至多一个 SUPPORTING Technique。正在运行的图状态保存正文 hash、版本、组合方案与逐 Skill 状态，因此删除 Skill 不会修改已提交轮次；下次重新加载失败会进入可审计的重规划路径。

Skill 只能是单目录 `SKILL.md`，不接受客户端路径。创建、修改、复制和删除全部经过固定根目录、slug、大小、 YAML `safe_load`、符号链接逃逸和 Prompt-only 内容校验。

## 6. 前端使用

1. 打开 Agents → Red Team Sessions → Open Chat。
2. 点击红色 **Attack Agent**。
3. 输入目标并点击 **Set Goal**。
4. 紧凑的 INTERACTION GOAL 卡持续显示状态和进度；点击 **Details** 查看轮次、方法、Skill、模型、Token、节点以及暂停/恢复/停止。
5. AI WATCH 自动开启，并把每轮目标进度和敏感分析分别记录。
6. 目标成功后输入区自动恢复，可立即设置下一个目标。
7. 齿轮按钮位于 Attack Agent 右侧：
   - Executor Skills：搜索、筛选、创建、编辑、验证、复制、启用/禁用和删除；
   - Workflow：纯 Vue 绘制的 Planner、Executor、Goal Evaluator 三智能体协作图。

GOAL PROGRESS 记录卡与敏感规则卡使用相同的折叠交互，但标签独立；进入记录弹窗后每轮默认折叠，展开后可查看完整请求、响应、证据和缺口。

## 7. 回滚

V2 是增量新增，不需要删除旧接口。若需要暂时回滚前端入口，可恢复 `EndpointsView.vue` 的旧调用路径；不要删除 V2 SQLite 文件或旧接口。回滚前先停止活动 V2 任务，避免旧循环和新后台任务同时作用于同一 Chat。

## 8. 验证清单

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm test -- --run
npm run build
```

手工验证：

- 启动任务后切换页面再返回，状态和卡片保持；
- 暂停后刷新，状态仍为 Paused；
- Resume 后从 checkpoint 继续；
- 成功后存在 GOAL PROGRESS 请求/响应记录且 Composer 已释放；
- 相似草稿先触发 Replan，不在第二次直接显示黄色停止；
- 设置面板不越界，技能列表独立滚动；
- Workflow 不含 Vue Flow 控件、缩放器或 minimap。
