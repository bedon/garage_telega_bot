.PHONY: setup install run stop restart test clean clean-all git deploy dev dev-verbose ig-login ig-check update-ytdlp

PY = venv/bin/python
PID = bot_dude.pid

setup:
	python3 -m venv venv
	$(MAKE) install

install:
	venv/bin/pip install -U -r requirements.txt -r requirements-dev.txt

run:
	nohup $(PY) src/main.py --instance=dude > bot.log 2>&1 & echo $$! > $(PID)

stop:
	-pkill -f "src/main.py --instance=dude"
	rm -f $(PID)

restart: stop run

git:
	git pull

# yt-dlp is upgraded on every deploy: Instagram/TikTok extractors break often.
deploy: git install stop run
	@echo "Deployed"

update-ytdlp:
	venv/bin/pip install -U yt-dlp instaloader

# Log in to Instagram from THIS machine (run on the server over SSH).
ig-login:
	$(PY) src/ig_login.py

ig-check:
	$(PY) src/ig_login.py --check

dev:
	$(PY) src/main.py

# Run with verbose logging (LOG_LEVEL=INFO) for debugging
dev-verbose:
	LOG_LEVEL=INFO $(PY) src/main.py

test:
	$(PY) -m pytest

clean:
	rm -f bot.log $(PID)
	rm -rf .pytest_cache .coverage htmlcov
	find . -path ./venv -prune -o -type d -name "__pycache__" -exec rm -rf {} +

clean-all: clean
	rm -rf venv .mypy_cache .ruff_cache
