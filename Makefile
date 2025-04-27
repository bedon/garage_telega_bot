.PHONY: setup run stop

setup:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

run:
	. venv/bin/activate && nohup python bot.py > bot.log 2>&1 & echo $$! > bot.pid

stop:
	kill $$(cat bot.pid) || true
	rm -f bot.pid

clean:
	rm -rf venv
	rm -f bot.log bot.pid 