
.PHONY: all format lint test test-update-golden runt runm clean

all: format lint test

format:
	poetry run ruff format src/ test/

lint:
	poetry run ruff check --fix src/ test/

test:
	poetry run pytest test/ -v

test-update-golden:
	poetry run pytest test/ -v --update-goldens

runt: out
	python3 src/translator.py examples/cat.meow out/out.bin

runm: out
	python3 src/machine.py out/out.bin out/out_data.bin input.txt -o char

out:
	mkdir -p out

clean:
	rm -rf out
