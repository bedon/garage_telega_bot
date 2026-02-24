.PHONY: setup run stop test clean clean-all

setup:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

run:
	. venv/bin/activate && nohup python src/main.py --instance=dude > bot.log 2>&1 & echo $$! > bot_dude.pid

stop:
	pkill -f "python src/main.py --instance=dude"

clean:
	rm -rf venv
	rm -f bot.log bot.pid
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete

clean-all: clean
	rm -rf venv
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

git:
	git pull

deploy: git stop run
	@echo "Deployed"


dev:
	python src/main.py

# Run with verbose logging (LOG_LEVEL=INFO) for debugging
dev-verbose:
	LOG_LEVEL=INFO python src/main.py

test:
	python -m pytest \
		--cov=src \
		--cov-report=term-missing \
		--cov-report=html \
		-v \
		tests/ 
