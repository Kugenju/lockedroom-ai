# LockedRoom AI 架构文档

## 总览

```
┌─────────────────────────── React 前端 (frontend/) ───────────────────────────┐
│  大厅 │ 对局视图(角色栏/对话流/线索板/指认弹窗) │ 回放视图(时间线/指标/报告)     │
│  api.ts (fetch 封装) · sse.ts (POST-SSE 流式解析)                            │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │ /api/*
┌──────────────────────────────▼───────────────────────────────────────────────┐
│                        FastAPI (backend/app/api/)                            │
│  routes_game.py · schemas.py · store.py(会话注册表) · app.py(工厂+静态托管)   │
└──────────────┬──────────────────────────────────────────────┬────────────────┘
               │                                              │
┌──────────────▼─────────────┐                  ┌─────────────▼────────────────┐
│   引擎 core/engine/         │                  │  持久化 core/persistence/     │
│  state_machine(7阶段)      │                  │  SQLAlchemy: games + events   │
│  session(事件溯源)          │                  │  (SQLite 默认 / PG 可切)       │
│  reveal(主持人真相生成)     │                  └──────────────────────────────┘
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────────────────────────────────────────────────────┐
│                    角色 Agent core/agents/                                   │
│  prompt_builder：人格 + 公开事实 + 自己的秘密 + 铁律（L1 执行点）              │
│  agent.respond(): 生成 → 检测 → 裁决 → 重写/降级 → 事件记录                    │
└──────┬──────────────────────┬───────────────────────────────┬────────────────┘
       │                      │                               │
┌──────▼─────────┐  ┌─────────▼────────┐  ┌───────────────────▼──────────────┐
│ InfoGuard L1   │  │ InfoGuard L2     │  │ InfoGuard L3                        │
│ scope.py       │  │ detector.py      │  │ context_guard.py                    │
│ 剧本编译期：    │  │ judge.py         │  │ 玩家消息/记忆注入前标注越权事实        │
│ 每角色信息     │  │ 规则初筛          │  │ 加防护注释（不阻断合法质问）           │
│ 作用域+禁止清单│  │ + LLM 裁决       │  │                                     │
└────────────────┘  └──────────────────┘  └─────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────────────┐
│  LLM 抽象 core/llm/ · 剧本 core/scripts/ · ReplayEval core/replayeval/        │
│  OpenAI-compatible/Ollama/fake · thinking 开关 · YAML schema+可解性校验        │
│  metrics(泄露率/覆盖率/评级) · chain(推理链) · report(markdown)               │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 一次对话的完整管线（InfoGuard 如何工作）

玩家向角色 C 发送消息 m：

1. **L3 输入防护**：`ContextGuard` 用 FactMatcher 扫描 m，若含 C 不可能知道的事实，
   注入 prompt 时包装为"玩家声称：…（你对此一无所知）"，阻断秘密被吸收；
   **不阻断提问本身**——拿 A 的秘密质问 B 是合法玩法。
2. **L1 作用域**：prompt 由 system（人格+公开事实+自己的秘密+铁律，凶手另有隐瞒指令）
   + 经防护的对话记忆 + 当前消息构成。禁止清单内的事实从不出现在输入中。
3. **生成**：LLM 产出草稿。
4. **L2 输出检测**：`LeakDetector`（关键词 soft / 内容 shingle hard）扫描草稿；
   有命中则 `LeakJudge`（LLM）裁决 confirmed / downgraded / dismissed
   （解析失败一律按 confirmed，**失败安全**）。
5. **处置**：confirmed-hard → 带警告重写一次；仍 hard → 丢弃草稿、降级为安全回复；
   soft → 记录放行。泄露草案**永不进入记忆**，也永不出现在 SSE 流上（先审后发）。
6. **事件溯源**：玩家消息、回复、泄露事件、阶段切换、线索、指认全部追加为
   `GameEvent`（内存 + 数据库双写），这是 ReplayEval 的唯一数据源。

## 剧本模型与可解性

剧本是结构化 YAML（`backend/app/scripts/*.yaml`）：

- `facts`：信息原子单元，`public` 人尽皆知，`private` 是秘密；`core` 标记破案必需；
  `keywords` 是泄露检测的种子词。
- `characters.known_fact_ids`：该角色唯一可知的私有事实 → 决定 L1 作用域。
- `clues.reveals_fact_ids`：搜证揭示给玩家的事实（动机选项只来自已解锁线索，防剧透）。
- `evaluation`：真凶 / 动机事实 / 必需事实（判分真值）。

schema 校验保证可解性：每个私有事实必须被至少一名角色知晓或被某条线索揭示；
恰好一名凶手且必须知道动机事实；受害者不可持有秘密。

## ReplayEval：指标定义

从事件流纯函数计算（`core/replayeval/metrics.py`）：

| 指标 | 定义 |
|---|---|
| 加权泄露率 | Σ(硬=1.0, 软=0.3) ÷ 角色回复数 |
| 关键线索覆盖率 | 已解锁线索揭示的必需事实 ÷ 全部必需事实 |
| 综合评分 | 100×(0.45×覆盖率 + 0.35×凶手对 + 0.20×动机对) − 20×泄露率 |
| 评级 | S ≥ 90 / A ≥ 75 / B ≥ 60 / 其余 C |
| 剧本难度 | min(10, 必需事实×1.0 + 可问询角色×0.5 + 私有事实×0.2) |

推理链（`chain.py`）：LLM 读取玩家提问、已解锁线索、指认与真相，输出
怀疑轨迹 / 关键洞察 / 遗漏线索 / 总结；解析失败降级为占位文本，事件流仍是权威记录。

## 配置一览（前缀 SM_，环境变量或根目录 .env）

| 变量 | 默认 | 说明 |
|---|---|---|
| SM_INFERENCE_SERVICE | deepseek | deepseek / openai / ollama / fake |
| SM_MODEL | deepseek-flash | 对话模型 |
| SM_API_KEY / SM_OPENAI_API_BASE | — | OpenAI 兼容端点凭据 |
| SM_OLLAMA_URL | localhost:11434 | Ollama 地址 |
| SM_THINKING_ENABLED | false | DeepSeek thinking 模式（对话建议关） |
| SM_JUDGE_ENABLED / SM_JUDGE_MODEL | true / — | 泄露裁决开关与独立模型 |
| SM_DATABASE_URL | sqlite ./data | PostgreSQL 等可切 |
| SM_TEMPERATURE / SM_MAX_TOKENS | 0.7 / 2048 | 采样参数 |

## 扩展指引

- **新剧本**：复制 `backend/app/scripts/` 下任一模版，跑
  `pytest backend/tests/models/test_script.py` 验证可解性。
- **新 LLM 后端**：实现 `core/llm/base.py` 的 `BaseChatModel` 两个方法，
  在 `factory.py` 注册即可；judge/chain 等全部复用。
- **新指标**：在 `compute_metrics` 中加字段，`to_dict` 自动带出，前端 `Metrics` 类型同步。
