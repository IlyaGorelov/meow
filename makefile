.PHONY: runt runm clean

runt: out
	python3 src/translator.py meow/hello_username.meow out/out.bin

runm: out
	python3 src/machine.py out/out.bin out/out_data.bin input.txt

out:
	mkdir -p out

clean:
	rm -rf out