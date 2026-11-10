# W2 实施计划：InfoGuard 三层完备 + 事件持久化 + 对抗测试套件

日期：2026-11-10
目标：防剧透引擎从"规则单_LAYER_"升级为完整三层管线；对局事件落库；泄露检测有矩阵级测试。

## 设计修订（相对设计文档的细化）

- **L3 采用"标注+防护包装"而非"阻断玩家输入"**：剧本杀里玩家拿着 A 的秘密去质问 B 是合法玩法，不能拦。
  L3 的职责是：玩家消息/记忆中若含有"当前角色不可能知道"的事实，注入 prompt 时加防护注释
  （"玩家声称……但你对此一无所知"），防止 B 把秘密当成已知事实复述——复述则由 L2 输出检测兜底。
- **L2 升级为"规则初筛 + LLM judge 复核"两阶段**：规则命中才调 judge（成本控制），
  judge 可确认/降级/撤销，裁决写入 LeakEvent.detail。

## Task 1: FactMatcher 抽象 + ContextGuard（L3）
**Goal:** 任意文本 → 命中的事实清单（复用关键词+shingle 双信号）；角色上下文带越权事实时被标注包装
**Files:**
- `backend/app/core/infoguard/matcher.py`（FactMatcher：从 LeakDetector 抽出索引与匹配逻辑）
- `backend/app/core/infoguard/context_guard.py`（ContextGuard.guard(scope, text) → GuardResult(text, findings)）
- `backend/app/core/infoguard/detector.py`（重构为基于 FactMatcher 的薄封装，行为不变）
- `backend/app/core/agents/agent.py`（prompt 组装时对每条 memory/玩家消息过 ContextGuard）
- `backend/tests/core/infoguard/test_matcher.py`、`test_context_guard.py`
- `backend/tests/core/agents/test_agent.py`（新增 L3 用例）
**Verification:** 既有 detector/agent 测试不回归；新增：玩家消息含他人秘密 → 注入消息带防护注释；角色回复被 L2 拦截的用例依然通过

## Task 2: LeakJudge（L2 LLM 复核）
**Goal:** 规则命中后由 judge 裁决 confirmed/downgraded/dismissed；hard 命中须 judge 确认才重写
**Files:**
- `backend/app/core/infoguard/judge.py`（LeakJudge：prompt 要求严格 JSON 输出，防御性解析）
- `backend/app/core/config.py`（SM_JUDGE_MODEL，空=沿用主模型）
- `backend/app/core/agents/agent.py`（接线：hard → judge 确认 → 重写；soft → judge 可升级 hard）
- `backend/tests/core/infoguard/test_judge.py`
**Verification:** FakeLLM 模拟三种裁决；确认才触发重写的路径被测试锁定

## Task 3: Thinking 模式开关
**Goal:** 以 DeepSeek 官方文档为准实现对话 thinking 开关（默认关，降延迟）
**Files:** `backend/app/core/config.py`（SM_THINKING_ENABLED）、`backend/app/core/llm/openai_compat.py`（透传）
**Verification:** 先查官方 Thinking Mode 文档确认参数名；单测断言请求体；真 key 延迟对比由用户侧回归确认

## Task 4: 事件持久化（SQLAlchemy）
**Goal:** games + events 落库（SQLite 默认，SM_DATABASE_URL 可切 PG）；内存实现保留给测试
**Files:**
- `backend/app/core/persistence/db.py`（engine/session factory，默认 sqlite:///data/scriptmurder.db）
- `backend/app/core/persistence/models.py`（GameRow / EventRow ORM）
- `backend/app/core/persistence/event_store.py`（EventStore 协议 + SqlAlchemy 实现 + Memory 实现）
- `backend/app/api/store.py`、`backend/app/core/engine/session.py`（_emit 写穿持久层）
**Verification:** 内存 SQLite roundtrip 测试；现有 API 测试改用 Memory store 不回归

## Task 5: 泄露检测对抗矩阵
**Goal:** 简历素材：demo 剧本 全角色 × 全事实 的泄露语料集
**Files:** `backend/tests/core/infoguard/test_detector_matrix.py`
- 每角色四类语料：自述秘密（合法放行）/ 含他人关键词（检出 soft）/ 复述他人内容（检出 hard）/ 无辜闲聊（零误报）
**Verification:** 矩阵全绿

## Task 6: W2 验收
全量 pytest + ruff + 真 key 冒烟（play.py 回归，观察 judge 介入后的对话质量与延迟）
