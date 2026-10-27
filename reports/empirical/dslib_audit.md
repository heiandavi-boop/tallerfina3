# DSLIB v3.4 Dataset Audit

- Projects found across analysis/workbooks: **231**
- Analysis-sheet projects: **231**
- Per-project Excel workbooks: **231**
- License: **not specified by publisher**
- Health training: **blocked** until a defensible, pre-registered label is available

## Coverage

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

## Candidate Sample Counts

| Target | Baseline projects | Snapshots used for training |
|---|---:|---:|
| Health | 0 | 0 |
| Delay | 151 | 0 |
| Cost | 151 | 0 |

Delay candidate: actual duration minus planned duration, in days; negative values mean early completion.
Cost candidate: (actual cost - BAC) / BAC; negative values mean below-budget execution.
The temporal EVM candidate count is reported separately; the initial empirical models use one baseline row per project.

## Limitations

- The analysis sheet includes final outcomes and summary metrics; these must never be used as snapshot features.
- Project-control sheets vary in availability and completeness.
- No Health label is inferred and no model is trained by this audit.
- The publisher's repository does not state a data license.
