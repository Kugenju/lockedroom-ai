# LockedRoom AI

> 仓库名 `lockedroom-ai` ——"密室"双关：剧本杀的经典密室诡计，与每个 AI 角色被锁进自己信息密室的信息隔离设计。

多智能体 LLM 剧本杀推理平台 —— 以**信息隔离与防剧透引擎（InfoGuard）**和**复盘评估系统（ReplayEval）**为核心差异化。

每个 AI 角色是独立 Agent，拥有按剧本编译的信息作用域；泄露检测在回复到达玩家之前拦截；整局游戏以事件流持久化，支撑回放、推理链提取与量化评估。

## 当前进度（W5 ✅ 前端游戏壳化完成）

- **三栏游戏壳**（参考 ai-murder-mystery / wolfcha 的界面调研）：顶栏六阶段进度条 + 左栏案件档案（案情简介常驻可折叠 + 线索板）+ 中单聊视图 + 右角色名册（配色头像/当前对象高亮）+ 底部阶段行动条
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
