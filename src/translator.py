import os
import sys

import yaml

from data_generator import DataGenerator
from generator import CodeGenerator
from isa import Assembler
from lexer import Lexer
from parser import Parser


def write_ast_to_yaml(ast, filename):
    ignored_keys = {"line", "char"}

    def filter_dict(obj):
        if isinstance(obj, dict):
            return {key: filter_dict(value) for key, value in obj.items() if key not in ignored_keys}

        if isinstance(obj, list):
            return [filter_dict(item) for item in obj]

        return obj

    with open(filename, "w", encoding="utf-8") as file:
        yaml.dump(filter_dict(ast), file, allow_unicode=True, sort_keys=False, default_flow_style=False)


def main(source, target):
    if not target.endswith(".bin"):
        return

    os.makedirs(os.path.dirname(os.path.abspath(target)) or ".", exist_ok=True)

    with open(source, encoding="utf-8") as f:
        source = f.read()

    tokens = Lexer(source).tokenize()

    ast = Parser(tokens).parse()
    write_ast_to_yaml(ast, target.replace(".bin", "_AST.yml"))

    code = CodeGenerator(ast).generate()

    code = CodeGenerator.resolve_data_references(code)
    code = CodeGenerator.resolve_code_addresses(code)

    binary = Assembler.to_bytes(code)

    hex_repr = Assembler.to_hex(code)

    binary_data = DataGenerator().generate(code)
    hex_data = DataGenerator().to_hex(binary_data)

    with open(target, "wb") as f:
        f.write(binary)
    with open(target + ".hex", "w") as f:
        f.write(hex_repr)
    with open(target.replace(".bin", "_data.bin"), "wb") as f:
        f.write(binary_data)
    with open(target.replace(".bin", "_data.bin.hex"), "w") as f:
        f.write(hex_data)


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)
