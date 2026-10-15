.PHONY: install data bench test clean
install:
	pip install -r requirements.txt
data:
	python3 experiments/run_all.py --download-only
bench:
	python3 experiments/run_all.py
test:
	pytest -q
clean:
	rm -rf data/*.csv results/*
