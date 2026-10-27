# Empirical Training Report

- Version: **1.0.1-empirical**
- Run: `20261027T233652Z-2c9fedbf`
- Dataset: DSLIB / PSLIB v3.4 (229 projects with baseline workbooks)
- Dataset SHA-256: `19f87632c589f5d49f72b5f071992efc6379df2beb35f1efd3a60ac1381dc277`
- Seed: 42; split by project_id; test reserved before model selection.
- Split sizes by target: {'delay': {'train': 90, 'validation': 30, 'test': 31}, 'cost': {'train': 90, 'validation': 30, 'test': 31}}.
- Health: not trained; no consistent observed Health label is available.
- Features: planned duration (days), BAC; no synthetic features or inferred categories.

## Dataset Audit Coverage

| Variable | Projects available | Coverage |
|---|---:|---:|
| project Excel workbook | 231 | 100.00% |
| baseline schedule | 229 | 99.13% |
| actual/control data | 156 | 67.53% |
| complete EVM (EV/PV/AC) | 116 | 50.22% |
| BAC > 0 | 196 | 84.85% |
| PV numeric | 116 | 50.22% |
| EV numeric | 116 | 50.22% |
| AC numeric | 155 | 67.10% |
| planned duration > 0 | 231 | 100.00% |
| actual duration observed | 155 | 67.10% |
| dated tracking information | 154 | 66.67% |
| final cost observed | 153 | 66.23% |
| incomplete project | 82 | 35.50% |

Early prediction: **not_available**. Leakage-cleared EVM candidates: 13 projects / 13 snapshots per target, insufficient for reliable cutoff evaluation.

## Results

### Delay

- Projects: 151; target: observed final actual duration - planned duration; unit: days
- Selected on validation MAE: median_baseline
- Validation candidates (MAE / RMSE / R²):
  - median_baseline: 31.533333333333335 / 69.66012728479136 / -0.113044648400346
  - ridge: 32.774719069039996 / 57.26134416724388 / 0.2479146386811104
  - random_forest: 42.12469464285717 / 69.70933225835026 / -0.1146176192603161
  - lightgbm: 33.18518870611865 / 57.85273611280886 / 0.232299425707703
- Test: MAE 30.7097, RMSE 45.9453, R² -0.0339253
- Median baseline test MAE: 30.7097
- Test MAE bootstrap interval: [19.740322580646055, 43.24193548387164]

### Cost

- Projects: 151; target: (observed final actual cost - BAC) / BAC; unit: ratio of BAC
- Selected on validation MAE: median_baseline
- Validation candidates (MAE / RMSE / R²):
  - median_baseline: 0.09621241802973318 / 0.1706200339989955 / -0.018491893743313836
  - ridge: 0.14373627680533016 / 0.20810235977465108 / -0.515135724459105
  - random_forest: 0.16752643047555532 / 0.2491413220757455 / -1.1716461276540469
  - lightgbm: 0.17876845851043935 / 0.25714239062998906 / -1.313368846772554
- Test: MAE 0.115703, RMSE 0.277471, R² -0.0317475
- Median baseline test MAE: 0.115703
- Test MAE bootstrap interval: [0.05171297156013941, 0.2109822770337502]

## Limitations

- Small, heterogeneous observational sample; no causal claims or external generalization established.
- Only project-baseline features were used; temporal EVM snapshots are too sparse for training in this release.
- The selected median estimator has no feature importance or local sensitivity drivers.
- Delay and cost metrics describe DSLIB's own target/split and cannot be ranked head-to-head against the academic dataset.
