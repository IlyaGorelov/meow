.PHONY: run clean

run: bin
	src/translator.py meow/sort.meow bin/out.bin

bin:
	mkdir -p bin

clean:
	rm -rf bin