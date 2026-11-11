# Results

## Reading and writing speed by prompt length

| tag             |   target_tokens |   prompt_tokens |   reading_seconds |   reading_tok_per_s |   writing_tok_per_s |
|:----------------|----------------:|----------------:|------------------:|--------------------:|--------------------:|
| kaggle-Q4       |            2000 |            2029 |               1.5 |              1366   |                57.4 |
| kaggle-Q4       |            8000 |            8074 |               4.9 |              1650.8 |                55.7 |
| kaggle-Q4       |           16000 |           16136 |              10   |              1608.9 |                53.3 |
| kaggle-Q4       |           30000 |           30241 |              19.8 |              1528.3 |                49.7 |
| laptop-IQ3      |            2000 |            2029 |              81.6 |                24.9 |                 2.6 |
| laptop-IQ3      |            8000 |            8074 |             376.7 |                21.4 |                 1.9 |
| laptop-Q2       |            2000 |            2029 |              86.4 |                23.5 |                 2.5 |
| laptop-Q2       |            8000 |            8074 |             381.5 |                21.2 |                 1.8 |
| laptop-Q2-clean |            2000 |            2029 |             140.6 |                14.4 |                 0.9 |

## Seconds per agent step (replay)

| setup                  |   steps |   avg_prompt_tokens |   reading_s |   writing_s |   step_s |   reading_share_pct |
|:-----------------------|--------:|--------------------:|------------:|------------:|---------:|--------------------:|
| kaggle-Q4 (cold)       |      12 |             12538.4 |         9   |         1.6 |     10.6 |                  85 |
| kaggle-Q4 (warm)       |      12 |              1463   |         1.6 |         3   |      4.6 |                  35 |
| laptop-Q2-clean (cold) |       4 |             11885.2 |       865.3 |       113.2 |    978.4 |                  88 |
| laptop-Q2-clean (warm) |       4 |              1428.8 |       120.7 |        56.2 |    176.8 |                  68 |
| laptop-Q2-rerun (cold) |       4 |             11885.2 |      1182.6 |       121.6 |   1304.1 |                  91 |
| laptop-Q2-rerun (warm) |       4 |              1423.2 |       181.5 |        88.1 |    269.6 |                  67 |

## Live agent runs (real time spent per task)

| tag       |   tasks |   avg_task_minutes |   reading_share_pct |
|:----------|--------:|-------------------:|--------------------:|
| laptop-Q2 |       3 |              157.8 |                27.7 |
