| 26 Oct | hybrid: Postgres ts_rank + vector, RRF | fixed_1000_200 | 0.54 | 0.83 | 0.64 |
| 26 Oct | hybrid: BM25 + vector, RRF (kw weight 1.0) | fixed_1000_200 | 0.59 | 0.90 | 0.71 |
| 26 Oct | hybrid: BM25 + vector, RRF (kw weight 0.3) | fixed_1000_200 | 0.73 | 0.93 | 0.81 |
| 26 Oct | Cohere rerank-v3.5 over top-20 vector candidates | fixed_1000_200 | 0.90 | 1.00 | 0.94 |
| 26 Oct | vector, k=5 | 0.95 | 0.93 | 0.07 | 5.6s | $0.00102 |
| 26 Oct | vector + Cohere rerank, k=5 | 0.93 | 0.88 | 0.12 | 6.5s | $0.00102 |
| 27 Oct | vector + Cohere rerank, k=3 | 0.95 | 0.95 | 0.05 | 5.2s | $0.00084 |

Decision: ship rerank + k=3. Same quality (differences within run-to-run noise), 18% cheaper, faster median.
Cost fell 18% not 40% because output/reasoning tokens dominate gpt-5-mini cost.
