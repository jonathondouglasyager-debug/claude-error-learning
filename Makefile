.PHONY: test test-verbose

test:
	python3 -m unittest discover tests

test-verbose:
	python3 -m unittest discover tests -v
