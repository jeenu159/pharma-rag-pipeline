| 26 Oct | hybrid: Postgres ts_rank + vector, RRF | fixed_1000_200 | 0.54 | 0.83 | 0.64 |
| 26 Oct | hybrid: BM25 + vector, RRF (kw weight 1.0) | fixed_1000_200 | 0.59 | 0.90 | 0.71 |
| 26 Oct | hybrid: BM25 + vector, RRF (kw weight 0.3) | fixed_1000_200 | 0.73 | 0.93 | 0.81 |
| 26 Oct | Cohere rerank-v3.5 over top-20 vector candidates | fixed_1000_200 | 0.90 | 1.00 | 0.94 |
| 26 Oct | vector, k=5 | 0.95 | 0.93 | 0.07 | 5.6s | $0.00102 |
| 26 Oct | vector + Cohere rerank, k=5 | 0.93 | 0.88 | 0.12 | 6.5s | $0.00102 |
| 27 Oct | vector + Cohere rerank, k=3 | 0.95 | 0.95 | 0.05 | 5.2s | $0.00084 |
| 27 Oct | rerank, k=3, + neighbour expansion (±1 chunk) | 0.90 | 0.88 | 0.10 | 3.9s* | $0.00105 |

Decision: neighbours off. Fixed the perphenazine 5618 gap, but ~3x context caused embellishment (4 unfaithful) and one lost-in-the-middle miss (Q21); +25% cost.
*Latency not comparable across runs: API time varies by time of day; needs repeated runs.
Note: run-to-run noise is ~1-2 questions (0.02-0.05); differences smaller than that are not conclusions.

## Judge validation (2 Nov, run answers_20261102_1216, 41 answerable questions)

Second judge: Claude (different model family), labelled independently.
- Faithfulness agreement: 41/41 (100%). Both flagged Q3, Q6, Q20, Q38.
- Correctness agreement: 40/41 (98%). Disagreement: Q6 (GPT-5: yes, Claude: partial; prednisone answer misattributes replacement therapy).
- All 4 unfaithful answers are embellishments (added mechanism, advice, or misattribution), not fabricated facts.