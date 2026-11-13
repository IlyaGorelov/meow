import os
import sys
import yaml

from lexer import Lexer
from parser import Parser
from generator import CodeGenerator
from isa import Assembler
from data_generator import DataGenerator
    
def write_ast_to_yaml(ast, filename):
    ignored_keys = {"line", "char"}

    def filter_dict(obj):
        if isinstance(obj, dict):
            return {
                key: filter_dict(value)
                for key, value in obj.items()
                if key not in ignored_keys
            }

        if isinstance(obj, list):
            return [filter_dict(item) for item in obj]

        return obj
    
    with open(filename, "w", encoding="utf-8") as file:
        yaml.dump(
            filter_dict(ast),
            file,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False
        )

def main(source, target):
    if not target.endswith(".bin"):
        return
    
    os.makedirs(os.path.dirname(os.path.abspath(target)) or ".", exist_ok=True)
    
    with open(source, encoding="utf-8") as f:
        source = f.read()

    tokens = Lexer(source).tokenize()

    ast = Parser(tokens).parse()
    write_ast_to_yaml(ast, target.replace(".bin", "_AST.yaml"))

    code = CodeGenerator().generate(ast)

    binary = Assembler.to_bytes(code)

    binary_data = DataGenerator().generate(code)

    hex = Assembler.to_hex(code)


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