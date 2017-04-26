.DEFAULT_GOAL := init

init:
	bash install-dep.sh

test:
	cd test && python run_tests.py

docs:
	cd escape/doc && bash generate-doc.sh

kill:
	bash tools/kill-escape.sh

clean:
	sudo -S python escape.py -x

stat:
	bash tools/gen_stat.sh

.PHONY: init test docs kill clean stat
