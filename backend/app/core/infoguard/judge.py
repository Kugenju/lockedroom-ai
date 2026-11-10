"""InfoGuard Layer 2b — LLM adjudication over rule-based leak findings.

The rule detector (keyword/shingle) is fast and deterministic but noisy: it
cannot tell "我亲眼看见老爷死于过量胰岛素注射" (a hard leak) from
"胰岛素是管控药品" (common knowledge). The judge asks an LLM to rule on each
hit: confirmed / downgraded / dismissed.

Fail-safe policy: any parsing failure or missing ruling counts as *confirmed* —
we would rather rewrite an innocent reply than let a real leak through.
"""

import json
from dataclasses import dataclass

from app.core.infoguard.detector import LeakFinding
from app.core.llm.base import BaseChatModel, ChatMessage
from app.models.script import Script

VERDICTS = ("confirmed", "downgraded", "dismissed")

_SYSTEM = """你是剧本杀游戏的信息安全裁判。一个角色刚刚说出了疑似泄露其不可能知道的信息的话。
对每条规则命中，裁决三选一：
- confirmed：文本确实以该角色不可能知道的方式表达了该事实（直接复述、肯定断言、细节吻合）
- downgraded：确有提及，但属常识、合理推测或语境自然，泄露程度较轻
- dismissed：纯属巧合或否定/反问语境，不构成泄露
只输出 JSON，不要输出其他内容：
{"rulings":[{"fact_id":"...","verdict":"confirmed|downgraded|dismissed","reason":"一句话理由"}]}"""


@dataclass(frozen=True)
class AdjudicatedLeak:
    finding: LeakFinding
    verdict: str  # "confirmed" | "downgraded" | "dismissed"
    reason: str

    @property
    def effective_severity(self) -> str:
        if self.verdict == "downgraded":
            return "soft"
        return self.finding.severity  # confirmed keeps rule severity


class LeakJudge:
    def __init__(self, llm: BaseChatModel, script: Script):
        self._llm = llm
        self._script = script

    async def adjudicate(
        self, character_id: str, text: str, findings: list[LeakFinding]
    ) -> list[AdjudicatedLeak]:
        """Return the leaks that survive adjudication (dismissals are dropped)."""
        if not findings:
            return []

        fact_lines = "\n".join(
            f"- {f.fact_id}: {self._script.get_fact(f.fact_id).content}" for f in findings
        )
        hit_lines = "\n".join(
            f"- {f.fact_id}（{f.severity}，命中词：{f.matched_text}）" for f in findings
        )
        user = (
            f"角色：{character_id}\n"
            f"该角色不可能知道的事实：\n{fact_lines}\n"
            f"待裁决文本：{text}\n"
            f"规则命中：\n{hit_lines}"
        )
        resp = await self._llm.chat(
            [ChatMessage(role="system", content=_SYSTEM), ChatMessage(role="user", content=user)],
            temperature=0,
        )
        rulings, parse_ok = self._parse(resp.content)
        by_fact = {r["fact_id"]: r for r in rulings if r.get("verdict") in VERDICTS}

        out: list[AdjudicatedLeak] = []
        for finding in findings:
            ruling = by_fact.get(finding.fact_id)
            if ruling is None:
                reason = (
                    "no ruling from judge (fail-safe)"
                    if parse_ok
                    else "judge output unparseable (fail-safe)"
                )
                out.append(AdjudicatedLeak(finding, "confirmed", reason))
            elif ruling["verdict"] == "dismissed":
                continue
            else:
                out.append(AdjudicatedLeak(finding, ruling["verdict"], ruling.get("reason", "")))
        return out

    @staticmethod
    def _parse(content: str) -> tuple[list[dict], bool]:
        try:
            start, end = content.index("{"), content.rindex("}")
            data = json.loads(content[start : end + 1])
            rulings = data.get("rulings", [])
            return ([r for r in rulings if isinstance(r, dict) and "fact_id" in r], True)
        except (ValueError, json.JSONDecodeError, AttributeError):
            return [], False
