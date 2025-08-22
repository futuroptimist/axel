.PHONY: install hillclimb hillclimb-execute test
install:
	python -m pip install -r requirements.txt
hillclimb:
	python .axel/hillclimb/scripts/axel.py hillclimb --runs 4 --dry-run
hillclimb-execute:
	python .axel/hillclimb/scripts/axel.py hillclimb --runs 4 --execute
test:
	pytest --cov=axel --cov=tests
