import logging
import sys

from data_path import DataPath
from control_unit import ControlUnit
from isa import Assembler, Opcode
from microcode_mem import *

microcode = setup_micro_memory()

def simulation(code, data, input_tokens, data_memory_size, limit):
    data_path = DataPath(data_memory_size, data, input_tokens)
    control_unit = ControlUnit(code, data_path, microcode)

    logging.debug("%s", control_unit)
    try:
        while control_unit._tick < limit:
            control_unit.process_next_tick()
            logging.debug("%s", control_unit)
    except EOFError:
        logging.warning("Input buffer is empty!")
    except StopIteration:
        pass

    if control_unit._tick >= limit:
        logging.warning("Limit exceeded!")
    logging.info("output_buffer: %s", repr("".join(data_path.output_buffer)))
    return "".join(data_path.output_buffer), control_unit.current_tick()


def main(code_file, data_file, input_file):
    with open(code_file, "rb") as file:
        binary_code = file.read()
    code = Assembler.from_bytes(binary_code)

    with open(data_file, "rb") as file:
        binary_code = file.read()
    data = binary_code

    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        input_token = []
        for char in input_text:
            input_token.append(char)

    output, ticks = simulation(
        code,
        data,
        input_tokens=input_token,
        data_memory_size=100,
        limit=2000,
    )

    print("".join(output))
    print("ticks:", ticks)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 4, "Wrong arguments: machine.py <code_file> <data_file> <input_file>"
    _, code_file, data_file, input_file = sys.argv
    main(code_file, data_file, input_file)