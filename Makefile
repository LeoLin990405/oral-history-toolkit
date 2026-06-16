SKILL := oral-history-master

.PHONY: test lint help

help:
	@echo "make test   跑单元测试"
	@echo "make lint   语法检查 (py_compile)"

test:
	cd $(SKILL) && python3 -m unittest discover tests -v

lint:
	python3 -m py_compile $(SKILL)/scripts/*.py $(SKILL)/tests/*.py
	@echo "✓ py_compile OK"
