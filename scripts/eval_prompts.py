"""Prompt-structure linter.

Scores each (character × prompt_version) against the structural rubric
defined in evals/rubrics.md. Runs without an API key — the whole point
is that prompt engineering quality should be auditable without spending
tokens.

Run:
    uv run python -m scripts.eval_prompts
    uv run python -m scripts.eval_prompts --write docs/transcripts/prompt-scores.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.models.schemas import Character, RetrievalHit
from app.prompts.character_prompts import available_versions, render_system_prompt
from app.services.character_loader import list_characters

# A single placeholder hit so the RAG block renders during scoring.
# Without this, criterion 11 (RAG grounding wording) would always read 0
# even for a renderer that does have the correct wording — the block only
# appears at runtime when retrieval returned something.
_FIXTURE_HIT = [RetrievalHit(text="placeholder lore fact.", source="probe.md", score=1.0)]


# Criterion: (name, weight, check_fn(prompt_text, character) -> (0..weight))
def _score_prompt(prompt: str, character: Character) -> dict[str, int]:
    def section_present(headings: list[str]) -> bool:
        return any(h in prompt for h in headings)

    idx = lambda h: prompt.find(h)  # noqa: E731

    scores: dict[str, int] = {}
    scores["1_identity"] = 1 if section_present(["# 역할"]) else 0
    scores["2_personality"] = 1 if section_present(["# 성격"]) else 0
    scores["3_style_tone"] = (
        1 if section_present(["# 말투/스타일", "# 말투·톤"]) else 0
    )
    scores["4_backstory"] = 1 if section_present(["# 배경 이야기"]) else 0
    scores["5_ai_reveal_guardrail"] = 2 if ("AI" in prompt and "언어모델" in prompt) else 0
    scores["6_forbidden_list"] = 1 if section_present(["# 금지 주제", "# 절대 규칙"]) else 0

    # 7: few-shot example count, up to 3
    example_count = prompt.count("User:")
    scores["7_few_shot_count"] = min(example_count, 3)

    # 8: primacy — few-shot positioned before personality description
    idx_examples = idx("# 대화 예시")
    idx_personality = idx("# 성격")
    primacy = (
        idx_examples != -1
        and idx_personality != -1
        and idx_examples < idx_personality
    )
    scores["8_few_shot_primacy"] = 2 if primacy else 0

    # 9: identity guardrail separated from topic guardrail
    has_identity_section = "# 정체성 보호" in prompt
    has_forbidden_section = "# 금지 주제" in prompt
    scores["9_guardrails_separated"] = 2 if (has_identity_section and has_forbidden_section) else 0

    # 10: explicit real-world question handling
    scores["10_real_world_handling"] = 2 if "# 현실 세계 질문 처리" in prompt else 0

    # 11: RAG grounding discipline (wording that survives even if no hits present)
    rag_wording = ("지어내지 않" in prompt) or ("자료에 없는" in prompt) or ("자료에 있는" in prompt)
    scores["11_rag_grounding_wording"] = 1 if rag_wording else 0

    # 12: length within reasonable band (500-2500 chars)
    scores["12_length_band"] = 1 if 500 <= len(prompt) <= 2500 else 0

    return scores


MAX_PER_CRITERION = {
    "1_identity": 1,
    "2_personality": 1,
    "3_style_tone": 1,
    "4_backstory": 1,
    "5_ai_reveal_guardrail": 2,
    "6_forbidden_list": 1,
    "7_few_shot_count": 3,
    "8_few_shot_primacy": 2,
    "9_guardrails_separated": 2,
    "10_real_world_handling": 2,
    "11_rag_grounding_wording": 1,
    "12_length_band": 1,
}
MAX_TOTAL = sum(MAX_PER_CRITERION.values())  # 18


def _pct(n: int, d: int) -> str:
    return f"{(n / d * 100):.1f}%" if d else "n/a"


def run() -> str:
    characters = list_characters()
    versions = available_versions()

    # Per-version × per-character scores
    per_char: dict[str, dict[str, dict[str, int]]] = {v: {} for v in versions}
    for v in versions:
        for ch in characters:
            # Score against the RAG-on rendering so criterion 11 can be evaluated.
            prompt = render_system_prompt(ch, rag_hits=_FIXTURE_HIT, version=v)
            per_char[v][ch.id] = _score_prompt(prompt, ch)

    # Aggregate
    version_totals: dict[str, int] = {}
    for v in versions:
        total = sum(sum(sc.values()) for sc in per_char[v].values())
        version_totals[v] = total

    # Build markdown report
    lines: list[str] = []
    lines.append("# Prompt-structure scores")
    lines.append("")
    lines.append(
        "Scored by `scripts/eval_prompts.py` against the 12 criteria in "
        "`evals/rubrics.md`. Each row is one (character × version) system "
        "prompt. 18 points possible per prompt."
    )
    lines.append("")

    # Summary table first — this is the number the user will cite in interviews.
    lines.append("## Summary (mean across 3 characters)")
    lines.append("")
    lines.append("| Version | Total | Per-character | As % of 18 |")
    lines.append("|---------|------:|--------------:|-----------:|")
    for v in versions:
        total = version_totals[v]
        per_char_mean = total / len(characters)
        lines.append(
            f"| `{v}` | {total}/{MAX_TOTAL * len(characters)} | "
            f"{per_char_mean:.1f}/{MAX_TOTAL} | {_pct(int(per_char_mean), MAX_TOTAL)} |"
        )
    if len(versions) >= 2:
        # Show the v2 − v1 delta explicitly.
        v1, v2 = versions[0], versions[-1]
        delta = version_totals[v2] - version_totals[v1]
        delta_per_char = delta / len(characters)
        lines.append("")
        lines.append(
            f"**Delta `{v1}` → `{v2}`:** +{delta} absolute, "
            f"+{delta_per_char:.1f} per prompt, "
            f"+{(delta_per_char / MAX_TOTAL * 100):.1f} percentage points."
        )
    lines.append("")

    # Per-criterion breakdown
    lines.append("## Per-criterion breakdown")
    lines.append("")
    header = "| Criterion | Max | " + " | ".join(f"`{v}`" for v in versions) + " |"
    sep = "|---|---:|" + "---:|" * len(versions)
    lines.append(header)
    lines.append(sep)
    for crit, maxpts in MAX_PER_CRITERION.items():
        row = [crit, str(maxpts)]
        for v in versions:
            # sum this criterion across all characters
            s = sum(per_char[v][ch.id][crit] for ch in characters)
            row.append(f"{s}/{maxpts * len(characters)}")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Per-character detail
    for v in versions:
        lines.append(f"## Per-character detail — `{v}`")
        lines.append("")
        lines.append("| Character | " + " | ".join(MAX_PER_CRITERION.keys()) + " | Total |")
        lines.append("|---|" + "---:|" * (len(MAX_PER_CRITERION) + 1))
        for ch in characters:
            sc = per_char[v][ch.id]
            row = [ch.id] + [str(sc[k]) for k in MAX_PER_CRITERION.keys()]
            row.append(str(sum(sc.values())))
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        type=Path,
        default=None,
        help="Write the report to this path instead of stdout.",
    )
    args = parser.parse_args()

    report = run()
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(report, encoding="utf-8")
        print(f"[eval] Wrote {args.write}")
    else:
        print(report)


if __name__ == "__main__":
    main()
