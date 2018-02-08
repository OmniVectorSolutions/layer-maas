.PHONY: test
test:
	@tox

build:
	@charm build -rl DEBUG
