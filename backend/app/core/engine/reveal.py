"""Narrated truth reveal (真相揭晓).

Unlike character agents, the narrator legitimately knows everything — this is
the one place where the *full* fact list enters a prompt. Called once per game,
at the accusation.
"""

from app.core.llm.base import BaseChatModel, ChatMessage
from app.models.script import Script

_SYSTEM = """你是剧本杀游戏的主持人，现在公布案件真相。
要求：
1. 先用一句话宣布玩家的指认是否正确（凶手与动机分开说）。
2. 然后用连贯的一两段讲清真正的作案手法、时间线与动机，像推理小说结尾的解谜篇章。
3. 全程用中文，250 字左右，不要条目化，不要提及"剧本""AI"等词。"""


async def generate_reveal(
    script: Script,
    suspect_id: str,
    motive_fact_id: str,
    llm: BaseChatModel,
) -> str:
    ev = script.evaluation
    facts_text = "\n".join(f"- {f.content}" for f in script.facts)
    suspect = script.get_character(suspect_id).name
    truth = script.get_character(ev.killer_id).name
    motive = script.get_fact(ev.motive_fact_id).content
    if motive_fact_id is not None:
        accused_motive = script.get_fact(motive_fact_id).content
    else:
        accused_motive = "（玩家未指认动机）"
    user = (
        f"案件完整事实：\n{facts_text}\n\n"
        f"玩家指认：凶手={suspect}，动机={accused_motive}\n"
        f"正确答案：凶手={truth}，动机={motive}"
    )
    resp = await llm.chat(
        [ChatMessage(role="system", content=_SYSTEM), ChatMessage(role="user", content=user)],
        temperature=0.7,
    )
    return resp.content
