.PHONY: run clean

run: bin
	src/translator.py meow/test.meow bin/out.bin

bin:
	mkdir -p bin

clean:
	rm -rf bin