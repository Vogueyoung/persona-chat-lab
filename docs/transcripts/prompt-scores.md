# Prompt-structure scores

Scored by `scripts/eval_prompts.py` against the 12 criteria in `evals/rubrics.md`. Each row is one (character × version) system prompt. 18 points possible per prompt.

## Summary (mean across 3 characters)

| Version | Total | Per-character | As % of 18 |
|---------|------:|--------------:|-----------:|
| `v1` | 36/54 | 12.0/18 | 66.7% |
| `v2` | 54/54 | 18.0/18 | 100.0% |

**Delta `v1` → `v2`:** +18 absolute, +6.0 per prompt, +33.3 percentage points.

## Per-criterion breakdown

| Criterion | Max | `v1` | `v2` |
|---|---:|---:|---:|
| 1_identity | 1 | 3/3 | 3/3 |
| 2_personality | 1 | 3/3 | 3/3 |
| 3_style_tone | 1 | 3/3 | 3/3 |
| 4_backstory | 1 | 3/3 | 3/3 |
| 5_ai_reveal_guardrail | 2 | 6/6 | 6/6 |
| 6_forbidden_list | 1 | 3/3 | 3/3 |
| 7_few_shot_count | 3 | 9/9 | 9/9 |
| 8_few_shot_primacy | 2 | 0/6 | 6/6 |
| 9_guardrails_separated | 2 | 0/6 | 6/6 |
| 10_real_world_handling | 2 | 0/6 | 6/6 |
| 11_rag_grounding_wording | 1 | 3/3 | 3/3 |
| 12_length_band | 1 | 3/3 | 3/3 |

## Per-character detail — `v1`

| Character | 1_identity | 2_personality | 3_style_tone | 4_backstory | 5_ai_reveal_guardrail | 6_forbidden_list | 7_few_shot_count | 8_few_shot_primacy | 9_guardrails_separated | 10_real_world_handling | 11_rag_grounding_wording | 12_length_band | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aria_knight | 1 | 1 | 1 | 1 | 2 | 1 | 3 | 0 | 0 | 0 | 1 | 1 | 12 |
| nori_librarian | 1 | 1 | 1 | 1 | 2 | 1 | 3 | 0 | 0 | 0 | 1 | 1 | 12 |
| zen_hacker | 1 | 1 | 1 | 1 | 2 | 1 | 3 | 0 | 0 | 0 | 1 | 1 | 12 |

## Per-character detail — `v2`

| Character | 1_identity | 2_personality | 3_style_tone | 4_backstory | 5_ai_reveal_guardrail | 6_forbidden_list | 7_few_shot_count | 8_few_shot_primacy | 9_guardrails_separated | 10_real_world_handling | 11_rag_grounding_wording | 12_length_band | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aria_knight | 1 | 1 | 1 | 1 | 2 | 1 | 3 | 2 | 2 | 2 | 1 | 1 | 18 |
| nori_librarian | 1 | 1 | 1 | 1 | 2 | 1 | 3 | 2 | 2 | 2 | 1 | 1 | 18 |
| zen_hacker | 1 | 1 | 1 | 1 | 2 | 1 | 3 | 2 | 2 | 2 | 1 | 1 | 18 |
