.PHONY: install hillclimb hillclimb-execute
install:
	python -m pip install -r requirements.txt
hillclimb:
	python .axel/hillclimb/scripts/axel.py hillclimb --runs 4 --dry-run
hillclimb-execute:
	python .axel/hillclimb/scripts/axel.py hillclimb --runs 4 --execute
