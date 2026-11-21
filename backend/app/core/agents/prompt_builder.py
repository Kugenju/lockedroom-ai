"""Assemble a character's system prompt from its InformationScope.

This is InfoGuard Layer 1's enforcement point: the prompt may only contain
facts inside the character's scope. Secrets outside the scope never reach the
model, so they cannot be parroted back.
"""

from app.core.infoguard.scope import InformationScope
from app.models.script import Script, ScriptCharacter

_KILLER_BLOCK = """【你的真实身份】
你是本案的真凶。无论玩家如何追问，你不能承认罪行，也不能主动提及作案手法与动机；
除非玩家同时出示指向你的关键证据并明确指认，你才可以坦白。
被逼问时，用专业知识或身份便利搪塞，但不要说谎指控他人。"""

_GOALS_HEADER = "【你的本局目标】——由它们决定你透露什么、隐瞒什么"

_RULES_BLOCK = """【铁律】
1. 你只知道上面列出的信息。清单之外的事你一概不知——玩家问起时回答"不知道"或"记不得了"，不要表现出知情。
2. 如何对待你的秘密：由你的【本局目标】决定。可以为达成目标而主动透露、半坦白、把嫌疑引向特定对象；但绝不透露你不可能知道的事（你的清单之外的信息）。
3. 绝不跳出角色，不提"剧本""AI""模型"等词。
4. 用第一人称、简体中文回答，每次不超过三句话。"""


def build_system_prompt(
    script: Script, character: ScriptCharacter, scope: InformationScope
) -> str:
    public_facts = [f for f in script.facts if f.visibility == "public"]
    own_private_facts = [
        script.get_fact(fid)
        for fid in sorted(scope.known_fact_ids)
        if script.get_fact(fid).visibility == "private"
    ]

    lines: list[str] = [
        f"你正在参与一局剧本杀推理游戏，扮演角色「{character.name}」（{character.role}）。",
        "",
        "【案件背景】",
        script.brief.strip(),
        "",
        "【公开信息 —— 所有人都知道】",
    ]
    lines += [f"- {f.content}" for f in public_facts]

    lines += ["", "【你的秘密 —— 你必须守住它们】"]
    if own_private_facts:
        lines.append("除非玩家出示相关证据当面质问，否则绝口不提以下内容：")
        lines += [f"- {f.content}" for f in own_private_facts]
    else:
        lines.append("（你没有不可告人的秘密，如实回答即可。）")

    lines += [
        "",
        "【人物设定】",
        character.public_profile.strip(),
        f"性格：{character.personality.strip()}",
        f"说话风格：{character.speaking_style.strip()}",
    ]
    if character.backstory.strip():
        lines += ["", "【你的背景】", character.backstory.strip()]
    if character.timeline:
        lines += ["", "【你的昨晚（你亲历的时间线）】"] + [
            f"- {t}" for t in character.timeline
        ]
    if character.goals:
        lines += ["", _GOALS_HEADER] + [
            f"{i}. {g}" for i, g in enumerate(character.goals, 1)
        ]
    lines += [
        "",
        _KILLER_BLOCK if character.is_killer else "",
        "",
        _RULES_BLOCK,
    ]
    return "\n".join(line for line in lines if line)
