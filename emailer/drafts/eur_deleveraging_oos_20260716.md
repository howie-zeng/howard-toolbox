Hi,

Following up on the EUR deleveraging work, I have completed the out-of-sample evaluation.

**Bottom line:** the new model is modestly better overall, with an average weekly MAE of 0.764 px versus 0.779 px for Prod. It wins 13 of 22 weeks, including 9 of the most recent 12. The rating results are mixed: most of the improvement comes from B-rated bonds, BB is roughly flat, and BBB is worse.

**Recommendation: keep the current two-layer setup and the logit-transformed price target.**

The model combines a long-term GAM trained on market color and our internal trades/marks using a 180-day half-life, with a short-term residual overlay using a 30-day half-life. The overlay is capped at +/-5 px, and all ten features have monotonicity constraints.

I also tested fitting raw price directly. It is easier to interpret, but in that target comparison it performed about 10% worse out of sample: MAE increased from 0.67 to 0.75. Most of the loss was near par, where the logit transform gives the model more resolution.

For validation, I retrained the model weekly from February 12 through July 10 and scored only the following week's bonds. The test covers 22 weekly anchors and 676 prints, with each print evaluated at its actual listing type.

**Long-term fit**

![](2026-07-15-12-34-49.png)

**Short-term fit**

![](2026-07-15-12-34-31.png)

**Pooled MAE by rating**

| Rating | Prints | Prod | New | Better |
|---|---:|---:|---:|---|
| BBB | 248 | 0.335 | 0.441 | Prod |
| BB | 322 | 0.874 | 0.860 | New |
| B | 106 | 1.451 | 1.262 | New |

**Weekly out-of-sample results**

| Week | Prints | Prod | New | Better |
|---|---:|---:|---:|---|
| 02-12 | 46 | 0.688 | 0.829 | Prod |
| 02-19 | 58 | 0.489 | 0.642 | Prod |
| 02-26 | 58 | 0.575 | 0.628 | Prod |
| 03-05 | 37 | 0.477 | 0.434 | New |
| 03-12 | 26 | 0.994 | 0.865 | New |
| 03-19 | 25 | 0.595 | 1.024 | Prod |
| 03-26 | 22 | 0.872 | 1.215 | Prod |
| 04-02 | 7 | 0.475 | 0.288 | New |
| 04-09 | 38 | 0.752 | 0.720 | New |
| 04-16 | 22 | 0.602 | 0.935 | Prod |
| 04-23 | 29 | 1.014 | 0.995 | New |
| 04-30 | 32 | 1.187 | 1.016 | New |
| 05-07 | 29 | 1.054 | 1.074 | Prod |
| 05-14 | 32 | 0.807 | 0.601 | New |
| 05-21 | 29 | 0.477 | 0.612 | Prod |
| 05-28 | 25 | 1.115 | 0.822 | New |
| 06-04 | 9 | 1.253 | 0.875 | New |
| 06-11 | 42 | 0.989 | 0.799 | New |
| 06-18 | 40 | 0.894 | 0.867 | New |
| 06-25 | 38 | 0.840 | 0.766 | New |
| 07-02 | 20 | 0.551 | 0.339 | New |
| 07-09 | 12 | 0.436 | 0.473 | Prod |
| **Average** |  | **0.779** | **0.764** | **New: 13/22** |

Happy to walk through any of the weeks or slices in more detail.
