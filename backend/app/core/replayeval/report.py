"""Markdown replay report renderer.

Sections: 对局概况 / 结论 / 指标 / 泄露事件 / 推理链 / 时间线.
Consumed by the W4 frontend and exportable as a shareable artifact.
"""

from app.core.engine.events import EventType, GameEvent
from app.core.replayeval.chain import ReasoningChain
from app.core.replayeval.metrics import Metrics
from app.models.script import Script

_TIMELINE_CAP = 60


def render_report(
    script: Script, events: list[GameEvent], metrics: Metrics, chain: ReasoningChain
) -> str:
    ev = script.evaluation
    killer_name = script.get_character(ev.killer_id).name
    motive = script.get_fact(ev.motive_fact_id).content

    accusation = next(
        (e for e in events if e.type is EventType.PLAYER_ACTION
         and e.payload.get("action") == "accuse"),
        None,
    )

    lines: list[str] = [
        f"# 复盘报告：《{script.title}》",
        "",
        "## 对局概况",
        "",
        f"- 提问次数：{metrics.player_questions}",
        f"- 角色回复：{metrics.character_replies}",
        f"- 搜获线索：{metrics.clues_unlocked}/{len(script.clues)}",
        f"- 剧本难度：{metrics.difficulty}/10",
        "",
        "## 结论",
        "",
    ]
    if accusation is not None:
        d = accusation.payload.get("detail", {})
        suspect = script.get_character(d.get("suspect_id", "")).name
        verdict = "正确" if d.get("killer_correct") else "错误"
        motive_verdict = "正确" if d.get("motive_correct") else "错误"
        lines += [
            f"- 指认凶手：{suspect}（{verdict}，真相是 {killer_name}）",
            f"- 指认动机：{motive_verdict}",
        ]
    else:
        lines.append("- 玩家未进行指认。")
    lines += [
        f"- 真相：{killer_name}——{motive}",
        "",
        "## 指标",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        f"| 综合评分 | {metrics.score}（{metrics.grade} 级） |",
        f"| 关键线索覆盖率 | {metrics.clue_coverage:.0%} |",
        f"| 加权泄露率 | {metrics.leak_rate} |",
        f"| 泄露事件 | 共 {metrics.leak_events} 次（硬 {metrics.hard_leaks} / 软 {metrics.soft_leaks}） |",
        "",
        "## 泄露事件",
        "",
    ]
    leak_events = [e for e in events if e.type is EventType.LEAK_DETECTED]
    if leak_events:
        lines += ["| # | 角色 | 事实 | 严重度 | 处理 | 说明 |", "|---|---|---|---|---|---|"]
        for i, e in enumerate(leak_events, 1):
            p = e.payload
            char_name = _char_name(script, p.get("character_id", ""))
            lines.append(
                f"| {i} | {char_name} | {p.get('fact_id', '')} | {p.get('severity', '')} "
                f"| {p.get('action', '')} | {p.get('detail', '')} |"
            )
    else:
        lines.append("（本局无泄露事件，InfoGuard 全程静默。）")

    lines += ["", "## 推理链", ""]
    if chain.ok:
        if chain.suspect_trajectory:
            lines.append("**怀疑轨迹**：")
            lines += [f"{i}. {s}" for i, s in enumerate(chain.suspect_trajectory, 1)]
            lines.append("")
        if chain.key_insights:
            lines.append("**关键洞察**：")
            lines += [f"- {s}" for s in chain.key_insights]
            lines.append("")
        if chain.missed_clues:
            lines.append("**遗漏线索**：")
            lines += [f"- {s}" for s in chain.missed_clues]
            lines.append("")
        lines += [f"> {chain.summary}", ""]
    else:
        lines += [chain.summary, ""]

    lines += ["## 时间线", ""]
    lines += _timeline_lines(script, events)
    return "\n".join(lines)


def _timeline_lines(script: Script, events: list[GameEvent]) -> list[str]:
    lines: list[str] = []
    shown = 0
    for e in events:
        if shown >= _TIMELINE_CAP:
            lines.append(f"- …（其余 {len(events) - _TIMELINE_CAP} 条事件略）")
            break
        line = _event_line(script, e)
        if line:
            lines.append(line)
            shown += 1
    return lines


def _event_line(script: Script, e: GameEvent) -> str | None:
    p = e.payload
    if e.type is EventType.PHASE_CHANGE:
        return f"- ⏩ 阶段推进：{p.get('from')} → {p.get('to')}"
    if e.type is EventType.MESSAGE:
        sender = p.get("sender", "")
        content = str(p.get("content", "")).replace("\n", " ")
        if len(content) > 60:
            content = content[:57] + "……"
        if sender == "player":
            return f"- ❓ 玩家问 {_char_name(script, p.get('recipient', ''))}：{content}"
        if sender == "narrator":
            return "- 📜 主持人发言"
        return f"- 💬 {_char_name(script, sender)}：{content}"
    if e.type is EventType.CLUE_UNLOCKED:
        return f"- 🔍 搜获线索：{p.get('title', p.get('clue_id', ''))}"
    if e.type is EventType.LEAK_DETECTED:
        return (
            f"- ⚠️ 泄露（{p.get('severity', '')}）：{_char_name(script, p.get('character_id', ''))} "
            f"触及 {p.get('fact_id', '')}，已{p.get('action', '')}"
        )
    if e.type is EventType.PLAYER_ACTION and p.get("action") == "accuse":
        d = p.get("detail", {})
        return f"- 🎯 玩家指认：{_char_name(script, d.get('suspect_id', ''))}"
    if e.type is EventType.SYSTEM and p.get("kind") == "reveal":
        return "- 📖 真相揭晓"
    return None


def _char_name(script: Script, char_id: str) -> str:
    try:
        return script.get_character(char_id).name
    except KeyError:
        return char_id
