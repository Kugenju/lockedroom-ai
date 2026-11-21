# LockedRoom AI

> 仓库名 `lockedroom-ai` ——"密室"双关：剧本杀的经典密室诡计，与每个 AI 角色被锁进自己信息密室的信息隔离设计。

多智能体 LLM 剧本杀推理平台 —— 以**信息隔离与防剧透引擎（InfoGuard）**和**复盘评估系统（ReplayEval）**为核心差异化。

每个 AI 角色是独立 Agent，拥有按剧本编译的信息作用域；泄露检测在回复到达玩家之前拦截；整局游戏以事件流持久化，支撑回放、推理链提取与量化评估。

## 当前进度（W8 ✅ 公共知识层 + 角色剧本系统）

- **公共知识层**：线索解锁 → 广播进所有 Agent 记忆 + 其揭示事实转为公共知识——detector/guard 动态豁免，拿着线索质问不再被"你不可能知道"误伤（回归测试锁定）
- **角色剧本系统**：schema 新增 backstory/timeline/goals；三剧 14 个角色全部扩写（背景叙事 + 昨晚时间线 + 分层目标）
- **goals 驱动披露**：prompt 铁律从"绝不透露"改为"由你的本局目标决定透露什么"——允许目标驱动的主动放话/栽赃/半坦白，InfoGuard 只管真正的超范围知识
- **"你的剧本"专页**：背景故事 / 我的昨晚（时间线）/ 本局目标 / 只有你知道的事，开局先读剧本
- **扮演模式**（W7）：玩家入座制（含凶手位=脱罪胜利）、公开讨论通道（群聊视图，讨论发言走完整泄露管线）、角色卡覆盖层
- **分层记忆**（W6，调研 Generative Agents / MemGPT sleep-time / Mem0 / MARBO 后定案）：
  - 工作记忆：最近 10 轮原文常驻 prompt
  - 情景层：重要性 ≥7 的发言原文保留（上限 6 条）
  - 语义层：滑出窗口的低重要性对话由 LLM **滚动摘要**（惰性固化，backlog≥8 半轮才触发，均摊成本）
  - **InfoGuard 守门**：摘要草案和已存摘要均过泄露检测，带毒摘要禁止入库/注入（"记忆守门员"）
  - 预算护栏：记忆总字符硬封顶，超限自动降级
- **重要性评分**（LLM 1-10，Generative Agents 思路）：一次调用同时驱动记忆保留与笔记钉选
- **推理笔记面板**：档案栏"笔记"标签页——高价值发言自动钉入（📌 角色名+重要性），玩家手动增删（✍️）；事件溯源 add/del 折叠
- **三栏游戏壳**（W5）：顶栏六阶段进度条 + 左栏案件档案（案情简介常驻可折叠 + 线索/笔记标签页）+ 中单聊视图 + 右角色名册 + 底部阶段行动条
- **单聊分窗**：消息按角色分桶，右栏点头像切换对话对象，只看与 Ta 的往来；自动滚动仅在贴底时跟随
- **覆盖层仪式感**：角色登场（逐人点击推进，无定时器依赖）/ 真相揭晓全屏覆盖层
- **可扩展性**：剧本 YAML `mode` 字段 + 前端 `game/layout.ts` 布局注册表——扮演模式/阵营本未来以"注册新布局+面板"接入，壳不动
- 完整游戏闭环 + **双剧本**：《雪夜·山庄》（古典暴风雪山庄）/ 《午夜会议室》（现代本格·花生过敏密室）
- **单容器部署**：FastAPI 直接托管前端构建产物（SPA），根目录多阶段 `Dockerfile` + `docker-compose.yml`（数据卷持久化）
- **InfoGuard 三层防剧透管线**：
  - **L1** 静态信息作用域：prompt 只注入角色可知事实，凶手带隐瞒指令
  - **L2** 规则检测（关键词 soft / 内容 shingle hard）+ **LLM judge 复核**（确认/降级/撤销，失败安全默认为确认；`SM_JUDGE_ENABLED`、`SM_JUDGE_MODEL` 可配），硬泄露自动重写、重写失败降级安全回复
  - **L3** 上下文防护：玩家消息/记忆中越权事实注入前加防护注释，阻断"秘密回流"
- **ReplayEval 复盘评估**：加权泄露率 / 关键线索覆盖率 / 指认与动机判定 / S-C 综合评级 / 剧本难度分；LLM 推理链提取（怀疑轨迹、关键洞察、遗漏线索）；markdown 复盘报告导出；完整游戏闭环（按地点搜证 → 自由调查 → 指认凶手+动机 → 主持人真相揭晓）
- SSE 流式对话（先审后发：未过检的文本不会出现在流里）
- 示例剧本《雪夜·山庄》（5 嫌疑人 / 12 事实 / 5 线索）
- **228 个测试**：单元 + API + 全角色×全事实泄露对抗矩阵（95 格）+ 指标/报告

## 快速开始

### 方式一：Docker（推荐，单容器含前端+后端）

```powershell
docker compose up -d --build
# 打开 http://localhost:18000
```

在根目录 `.env` 填入 `SM_API_KEY` 等配置（compose 自动注入；无 key 可用 `SM_INFERENCE_SERVICE=fake` 体验假模型）。

### 方式二：本地开发

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
cd frontend && npm install
```

启动两个进程（PowerShell）：

```powershell
# 终端1：后端（无 API 可设 $env:SM_INFERENCE_SERVICE="fake"）
.venv\Scripts\python.exe -m uvicorn app.api.app:create_app --factory --app-dir backend --port 18000

# 终端2：前端（vite dev，/api 自动代理到 18000；若 18000 已有后端则端口任选）
cd frontend; npm run dev
```

浏览器打开 `http://localhost:5173`。前端构建产物（`frontend/dist`）存在时，后端也会直接托管在 18000——只跑后端也能玩。

### 终端试玩（无浏览器环境）

```powershell
.venv\Scripts\python.exe scripts\play.py
```

## 测试与检查

```bash
.venv/Scripts/python.exe -m pytest -q     # 230 个测试
.venv/Scripts/ruff.exe check backend
cd frontend && npm run build              # 前端类型检查 + 构建
```

## 剧本格式

见 `backend/app/scripts/snow-night-villa.yaml`（古典本格）与 `midnight-meeting.yaml`（现代本格）。核心概念：

- **fact**：信息原子单元（公开/私有，标记 core 表示破案必需）；`keywords` 是泄露检测的种子词
- **character.known_fact_ids**：该角色**唯一**能知道的事实 —— InfoGuard L1 只把这些注入 prompt，其余全部进禁止清单
- **clue.reveals_fact_ids**：搜证阶段解锁、对玩家揭示的事实；**指认的动机选项只来自已解锁线索**，找到动机证据才能指认动机
- **evaluation**：真凶、动机事实、破案必需事实（ReplayEval 的判分依据）

校验规则保证剧本可解：每个私有事实必须被至少一个角色知道或被某条线索揭示；恰好一名凶手且凶手必须知道动机事实。

## 架构

见 [docs/architecture.md](docs/architecture.md)（分层图、InfoGuard 管线、指标定义、扩展指引）。

## 后续迭代（长期维护）

- [ ] 多真人联机（WebSocket 房间 + 真人玩家信息隔离）
- [ ] 语音交互（ASR/TTS）与 AI 生成剧本编辑器
- [ ] 剧本可视化编辑器与 AI 剧本生成流水线
- [ ] 更多剧本与 LLM 后端（智谱 / Kimi / 本地 vLLM）

设计文档：`design-docs/2026-11-10-scriptmurder-design.md`
