import contextlib
import io
import logging
import os
import tempfile

import pytest
import yaml

import machine
import translator

MAX_LOG = 4000


@pytest.mark.golden_test("golden/*.yml")
def test_translator_and_machine(golden, caplog):
    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdirname:
        source = os.path.join(tmpdirname, "source.meow")
        input_stream = os.path.join(tmpdirname, "input.txt")

        target = os.path.join(tmpdirname, "target.bin")
        target_data = os.path.join(tmpdirname, "target_data.bin")
        target_hex = os.path.join(tmpdirname, "target.bin.hex")
        target_data_hex = os.path.join(tmpdirname, "target_data.bin.hex")
        target_ast = os.path.join(tmpdirname, "target_AST.yml")

        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["in_source"])
        with open(input_stream, "w", encoding="utf-8") as file:
            file.write(golden["in_stdin"])

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.main(source, target)
            print("============================================================")
            machine.main(target, target_data, input_stream)

        # Выходные данные также считываем в переменные.
        with open(target, "rb") as file:
            code = file.read()
        with open(target_data, "rb") as file:
            data = file.read()
        with open(target_hex, encoding="utf-8") as file:
            code_hex = file.read()
        with open(target_data_hex, encoding="utf-8") as file:
            data_hex = file.read()
        with open(target_ast, encoding="utf-8") as file:
            ast = file.read()

        # Проверяем, что ожидания соответствуют реальности.

        assert yaml.safe_load(ast) == yaml.safe_load(str(golden.out["ast"]))
        assert code == golden.out["out_code"]
        assert code_hex == golden.out["out_code_hex"]
        assert data == golden.out["out_data"]
        assert data_hex == golden.out["out_data_hex"]
        assert stdout.getvalue() == golden.out["out_stdout"]
        assert caplog.text[0:MAX_LOG] + "EOF" == golden.out["out_log"]
