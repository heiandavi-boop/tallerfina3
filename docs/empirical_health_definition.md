# Empirical Health Definition

## Decision

Health training is blocked for DSLIB v3.4. No consistent observed Health or final-status label is documented across the 231 projects. The dataset contains project-control/EVM measurements and final duration/cost fields, but a common outcome class and validated threshold policy are not available in the published files.

## Variables and label policy

No label is created. No `Healthy`, `At Risk`, or `Critical` thresholds are applied to delay, cost, SPI, CPI, schedule variance, or cost variance. Selecting thresholds to optimize this dataset's TEST would leak evaluation outcomes into label design and is explicitly prohibited.

An operational Health view may be derived from Delay and Cost only after a separate evidence-based definition is agreed and documented. That derived layer is not implemented and would not be a supervised DSLIB Health model. Team Health remains the existing deterministic operational heuristic; DSLIB does not train or calibrate it.

## Evidence required to revisit

1. A publisher-defined or independently justified outcome label tied to observed project outcomes.
2. Pre-registered variables, thresholds, units, and project inclusion criteria.
3. Sensitivity analysis specified before model selection.
4. Project-grouped train/validation/test evaluation with TEST frozen.
5. Evidence that no snapshot feature contains information observed after its timestamp.

Until these conditions are met, `health` has zero empirical training projects/snapshots and the API returns Health as unavailable for PRUNIN Empirical.