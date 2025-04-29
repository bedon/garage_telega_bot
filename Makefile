.PHONY: setup run stop test

setup:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

run:
	. venv/bin/activate && nohup python src/main.py > bot.log 2>&1 & echo $$! > bot.pid

stop:
	pkill -f main.py

clean:
	rm -rf venv
	rm -f bot.log bot.pid 

dev:
	python src/main.py

test:
	python -m pytest \
		--cov=src \
		--cov-report=term-missing \
		--cov-report=html \
		-v \
		tests/ 