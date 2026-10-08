# Delay experiment

Selection used TRAIN to fit and VALIDATION project-level MAE/RMSE/R² to compare candidates.
TEST was not used to tune candidates; only the frozen selected candidate is evaluated after selection.
Selected candidate: median_train_project_baseline
Decision: candidate selected on validation only; automatic promotion disabled
Final TEST MAE: 27.8503 days; RMSE 38.9988; R² -0.0142.
The experiment never overwrites artifacts/0.9.0-academic/delay_days.joblib.
