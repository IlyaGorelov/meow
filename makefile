.PHONY: run clean

run: bin
	python3 src/translator.py meow/cat.meow bin/out.bin

bin:
	mkdir -p bin

clean:
	rm -rf bin