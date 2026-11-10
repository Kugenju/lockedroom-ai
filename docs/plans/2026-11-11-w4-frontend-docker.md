# W4 实施计划：React 前端 + 第二剧本 + Docker + 架构文档

日期：2026-11-11
目标：项目从"能跑的 API"变成"能玩的完整产品"，可一键容器化部署。

## 设计决策（先定，避免返工）

1. **动机选项不剧透**：指认需要 motive_fact_id，但把全部私有事实列成选项会直接泄底。
   方案：新增 `GET /games/{id}/motive-options`——只把**玩家已通过线索解锁的事实**陈述列为候选
   （+ "我不确定"选项）。指认对动机 = 找到动机线索的奖励，与线索覆盖率指标闭环。
2. **单容器部署**：前端 build 产物由 FastAPI 静态托管（StaticFiles + SPA fallback），
   不引入 nginx 反向代理。开发态用 vite proxy `/api → 127.0.0.1:18000`。
   好处：本地"类生产"运行零配置，Docker 只需一个服务。
3. **前端零重型依赖**：react + react-dom + vite 官方模板，手写 CSS；
   不引入组件库/状态库/图表库（指标用表格 + 进度条表达）。视图用 App 内状态切换，不引 router。

## Task 1: motive-options 端点（后端补口）
**Files:** `routes_game.py`、`schemas.py`、`backend/tests/api/test_accuse_api.py`（追加用例）
**Verification:** 未搜证时仅"我不确定"；搜获抽屉字据后出现对应动机陈述

## Task 2: 前端骨架
**Files:** `frontend/`（vite react-ts 模板 + vite.config.ts 代理 + src 结构）
**Verification:** `npm run build` 通过

## Task 3: API client + 类型 + SSE 流式解析
**Files:** `frontend/src/api.ts`、`frontend/src/sse.ts`
**Verification:** 类型与后端 schemas 对齐（对照 routes_game.py 手检）

## Task 4: 大厅 + 对局视图（对话流 / 角色栏 / 搜证 / 线索板 / 指认弹窗）
**Files:** `Lobby.tsx`、`GameView.tsx`、`ChatPanel.tsx`、`ClueBoard.tsx`、`AccuseDialog.tsx`、`styles.css`
**Verification:** 对接 fake 后端全流程手测 + `npm run build`

## Task 5: 回放视图（时间线 + 指标 + 报告/推理链）
**Files:** `ReplayView.tsx`、`MetricsPanel.tsx`
**Verification:** build + 手测

## Task 6: 第二剧本《午夜会议室》（现代本格）
**Files:** `backend/app/scripts/midnight-meeting.yaml`
**Verification:** schema 校验通过 + loader 测试 + `scripts` 列表断言

## Task 7: FastAPI 静态托管 + Docker
**Files:** `backend/app/api/app.py`（挂 StaticFiles）、根 `Dockerfile`（多阶段）、`.dockerignore`、`docker-compose.yml`
**Verification:** `docker build`（若本机有 Docker）或文档化验收

## Task 8: 架构文档 + README 收尾 + W4 验收
**Files:** `docs/architecture.md`、README（前端玩法/部署更新）
**Verification:** pytest + ruff + npm run build 全绿
