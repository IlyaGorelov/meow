from collections import namedtuple
from enum import StrEnum


class UnknownInstructionError(ValueError):
    def __init__(self, mnemonic):
        super().__init__(f"Unknown instruction: {mnemonic}")


class Opcode(StrEnum):
    OP = "OP"
    LUI = "LUI"
    OPIMM = "OP-IMM"
    LOAD = "LOAD"
    STORE = "STORE"
    JAL = "JAL"
    JALR = "JALR"
    BRANCH = "BRANCH"
    IN = "IN"
    OUT = "OUT"
    HALT = "HALT"
    VECTOR = "VECTOR"
    VLOAD = "VLOAD"
    VSTORE = "VSTORE"
    VSETVLI = "VSETVLI"

    def __str__(self):
        return self.value


class Term(namedtuple("Term", "line pos symbol")):
    pass


opcode_to_binary = {
    Opcode.OPIMM: 0b1,
    Opcode.LUI: 0b10,
    Opcode.OP: 0b11,
    Opcode.JAL: 0b100,
    Opcode.JALR: 0b101,
    Opcode.BRANCH: 0b110,
    Opcode.LOAD: 0b111,
    Opcode.STORE: 0b1000,
    Opcode.IN: 0b1001,
    Opcode.OUT: 0b1010,
    Opcode.HALT: 0b1011,
    Opcode.VECTOR: 0b1100,
    Opcode.VSTORE: 0b1101,
    Opcode.VLOAD: 0b1110,
    Opcode.VSETVLI: 0b1111,
}

# I-type: funct3
i_instructions = {
    "addi": 0b000,
    "slti": 0b001,
    "sltiu": 0b010,
    "xori": 0b011,
}

# R-type: funct3, funct7
r_instructions = {
    "add": (0b000, 0b0000000),
    "sub": (0b001, 0b0000000),
    "slt": (0b010, 0b0000000),
    "sltu": (0b011, 0b0000000),
    "and": (0b100, 0b0000000),
    "xor": (0b101, 0b0000000),
    "or": (0b110, 0b0000000),
    "sll": (0b111, 0b0000000),
    "srl": (0b001, 0b0000001),
    "sra": (0b010, 0b0000001),
    "mul": (0b011, 0b0000001),
    "mulh": (0b100, 0b0000001),
    "div": (0b101, 0b0000001),
    "rem": (0b110, 0b0000001),
}

vector_r_instructions = {
    "vadd": (0b000, 0b0000000),
    "vsub": (0b001, 0b0000000),
    "vmul": (0b010, 0b0000000),
    "vdiv": (0b011, 0b0000000),
    "vslt": (0b100, 0b0000000),
}

# B-type: funct3
branch_instructions = {
    "blt": 0b000,
    "bge": 0b001,
    "beq": 0b010,
    "bne": 0b011,
    "bltu": 0b100,
}

load_instructions = {"lw": 0b000, "lb": 0b001}

store_instructions = {"sw": 0b000, "sb": 0b001}


binary_to_opcode = {value: key for key, value in opcode_to_binary.items()}

registers = {
    "v0": 0,
    "v1": 1,
    "v2": 2,
    "v3": 3,
    "v4": 4,
    "v5": 5,
    "v6": 6,
    "v7": 7,
    "zero": 0,
    "ra": 1,
    "sp": 2,
    "gp": 3,
    "tp": 4,
    "t0": 5,
    "t1": 6,
    "t2": 7,
    "s0": 8,
    "s1": 9,
    "a0": 10,
    "a1": 11,
    "a2": 12,
    "a3": 13,
    "a4": 14,
    "a5": 15,
    "a6": 16,
    "a7": 17,
    "s2": 18,
    "s3": 19,
    "s4": 20,
    "s5": 21,
    "s6": 22,
    "s7": 23,
    "s8": 24,
    "s9": 25,
    "s10": 26,
    "s11": 27,
    "t3": 28,
    "t4": 29,
    "t5": 30,
    "t6": 31,
}


