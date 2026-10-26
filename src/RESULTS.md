| 26 Oct | hybrid: Postgres ts_rank + vector, RRF | fixed_1000_200 | 0.54 | 0.83 | 0.64 |
| 26 Oct | hybrid: BM25 + vector, RRF (kw weight 1.0) | fixed_1000_200 | 0.59 | 0.90 | 0.71 |
| 26 Oct | hybrid: BM25 + vector, RRF (kw weight 0.3) | fixed_1000_200 | 0.73 | 0.93 | 0.81 |

Decision: keep vector-only. ts_rank has no IDF (common words dominate); BM25 helps but the drug-name chunk header already gives vector search the exact-match signal.