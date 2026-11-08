.PHONY: run clean

run: bin
	python3 src/translator.py meow/hello.meow bin/out.bin

bin:
	mkdir -p bin

clean:
	rm -rf bin