# Retrieval results (41 answerable questions, text-embedding-3-small, k=5)

| Date | Change | Strategy | R@1 | R@5 | MRR |
|---|---|---|---|---|---|
| 26 Oct | baseline | fixed_1000_200 | 0.83 | 0.98 | 0.89 |
| 26 Oct | baseline | recursive_1000_200 | 0.68 | 0.93 | 0.79 |
| 26 Oct | named 311 unnamed labels + generic-name scoring | fixed_1000_200 | 0.85 | 0.98 | 0.91 |
| 26 Oct | named 311 unnamed labels + generic-name scoring | recursive_1000_200 | 0.78 | 0.95 | 0.86 |

Decision: keep fixed_1000_200.