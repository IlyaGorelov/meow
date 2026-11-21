import argparse
import logging

from control_unit import ControlUnit
from data_path import DataPath


def simulation(code, data, input_tokens, data_memory_size, limit, output_type="dec"):
    data_path = DataPath(code, data_memory_size, data, input_tokens, output_type)
    control_unit = ControlUnit(data_path)

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
    logging.info("output_buffer: %s", repr(", ".join(data_path.io_mapping[1])))
    return "".join(data_path.io_mapping[1]), control_unit.current_tick()


def main(code_file, data_file, input_file, output_type="dec"):
    with open(code_file, "rb") as file:
        code = file.read()

    with open(data_file, "rb") as file:
        data = file.read()

    input_token = []

    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()

        for token in input_text.split(","):
            token = token.strip()

            if not token:
                continue

            if token.startswith('"') and token.endswith('"'):
                input_token.extend(ord(c) for c in token[1:-1])

            elif token.startswith("'") and token.endswith("'"):
                input_token.append(ord(token[1:-1]))

            else:
                input_token.append(int(token, 0))

    output, ticks = simulation(
        code, data, input_tokens=input_token, data_memory_size=4000, limit=10000000000, output_type=output_type
    )

    print("".join(output))
    print("ticks:", ticks)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)-8s %(module)s:%(funcName)-15s %(message)s",
    )
    parser = argparse.ArgumentParser(description="My program")

    parser.add_argument("code_file", help="Machine code file")
    parser.add_argument("data_file", help="Data memory file")
    parser.add_argument("input_file", help="Input file")

    parser.add_argument(
        "-o", "--output", type=str, default="dec", choices=["dec", "char"], help="Output format (dec or char)"
    )

    args = parser.parse_args()

    main(args.code_file, args.data_file, args.input_file, args.output)
