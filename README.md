# LockedRoom AI

> 仓库名 `lockedroom-ai` ——"密室"双关：剧本杀的经典密室诡计，与每个 AI 角色被锁进自己信息密室的信息隔离设计。

多智能体 LLM 剧本杀推理平台 —— 以**信息隔离与防剧透引擎（InfoGuard）**和**复盘评估系统（ReplayEval）**为核心差异化。

每个 AI 角色是独立 Agent，拥有按剧本编译的信息作用域；泄露检测在回复到达玩家之前拦截；整局游戏以事件流持久化，支撑回放、推理链提取与量化评估。

## 当前进度（W2 ✅）

- FastAPI 后端 + 事件溯源游戏会话（7 阶段状态机），事件**双写内存与数据库**（SQLite 默认，`SM_DATABASE_URL` 可切 PostgreSQL）
- LLM 抽象层：OpenAI-compatible（DeepSeek 等）/ Ollama / fake（无 API 调试），统一流式接口；DeepSeek **thinking 模式开关**（对话默认关，降延迟，`SM_THINKING_ENABLED`）
- 结构化剧本 YAML（facts / characters / clues / evaluation，含可解性校验）
- **InfoGuard 三层防剧透管线**：
  - **L1** 静态信息作用域：prompt 只注入角色可知事实，凶手带隐瞒指令
  - **L2** 规则检测（关键词 soft / 内容 shingle hard）+ **LLM judge 复核**（确认/降级/撤销，失败安全默认为确认；`SM_JUDGE_ENABLED`、`SM_JUDGE_MODEL` 可配），硬泄露自动重写、重写失败降级安全回复
  - **L3** 上下文防护：玩家消息/记忆中越权事实注入前加防护注释，阻断"秘密回流"
- **ReplayEval 复盘评估**：加权泄露率 / 关键线索覆盖率 / 指认与动机判定 / S-C 综合评级 / 剧本难度分；LLM 推理链提取（怀疑轨迹、关键洞察、遗漏线索）；markdown 复盘报告导出；完整游戏闭环（按地点搜证 → 自由调查 → 指认凶手+动机 → 主持人真相揭晓）
- SSE 流式对话（先审后发：未过检的文本不会出现在流里）
- 示例剧本《雪夜·山庄》（5 嫌疑人 / 12 事实 / 5 线索）
- **228 个测试**：单元 + API + 全角色×全事实泄露对抗矩阵（95 格）+ 指标/报告

## 快速开始

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
```

启动服务（Windows PowerShell）：

```powershell
$env:SM_INFERENCE_SERVICE="fake"; .venv\Scripts\python.exe -m uvicorn app.api.app:create_app --factory --app-dir backend --port 18000
```

Git Bash 等价写法（`SM_INFERENCE_SERVICE=fake .venv/Scripts/python.exe -m uvicorn ...`）同样可用。

接入真实模型（以 DeepSeek 为例；也可复制 `.env.example` 为仓库根目录的 `.env` 后省略这些变量）：

```powershell
$env:SM_INFERENCE_SERVICE="deepseek"; $env:SM_MODEL="deepseek-flash"; $env:SM_API_KEY="sk-xxx"; $env:SM_OPENAI_API_BASE="https://api.deepseek.com"; .venv\Scripts\python.exe -m uvicorn app.api.app:create_app --factory --app-dir backend --port 18000
```

Ollama 本地兜底：`$env:SM_INFERENCE_SERVICE="ollama"; $env:SM_OLLAMA_URL="http://localhost:11434"; $env:SM_MODEL="qwen2.5:7b"`

## 测试与检查

```bash
.venv/Scripts/python.exe -m pytest -q     # 57 个测试
.venv/Scripts/ruff.exe check backend
```

## 剧本格式

见 `backend/app/scripts/snow-night-villa.yaml`。核心概念：

- **fact**：信息原子单元（公开/私有，标记 core 表示破案必需）；`keywords` 是泄露检测的种子词
- **character.known_fact_ids**：该角色**唯一**能知道的事实 —— InfoGuard L1 只把这些注入 prompt，其余全部进禁止清单
- **clue.reveals_fact_ids**：搜证阶段解锁、对玩家揭示的事实
- **evaluation**：真凶、动机事实、破案必需事实（ReplayEval 的判分依据）

校验规则保证剧本可解：每个私有事实必须被至少一个角色知道或被某条线索揭示；恰好一名凶手且凶手必须知道动机事实。

## 路线图

- [x] W1 骨架 + LLM 抽象 + 剧本 schema + 引擎核心 + API
- [x] W2 InfoGuard 三层管线 + LLM judge + thinking 开关 + 数据库持久化 + 对抗矩阵
- [x] W3 ReplayEval：游戏闭环（搜证/指认/真相）+ 量化指标 + 推理链提取 + 复盘报告
- [ ] W4 React 前端（对话/搜证/回放可视化）+ 第二个剧本 + Docker 部署 + 架构文档

设计文档：`design-docs/2026-11-10-scriptmurder-design.md`
