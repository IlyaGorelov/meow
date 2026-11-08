import os
import sys

from lexer import Lexer
from parser import Parser
from generator import CodeGenerator
from isa import Assembler
from data_generator import DataGenerator


def main(source, target):
    with open(source, encoding="utf-8") as f:
        source = f.read()

    tokens = Lexer(source).tokenize()

    ast = Parser(tokens).parse()

    code = CodeGenerator().generate(ast)

    binary = Assembler.to_bytes(code)

    binary_data = DataGenerator().generate(code)

    hex = Assembler.to_hex(code)

    # Убедимся, что каталог назначения существует
    os.makedirs(os.path.dirname(os.path.abspath(target)) or ".", exist_ok=True)

    # Запишим выходные файлы
    if target.endswith(".bin"):
        with open(target, "wb") as f:
            f.write(binary)
        with open(target.replace(".bin", "_data.bin"), "wb") as f:
            f.write(binary_data)
        with open(target + ".hex", "w") as f:
            f.write(hex)
        with open(target + ".asm", "w") as f:
            f.write(code)

if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)