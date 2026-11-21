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
            machine.main(target, target_data, input_stream, golden["in_stdout_repr"])

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
            ast = yaml.safe_load(file.read())

        # Проверяем, что ожидания соответствуют реальности.

        assert ast == golden.out["ast"]
        assert code == golden.out["out_code"]
        assert code_hex == golden.out["out_code_hex"]
        assert data == golden.out["out_data"]
        assert data_hex == golden.out["out_data_hex"]
        assert stdout.getvalue() == golden.out["out_stdout"]

        assert truncate_log(caplog.text) + "EOF" == golden.out["out_log"]


def truncate_log(log: str, first: int = 4000, last: int = 500) -> str:
    if len(log) <= first + last:
        return log

    # End the first part at a newline before the limit
    first_end = log.rfind("\n", 0, first)
    if first_end == -1:
        first_end = first

    # Start the last part at a newline before the last section
    tail_limit = len(log) - last
    last_start = log.rfind("\n", 0, tail_limit)
    if last_start == -1:
        last_start = tail_limit
    else:
        last_start += 1  # skip the newline itself

    return log[: first_end + 1] + "\n... [LOG TRUNCATED] ...\n\n" + log[last_start:]
