#!/usr/bin/python3
"""Транслятор brainfuck в машинный код.
"""

import os
import sys

from lexer import Lexer
from parser import Parser
from semantic_analyzer import SemanticAnalyzer
from generator import CodeGenerator

def translate(soource):
    return

def main(source, target):
    with open(source, encoding="utf-8") as f:
        source = f.read()

    tokens = Lexer(source).tokenize()

    ast = Parser(tokens).parse()

    SemanticAnalyzer().analyze(ast)

    result = CodeGenerator().generate(ast)

    # Убедимся, что каталог назначения существует
    os.makedirs(os.path.dirname(os.path.abspath(target)) or ".", exist_ok=True)

    with open(target, "w") as f:
            f.write(result)

    # Запишим выходные файлы
    # if target.endswith(".bin"):
    #     with open(target, "wb") as f:
    #         f.write(res)
    #     with open(target + ".hex", "w") as f:
    #         f.write(res)

    # Обратите внимание, что память данных не экспортируется в файл, так как
    # в случае brainfuck она может быть инициализирована только 0.
    # print("source LoC:", len(source.split("\n")), "code instr:", len(code))


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)