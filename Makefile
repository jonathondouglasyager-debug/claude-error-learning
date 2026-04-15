.PHONY: test test-verbose

.DEFAULT_GOAL := test

test:
	python3 -m unittest discover tests

test-verbose:
	python3 -m unittest discover tests -v
