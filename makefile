.PHONY: run clean

run: bin
	python3 src/translator.py meow/sort.meow bin/out.bin

bin:
	mkdir -p bin

clean:
	rm -rf bin