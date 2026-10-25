from collections import namedtuple
from enum import Enum


class Opcode(str, Enum):
    OP = "OP"
    LUI = "LUI"
    OPIMM = "OP-IMM"
    LOAD = "LOAD"
    STORE = "STORE"
    JAL = "JAL"
    BRANCH = "BRANCH"
    IN = "IN"
    OUT="OUT"
    HALT = "HALT"

    def __str__(self):
        """Переопределение стандартного поведения `__str__` для `Enum`: вместо
        `Opcode.INC` вернуть `increment`.
        """
        return str(self.value)


class Term(namedtuple("Term", "line pos symbol")):
    """Описание выражения из исходного текста программы.

    Сделано через класс, чтобы был docstring.
    """

opcode_to_binary = {
    Opcode.OP:     0x00,  # 00000000
    Opcode.LUI:    0x01,  # 00000001
    Opcode.OPIMM: 0x02,  # 00000010
    Opcode.LOAD:   0x03,  # 00000011
    Opcode.STORE:  0x04,  # 00000100
    Opcode.JAL:    0x05,  # 00000101
    Opcode.BRANCH: 0x06,  # 00000110
    Opcode.IN:     0x07,  # 00000111
    Opcode.OUT:    0x08,  # 00001000
    Opcode.HALT:   0x09,  # 00001001
}

binary_to_opcode = {
    0x00: Opcode.OP,      # 00000000
    0x01: Opcode.LUI,     # 00000001
    0x02: Opcode.OPIMM,  # 00000010
    0x03: Opcode.LOAD,    # 00000011
    0x04: Opcode.STORE,   # 00000100
    0x05: Opcode.JAL,     # 00000101
    0x06: Opcode.BRANCH,  # 00000110
    0x07: Opcode.IN,      # 00000111
    0x08: Opcode.OUT,     # 00001000
    0x09: Opcode.HALT,    # 00001001
}



def to_bytes(code):
    """Преобразует машинный код в бинарное представление.

    Бинарное представление инструкций:

    ┌─────────┬─────────────────────────────────────────────────────────────┐
    │ 31...28 │ 27                                                        0 │
    ├─────────┼─────────────────────────────────────────────────────────────┤
    │  опкод  │                      адрес перехода                         │
    └─────────┴─────────────────────────────────────────────────────────────┘
    """
    binary_bytes = bytearray()
    for instr in code:
        # Получаем бинарный код операции
        opcode_bin = opcode_to_binary[instr["opcode"]] << 28

        # Добавляем адрес перехода, если он есть
        arg = instr.get("arg", 0)

        # Формируем 32-битное слово: опкод (4 бита) + адрес (28 бит)
        binary_instr = opcode_bin | (arg & 0x0FFFFFFF)

        # Преобразуем 32-битное целое число в 4 байта (big-endian)
        binary_bytes.extend(
            ((binary_instr >> 24) & 0xFF, (binary_instr >> 16) & 0xFF, (binary_instr >> 8) & 0xFF, binary_instr & 0xFF)
        )

    return bytes(binary_bytes)


def to_hex(code):
    """Преобразует машинный код в текстовый файл с шестнадцатеричным представлением.

    Формат вывода:
    <address> - <HEXCODE> - <mnemonic>
    Например:
    20 - 03340301 - add #01 <- 34 + #03
    """
    binary_code = to_bytes(code)
    result = []

    for i in range(0, len(binary_code), 4):
        if i + 3 >= len(binary_code):
            break

        # Формируем 32-битное слово из 4 байтов
        word = (binary_code[i] << 24) | (binary_code[i + 1] << 16) | (binary_code[i + 2] << 8) | binary_code[i + 3]

        # Получаем опкод и адрес
        opcode_bin = (word >> 28) & 0xF
        arg = word & 0x0FFFFFFF

        # Преобразуем опкод и адрес в мнемонику
        mnemonic = binary_to_opcode[opcode_bin].value
        if opcode_bin in (0x6, 0x7):  # jmp или jz требуют аргумент
            mnemonic = f"{mnemonic} {arg}"

        # Формируем строку в требуемом формате
        hex_word = f"{word:08X}"
        address = i // 4
        line = f"{address} - {hex_word} - {mnemonic}"
        result.append(line)

    return "\n".join(result)


def from_bytes(binary_code):
    """Преобразует бинарное представление машинного кода в структурированный формат.

    Бинарное представление инструкций:

    ┌─────────┬─────────────────────────────────────────────────────────────┐
    │ 31...28 │ 27                                                        0 │
    ├─────────┼─────────────────────────────────────────────────────────────┤
    │  опкод  │                      адрес перехода                         │
    └─────────┴─────────────────────────────────────────────────────────────┘
    """
    structured_code = []
    # Обрабатываем байты по 4 за раз для получения 32-битных инструкций
    for i in range(0, len(binary_code), 4):
        if i + 3 >= len(binary_code):
            break

        # Формируем 32-битное слово из 4 байтов
        binary_instr = (
            (binary_code[i] << 24) | (binary_code[i + 1] << 16) | (binary_code[i + 2] << 8) | binary_code[i + 3]
        )

        # Извлекаем опкод (старшие 4 бита)
        opcode_bin = (binary_instr >> 28) & 0xF
        opcode = binary_to_opcode[opcode_bin]

        # Извлекаем адрес перехода (младшие 28 бит)
        arg = binary_instr & 0x0FFFFFFF

        # Формируем структуру инструкции
        instr = {"index": i // 4, "opcode": opcode}

        # Добавляем адрес перехода только для инструкций перехода
        if opcode in (Opcode.JMP, Opcode.JZ):
            instr["arg"] = arg

        structured_code.append(instr)

    return structured_code