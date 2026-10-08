.PHONY: setup demo train-demo test
setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

demo:
	.venv/bin/python scripts/bootstrap_demo_data.py

train-demo: demo
	.venv/bin/python scripts/train_core.py --input data/processed/demo_core.csv --version demo-0.1.0

test:
	.venv/bin/python -m pytest -q
