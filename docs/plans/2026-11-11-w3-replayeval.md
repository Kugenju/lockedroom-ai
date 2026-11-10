# W3 实施计划：ReplayEval — 游戏闭环补全 + 回放/指标/推理链/报告

日期：2026-11-11
目标：一局游戏可以从头玩到结局；结束后产出时间线回放、量化指标、推理链报告与 markdown 复盘。

## Task 1: 搜证 API
**Goal:** 玩家按地点搜证 → 解锁线索（clue_unlocked 事件）→ 可查询已获线索
**Files:**
- `backend/app/api/routes_game.py`：`GET /games/{id}/locations`、`POST /games/{id}/search`、`GET /games/{id}/clues`
- `backend/app/core/engine/session.py`：`unlocked_clue_ids` 状态（事件驱动）
- `backend/tests/api/test_search_api.py`
**Verification:** 搜"书房"解锁 2 条线索；重复搜证不重复记录；未知地点 404

## Task 2: 指认 API + 真相生成
**Goal:** 指认凶手+动机 → 记录 accusation 事件（含对错）→ 生成真相揭晓 → 走完 accusation→reveal→ended
**Files:**
- `backend/app/core/engine/reveal.py`（主持人 prompt：全事实无 scope，宣布指认结果+讲清真相）
- `backend/app/api/routes_game.py`：`POST /games/{id}/accuse`
- `backend/tests/api/test_accuse_api.py`
**Verification:** 凶手+动机全对/全错/半对三种组合；错误阶段 400；非法 suspect/motive 400；reveal 事件入流

## Task 3: 量化指标 metrics.py
**Goal:** 从 (script, events) 纯函数计算：加权泄露率、关键线索覆盖率、指认正确率、动机匹配、剧本难度、综合评级
**Files:**
- `backend/app/core/replayeval/metrics.py`
- `backend/tests/core/replayeval/test_metrics.py`
**公式（写进 docstring）:**
- leak_rate = Σ(hard=1.0, soft=0.3) / 角色回复数
- clue_coverage = 已解锁线索揭示的 required facts ∩ required / |required|
- score = 100×(0.45×coverage + 0.35×killer + 0.20×motive) − 20×leak_rate，S/A/B/C 分级
- difficulty = min(10, required×1.0 + talkable×0.5 + private_facts×0.2)
**Verification:** 合成事件流断言每个指标

## Task 4: 推理链提取 chain.py
**Goal:** LLM 从玩家行为序列提取结构化推理链（怀疑轨迹、关键洞察、遗漏线索、总结）
**Files:**
- `backend/app/core/replayeval/chain.py`（prompt + 防御性 JSON 解析，复用 judge 模式）
- `backend/tests/core/replayeval/test_chain.py`
**Verification:** FakeLLM 三种输出路径（正常/散文包裹/损坏→降级文本）

## Task 5: 复盘报告 report.py + 回放 API
**Goal:** markdown 报告（对局信息/结论/指标表/泄露清单/推理链）；`GET /games/{id}/replay` 组装时间线+指标；`GET /games/{id}/report` 输出 markdown
**Files:**
- `backend/app/core/replayeval/report.py`
- `backend/app/api/routes_game.py`
- `backend/tests/core/replayeval/test_report.py`、`backend/tests/api/test_replay_api.py`
**Verification:** 完整玩一局（fake）后 replay/report 内容断言

## Task 6: W3 验收
全量 pytest + ruff + fake 冒烟全流程（建局→搜证→对话→指认→回放→报告）