class Assembler:
    @staticmethod
    def get_register_number(register):
        return registers[register]

    @staticmethod
    def get_opcode(opcode):
        return opcode_to_binary[opcode]

    @staticmethod
    def encode_u(opcode, rd, imm):
        return (imm << 12) | (rd << 7) | Assembler.get_opcode(opcode)

    @staticmethod
    def encode_r(opcode, funct3, funct7, rd, rs1, rs2):
        return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | Assembler.get_opcode(opcode)

    @staticmethod
    def encode_i(opcode, funct3, rd, rs1, imm):
        return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | Assembler.get_opcode(opcode)

    @staticmethod
    def encode_s(opcode, funct3, rs1, rs2, imm):
        imm = imm & 0xFFF

        return (
            (((imm >> 5) & 0x7F) << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | ((imm & 0x1F) << 7)
            | Assembler.get_opcode(opcode)
        )

    @staticmethod
    def encode_j(opcode, rd, imm):
        imm &= 0x1FFFFF

        return ((imm >> 1) << 12) | (rd << 7) | Assembler.get_opcode(opcode)

    @staticmethod
    def encode_b(opcode, funct3, rs1, rs2, imm):
        imm &= 0x1FFF

        return (
            (((imm >> 12) & 0x1) << 31)
            | (((imm >> 5) & 0x3F) << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | (((imm >> 1) & 0xF) << 8)
            | (((imm >> 11) & 0x1) << 7)
            | Assembler.get_opcode(opcode)
        )

    @staticmethod
    def parse_instruction(line):
        line = line.strip()

        if not line:
            return None

        if line.startswith(".") or ":" in line:
            return None

        line = line.replace(",", " ").replace("(", " ").replace(")", " ")

        parts = line.split()

        if not parts:
            return None

        mnemonic = parts[0]
        args = parts[1:]

        while len(args) < 3:
            args.append("zero")

        return mnemonic, args

    @staticmethod
    def assemble_instruction(line):  # noqa: C901
        parsed = Assembler.parse_instruction(line)

        if parsed is None:
            return None

        mnemonic, args = parsed

        encoders = {
            "halt": Assembler.encode_halt,
            "lui": Assembler.encode_lui,
            "in": Assembler.encode_in,
            "out": Assembler.encode_out,
            "mv": Assembler.encode_mv,
            "jal": Assembler.encode_jal,
            "j": Assembler.encode_jump,
            "jalr": Assembler.encode_jalr,
            "vsetvli": Assembler.encode_vsetvli,
            "vload": Assembler.encode_vload,
            "vstore": Assembler.encode_vstore,
        }

        encoder = encoders.get(mnemonic)

        if encoder is not None:
            return encoder(args)

        if mnemonic in r_instructions:
            return Assembler.encode_register_instruction(mnemonic, args)

        if mnemonic in i_instructions:
            return Assembler.encode_immediate_instruction(mnemonic, args)

        if mnemonic in load_instructions:
            return Assembler.encode_load_instruction(mnemonic, args)

        if mnemonic in store_instructions:
            return Assembler.encode_store_instruction(mnemonic, args)

        if mnemonic in branch_instructions:
            return Assembler.encode_branch_instruction(mnemonic, args)

        if mnemonic in vector_r_instructions:
            return Assembler.encode_vector_instruction(mnemonic, args)

        raise UnknownInstructionError(mnemonic)

    @staticmethod
    def encode_halt(args):
        return Assembler.encode_u(Opcode.HALT, 0, 0)

    @staticmethod
    def encode_lui(args):
        rd, imm, _ = args
        return Assembler.encode_u(Opcode.LUI, Assembler.get_register_number(rd), int(imm, 0))

    @staticmethod
    def encode_in(args):
        rd, imm, _ = args
        return Assembler.encode_i(Opcode.IN, 0, Assembler.get_register_number(rd), int(imm), 0)

    @staticmethod
    def encode_out(args):
        rs2, imm, _ = args
        return Assembler.encode_s(Opcode.OUT, 0, int(imm), Assembler.get_register_number(rs2), 0)

    @staticmethod
    def encode_mv(args):
        rd, rs1, _ = args
        return Assembler.encode_i(
            Opcode.OPIMM,
            0,
            Assembler.get_register_number(rd),
            Assembler.get_register_number(rs1),
            0,
        )

    @staticmethod
    def encode_jal(args):
        rd, imm, _ = args
        return Assembler.encode_j(Opcode.JAL, Assembler.get_register_number(rd), int(imm, 0))

    @staticmethod
    def encode_jump(args):
        imm = args[0]
        return Assembler.encode_j(Opcode.JAL, 0, int(imm, 0))

    @staticmethod
    def encode_jalr(args):
        rd, imm, rs1 = args
        return Assembler.encode_i(
            Opcode.JALR,
            0,
            Assembler.get_register_number(rd),
            Assembler.get_register_number(rs1),
            int(imm, 0),
        )

    @staticmethod
    def encode_register_instruction(mnemonic, args):
        rd, rs1, rs2 = args
        funct3, funct7 = r_instructions[mnemonic]

        return Assembler.encode_r(
            Opcode.OP,
            funct3,
            funct7,
            Assembler.get_register_number(rd),
            Assembler.get_register_number(rs1),
            Assembler.get_register_number(rs2),
        )

    @staticmethod
    def encode_immediate_instruction(mnemonic, args):
        rd, rs1, imm = args

        return Assembler.encode_i(
            Opcode.OPIMM,
            i_instructions[mnemonic],
            Assembler.get_register_number(rd),
            Assembler.get_register_number(rs1),
            int(imm, 0),
        )

    @staticmethod
    def encode_load_instruction(mnemonic, args):
        rd, imm, rs1 = args

        return Assembler.encode_i(
            Opcode.LOAD,
            load_instructions[mnemonic],
            Assembler.get_register_number(rd),
            Assembler.get_register_number(rs1),
            int(imm, 0),
        )

    @staticmethod
    def encode_store_instruction(mnemonic, args):
        rs2, imm, rs1 = args

        return Assembler.encode_s(
            Opcode.STORE,
            store_instructions[mnemonic],
            Assembler.get_register_number(rs1),
            Assembler.get_register_number(rs2),
            int(imm, 0),
        )

    @staticmethod
    def encode_branch_instruction(mnemonic, args):
        rs1, rs2, imm = args

        return Assembler.encode_b(
            Opcode.BRANCH,
            branch_instructions[mnemonic],
            Assembler.get_register_number(rs1),
            Assembler.get_register_number(rs2),
            int(imm, 0),
        )

    @staticmethod
    def encode_vector_instruction(mnemonic, args):
        rd, rs1, rs2 = args
        funct3, funct7 = vector_r_instructions[mnemonic]

        return Assembler.encode_r(
            Opcode.VECTOR,
            funct3,
            funct7,
            Assembler.get_register_number(rd),
            Assembler.get_register_number(rs1),
            Assembler.get_register_number(rs2),
        )

    @staticmethod
    def encode_vsetvli(args):
        rd, imm, _ = args

        return Assembler.encode_i(Opcode.VSETVLI, 0, Assembler.get_register_number(rd), 0, int(imm, 0))

    @staticmethod
    def encode_vload(args):
        rd, imm, rs1 = args

        return Assembler.encode_i(
            Opcode.VLOAD,
            0,
            Assembler.get_register_number(rd),
            Assembler.get_register_number(rs1),
            int(imm, 0),
        )

    @staticmethod
    def encode_vstore(args):
        rs2, imm, rs1 = args

        return Assembler.encode_s(
            Opcode.VSTORE,
            0,
            Assembler.get_register_number(rs1),
            Assembler.get_register_number(rs2),
            int(imm, 0),
        )

    @staticmethod
    def assemble(code):
        machine_code = []

        for line_number, line in enumerate(code.splitlines(), 1):
            instruction = Assembler.assemble_instruction(line)

            if instruction is not None:
                machine_code.append(instruction)

        return machine_code

    @staticmethod
    def to_bytes(code):
        code = Assembler.assemble(code)

        result = bytearray()

        for instruction in code:
            result.extend(instruction.to_bytes(4, byteorder="big"))

        return bytes(result)

    @staticmethod
    def to_hex(code):
        code = Assembler.assemble(code)
        result = []

        register_names = {number: name for name,
                          number in registers.items() if not name.startswith("v")}

        def reg(number, vector=False):
            return f"v{number}" if vector else register_names[number]

        decoders = {
            Opcode.OP: Assembler.decode_r_type,
            Opcode.OPIMM: Assembler.decode_i_type,
            Opcode.LUI: Assembler.decode_lui,
            Opcode.JAL: Assembler.decode_jal,
            Opcode.JALR: Assembler.decode_jalr,
            Opcode.BRANCH: Assembler.decode_branch,
            Opcode.LOAD: Assembler.decode_load,
            Opcode.STORE: Assembler.decode_store,
            Opcode.IN: Assembler.decode_in,
            Opcode.OUT: Assembler.decode_out,
            Opcode.HALT: Assembler.decode_halt,
            Opcode.VECTOR: Assembler.decode_vector,
            Opcode.VSETVLI: Assembler.decode_vsetvli,
            Opcode.VLOAD: Assembler.decode_vload,
            Opcode.VSTORE: Assembler.decode_vstore,
        }

        for i, instruction in enumerate(code):
            opcode = instruction & 0x7F
            rd = (instruction >> 7) & 0x1F
            funct3 = (instruction >> 12) & 0x7
            rs1 = (instruction >> 15) & 0x1F
            rs2 = (instruction >> 20) & 0x1F
            funct7 = (instruction >> 25) & 0x7F

            op = binary_to_opcode[opcode]
            mnemonic = op.value

            decoder = decoders.get(op)

            if decoder is None:
                operands = ""
            else:
                mnemonic, operands = decoder(
                    instruction, rd, rs1, rs2, funct3, funct7, reg)

            hex_word = f"{instruction:08X}"
            address = i * 4
            assembly = f"{mnemonic} {operands}".strip()

            result.append(f"{address:08X} - {hex_word} - {assembly}")

        return "\n".join(result)

    @staticmethod
    def sign_extend(value, bits):
        sign = 1 << (bits - 1)
        return (value ^ sign) - sign

    @staticmethod
    def decode_r_type(instruction, rd, rs1, rs2, funct3, funct7, reg):
        mnemonic = next(name for name, (f3, f7) in r_instructions.items(
        ) if f3 == funct3 and f7 == funct7)
        return mnemonic, f"{reg(rd)}, {reg(rs1)}, {reg(rs2)}"

    @staticmethod
    def decode_i_type(instruction, rd, rs1, rs2, funct3, funct7, reg):
        mnemonic = next(
            name for name, f3 in i_instructions.items() if f3 == funct3)
        imm = Assembler.sign_extend(instruction >> 20, 12)

        return mnemonic, f"{reg(rd)}, {reg(rs1)}, {imm}"

    @staticmethod
    def decode_lui(instruction, rd, rs1, rs2, funct3, funct7, reg):
        imm = instruction >> 12
        return "LUI", f"{reg(rd)}, {imm}"

    @staticmethod
    def decode_jal(instruction, rd, rs1, rs2, funct3, funct7, reg):
        imm = ((instruction >> 12) & 0xFFFFF) << 1

        imm = Assembler.sign_extend(imm, 21)
        return "JAL", f"{reg(rd)}, {hex(imm)}"

    @staticmethod
    def decode_jalr(instruction, rd, rs1, rs2, funct3, funct7, reg):
        imm = Assembler.sign_extend(instruction >> 20, 12)
        return "JALR", f"{reg(rd)}, {imm}({reg(rs1)})"

    @staticmethod
    def decode_branch(instruction, rd, rs1, rs2, funct3, funct7, reg):
        mnemonic = next(
            name for name, f3 in branch_instructions.items() if f3 == funct3)

        imm = (
            (((instruction >> 31) & 0x1) << 12)
            | (((instruction >> 25) & 0x3F) << 5)
            | (((instruction >> 8) & 0xF) << 1)
            | (((instruction >> 7) & 0x1) << 11)
        )

        imm = Assembler.sign_extend(imm, 13)
        return mnemonic, f"{reg(rs1)}, {reg(rs2)}, {hex(imm)}"

    @staticmethod
    def decode_load(instruction, rd, rs1, rs2, funct3, funct7, reg):
        mnemonic = next(
            name for name, f3 in load_instructions.items() if f3 == funct3)

        imm = Assembler.sign_extend(instruction >> 20, 12)
        return mnemonic, f"{reg(rd)}, {imm}({reg(rs1)})"

    @staticmethod
    def decode_store(instruction, rd, rs1, rs2, funct3, funct7, reg):
        mnemonic = next(
            name for name, f3 in store_instructions.items() if f3 == funct3)

        imm = (((instruction >> 25) & 0x7F) << 5) | ((instruction >> 7) & 0x1F)
        imm = Assembler.sign_extend(imm, 12)

        return mnemonic, f"{reg(rs2)}, {imm}({reg(rs1)})"

    @staticmethod
    def decode_in(instruction, rd, rs1, rs2, funct3, funct7, reg):
        return "IN", f"{reg(rd)}, {rs1}"

    @staticmethod
    def decode_out(instruction, rd, rs1, rs2, funct3, funct7, reg):
        return "OUT", f"{reg(rs2)}, {rs1}"

    @staticmethod
    def decode_halt(instruction, rd, rs1, rs2, funct3, funct7, reg):
        return "HALT", ""

    @staticmethod
    def decode_vector(instruction, rd, rs1, rs2, funct3, funct7, reg):
        mnemonic = next(name for name, (f3, f7) in vector_r_instructions.items(
        ) if f3 == funct3 and f7 == funct7)

        operands = f"{reg(rd, True)}, {reg(rs1, True)}, {reg(rs2, True)}"
        return mnemonic, operands

    @staticmethod
    def decode_vsetvli(instruction, rd, rs1, rs2, funct3, funct7, reg):
        imm = Assembler.sign_extend(instruction >> 20, 12)
        return "VSETVLI", f"{reg(rd)}, {hex(imm)}"

    @staticmethod
    def decode_vload(instruction, rd, rs1, rs2, funct3, funct7, reg):
        imm = Assembler.sign_extend(instruction >> 20, 12)
        return "VLOAD", f"{reg(rd, True)}, {imm}({reg(rs1)})"

    @staticmethod
    def decode_vstore(instruction, rd, rs1, rs2, funct3, funct7, reg):
        imm = (((instruction >> 25) & 0x7F) << 5) | ((instruction >> 7) & 0x1F)
        imm = Assembler.sign_extend(imm, 12)

        return "VSTORE", f"{reg(rs2, True)}, {imm}({reg(rs1)})"
