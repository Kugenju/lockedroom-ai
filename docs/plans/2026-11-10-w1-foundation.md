# W1 实施计划：项目骨架 + LLM 抽象 + 剧本 Schema + 引擎核心

日期：2026-11-10
目标：后端核心可运行——能加载剧本、跑通与 AI 角色的流式对话，事件流可持久化。

## Task 1: 仓库骨架
**Goal:** Python 项目可安装、pytest 可运行、目录结构就位
**Files:** `pyproject.toml`, `.gitignore`, `backend/app/**/__init__.py`
**Verification:** `.venv/Scripts/python.exe -m pytest` 无收集错误

## Task 2: LLM 抽象层
**Goal:** 统一 ChatModel 接口，OpenAI-compatible（DeepSeek 等）与 Ollama 可切换，支持流式；FakeLLM 供测试
**Files:**
- `backend/app/core/llm/base.py`（ChatMessage / LLMResponse / BaseChatModel 抽象）
- `backend/app/core/llm/openai_compat.py`（OpenAI SDK + base_url 覆盖）
- `backend/app/core/llm/factory.py`（settings → provider）
- `backend/app/core/llm/fake.py`（FakeLLM：按规则回放，测试用）
- `backend/tests/core/llm/test_base_and_fake.py`、`test_openai_compat.py`
**Approach:**
1. 测试先行：FakeLLM 按消息历史返回脚本化回复；openai_compat 用 monkeypatched client 验证 base_url/api_key 透传与流式聚合
2. BaseChatModel：`chat(messages) -> LLMResponse` + `stream(messages) -> AsyncIterator[str]` + `judge(...)` 便捷方法（评估用）
**Verification:** pytest 通过；切换 INFERENCE_SERVICE 环境变量可走不同后端

## Task 3: 剧本 Schema + 加载器
**Goal:** 结构化剧本 YAML：truths（带 fact_id）/ characters（public/secrets/known_fact_ids）/ clues（可见范围）
**Files:**
- `backend/app/models/script.py`（Pydantic：Script/Character/TruthFact/Clue，含引用校验）
- `backend/app/core/scripts/loader.py`（load_script(path) / validate）
- `backend/app/scripts/demo_storm.yaml`（示例剧本）
- `backend/tests/models/test_script.py`、`backend/tests/core/scripts/test_loader.py`
**Verification:** 能加载 demo 剧本；fact_id 引用不存在时校验报错

## Task 4: InfoGuard — InformationScope 编译器
**Goal:** 剧本 → 每角色的 InformationScope（可见事实集 + 禁止清单）
**Files:**
- `backend/app/core/infoguard/scope.py`（compile_scopes(script) → dict[char_id, InformationScope]）
- `backend/tests/core/infoguard/test_scope.py`
**Approach:** 可见 = 公开事实 ∪ own_secrets ∪ known_fact_ids；禁止 = 其余全部事实；校验 known_fact_ids 不互相矛盾（如凶手不知道自己手法以外的核心诡计则告警——W1 只做基本集运算）
**Verification:** 单测覆盖：凶手 scope 不含他人秘密；受害者角色（若存在）scope 只含公开信息

## Task 5: 游戏引擎状态机 + 事件流
**Goal:** 7 阶段状态机、GameEvent 追加、非法转移拒绝
**Files:**
- `backend/app/core/engine/events.py`（GameEvent 类型：phase_change/message/player_action/leak_detected/clue_unlocked，UTC 时间戳）
- `backend/app/core/engine/state_machine.py`（Phase 枚举 + 转移表）
- `backend/app/core/engine/session.py`（GameSession：状态 + event log 内存实现）
- `backend/tests/core/engine/test_state_machine.py`、`test_session_events.py`
**Verification:** 合法/非法转移单测；事件按序追加可回放

## Task 6: 角色 Agent
**Goal:** prompt 组装（人格 + scope 注入）+ 对话记忆 + InfoGuard 管线挂点（W1 先规则级泄露检查）
**Files:**
- `backend/app/core/agents/prompt_builder.py`（system prompt 组装）
- `backend/app/core/agents/agent.py`（CharacterAgent：respond(player_msg) → 流式输出 + 事件记录）
- `backend/app/core/infoguard/detector.py`（规则级 LeakDetector：n-gram 命中禁止清单；LeakEvent 分级）
- `backend/tests/core/agents/test_prompt_builder.py`、`test_agent.py`
- `backend/tests/core/infoguard/test_detector.py`
**Verification:** prompt 中不包含 scope 外事实；注入"我是凶手我杀了X"类回复被检出并记事件

## Task 7: FastAPI + SSE
**Goal:** REST 建局/列表 + SSE 流式对话
**Files:**
- `backend/app/api/app.py`（FastAPI factory）、`backend/app/api/routes_game.py`、`backend/app/api/sse.py`
- `backend/tests/api/test_game_api.py`（TestClient + FakeLLM 端到端）
**Verification:** POST 创建对局 → SSE 对话收到流式回复 → GET 事件流完整

## Task 8: W1 验收
**Goal:** 全量 pytest 绿 + ruff 无报错 + 手工冒烟（uvicorn 起服务走通 demo 剧本一轮对话）
**Verification:** `.venv/Scripts/python.exe -m pytest -q` 全绿；`ruff check backend` 干净
