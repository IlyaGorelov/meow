from collections import namedtuple
from enum import Enum


class Opcode(str, Enum):
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
    VSTORE="VSTORE"
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
    "addi":  0b000,
    "mv": 0b000,
    "slti":  0b001,
    "sltiu": 0b010,
    "xori":  0b011,
}

# R-type: funct3, funct7
r_instructions = {
    "add":  (0b000, 0b0000000),
    "sub":  (0b001, 0b0000000),

    "slt":  (0b010, 0b0000000),
    "sltu": (0b011, 0b0000000),

    "and":  (0b100, 0b0000000),
    "xor":  (0b101, 0b0000000),
    "or":   (0b110, 0b0000000),

    "sll":  (0b111, 0b0000000),
    "srl":  (0b001, 0b0000001),
    "sra":  (0b010, 0b0000001),

    "mul":  (0b011, 0b0000001),
    "mulh": (0b100, 0b0000001),
    "div":  (0b101, 0b0000001),
    "rem":  (0b110, 0b0000001),
}

# B-type: funct3
branch_instructions = {
        "blt": 0b000,
        "bge": 0b001,
        "beq": 0b010,
        "bne": 0b011,
        "bltu": 0b100,
    }

load_instructions = {
        "lw": 0b000,
        "lb": 0b001,
        "vload": 0
    }

store_instructions = {
        "sw": 0b000,
        "sb": 0b001,
        "vstore": 0
    }

vector_instructions = {
    "add":  (0b000, 0b0000000),
    "sub":  (0b001, 0b0000000),
    "mul":  (0b010, 0b0000000),
    "div":  (0b011, 0b0000000),
    "slt":  (0b100, 0b0000000),
}

binary_to_opcode = {
    value: key for key, value in opcode_to_binary.items()
}

registers = {
    "zero": 0,
    "ra": 1,
    "sp": 2,
    "gp": 3,
    "tp": 4,

    "t0": 5,
    "t1": 6,
    "t2": 7,

    "s0": 8,
    "fp": 8,
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

    # U-type
    # imm[31:12] | rd | opcode
    @staticmethod
    def encode_u(opcode, rd, imm):
        instruction = (
            (imm << 12)
            | (rd << 7)
            | Assembler.get_opcode(opcode)
        )

        return instruction

    # R-type
    # funct7 | rs2 | rs1 | funct3 | rd | opcode
    @staticmethod
    def encode_r(opcode, funct3, funct7, rd, rs1, rs2):
        instruction = (
            (funct7 << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | (rd << 7)
            | Assembler.get_opcode(opcode)
        )

        return instruction

    # I-type
    # imm[11:0] | rs1 | funct3 | rd | opcode
    @staticmethod
    def encode_i(opcode, funct3, rd, rs1, imm):
        instruction = (
            ((imm & 0xFFF) << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | (rd << 7)
            | Assembler.get_opcode(opcode)
        )

        return instruction

    # S-type
    # imm[11:5] | rs2 | rs1 | funct3 | imm[4:0] | opcode
    @staticmethod
    def encode_s(opcode, funct3, rs1, rs2, imm):
        imm = imm & 0xFFF

        instruction = (
            (((imm >> 5) & 0x7F) << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | ((imm & 0x1F) << 7)
            | Assembler.get_opcode(opcode)
        )

        return instruction

    # J-type
    # imm[20] | imm[10:1] | imm[11] | imm[19:12] | rd | opcode
    @staticmethod
    def encode_j(opcode, rd, imm):
        imm &= 0x1FFFFF

        instruction = (
            (((imm >> 20) & 0x1) << 31)
            | (((imm >> 1) & 0x3FF) << 21)
            | (((imm >> 11) & 0x1) << 20)
            | (((imm >> 12) & 0xFF) << 12)
            | (rd << 7)
            | Assembler.get_opcode(opcode)
        )

        return instruction

    # B-type
    # imm[12] | imm[10:5] | rs2 | rs1 | funct3 | imm[4:1] | imm[11] | opcode
    @staticmethod
    def encode_b(opcode, funct3, rs1, rs2, imm):
        imm &= 0x1FFF

        instruction = (
            (((imm >> 12) & 0x1) << 31)
            | (((imm >> 5) & 0x3F) << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (funct3 << 12)
            | (((imm >> 1) & 0xF) << 8)
            | (((imm >> 11) & 0x1) << 7)
            | Assembler.get_opcode(opcode)
        )

        return instruction

    @staticmethod
    def parse_instruction(line):
        line = line.strip()

        if not line:
            return None

        if line.startswith(".") or ":" in line:
            return None

        line = (
            line.replace(",", " ")
                .replace("(", " ")
                .replace(")", " ")
        )

        parts = line.split()

        if not parts:
            return None

        mnemonic = parts[0]
        args = parts[1:]

        while len(args)<3:
            args.append("zero")

        return mnemonic, args

    @staticmethod
    def assemble_instruction(line):
        parsed = Assembler.parse_instruction(line)

        if parsed is None:
            return None

        mnemonic, args = parsed

        if mnemonic == "halt":
            return Assembler.encode_u(
                Opcode.HALT, 0, 0
            )

        if mnemonic == "lui":
            rd, imm, _ = args

            return Assembler.encode_u(
                Opcode.LUI,
                Assembler.get_register_number(rd),
                int(imm,0)
            )

        if mnemonic in r_instructions:
            rd, rs1, rs2 = args

            funct3, funct7 = r_instructions[mnemonic]

            return Assembler.encode_r(
                Opcode.OP,
                funct3,
                funct7,
                Assembler.get_register_number(rd),
                Assembler.get_register_number(rs1),
                Assembler.get_register_number(rs2)
            )

        if mnemonic in ("in", "out"):
            rd, rs1, rs2 = args

            opcode = Opcode.IN if mnemonic == "in" else Opcode.OUT

            if opcode == Opcode.IN:
                return Assembler.encode_r(
                    opcode,
                    0,
                    0,
                    Assembler.get_register_number(rd),
                    Assembler.get_register_number(rs1),
                    Assembler.get_register_number(rs2)
                )
            else:
                return Assembler.encode_r(
                    opcode,
                    0,
                    0,
                    Assembler.get_register_number(rs1),
                    Assembler.get_register_number(rd),
                    Assembler.get_register_number(rs2)
                )

        if mnemonic in i_instructions:
            rd, rs1, imm = args

            return Assembler.encode_i(
                Opcode.OPIMM,
                i_instructions[mnemonic],
                Assembler.get_register_number(rd),
                Assembler.get_register_number(rs1),
                int(imm,0)
            )

        if mnemonic == "mv":
            rd, rs1, _ = args

            return Assembler.encode_i(
                Opcode.OPIMM,
                0,
                Assembler.get_register_number(rd),
                Assembler.get_register_number(rs1),
                0
            )

        if mnemonic in load_instructions:
            rd, imm, rs1 = args

            return Assembler.encode_i(
                Opcode.LOAD,
                load_instructions[mnemonic],
                Assembler.get_register_number(rd),
                Assembler.get_register_number(rs1),
                int(imm,0)
            )

        if mnemonic in store_instructions:
            rs2, imm, rs1 = args

            return Assembler.encode_s(
                Opcode.STORE,
                store_instructions[mnemonic],
                Assembler.get_register_number(rs1),
                Assembler.get_register_number(rs2),
                int(imm,0)
            )

        if mnemonic in branch_instructions:
            rs1, rs2, imm = args

            return Assembler.encode_b(
                Opcode.BRANCH,
                branch_instructions[mnemonic],
                Assembler.get_register_number(rs1),
                Assembler.get_register_number(rs2),
                int(imm,0)
            )

        if mnemonic == "jal":
            rd, imm, _ = args

            return Assembler.encode_j(
                Opcode.JAL,
                Assembler.get_register_number(rd),
                int(imm,0)
            )

        if mnemonic == "j":
            imm = args[0]

            return Assembler.encode_j(
                Opcode.JAL,
                0,
                int(imm,0)
            )

        if mnemonic == "jalr":
            rd, imm, rs1 = args

            return Assembler.encode_i(
                Opcode.JALR,
                0,
                Assembler.get_register_number(rd),
                Assembler.get_register_number(rs1),
                int(imm,0)
            )
            
        if mnemonic in vector_instructions:
            rd, rs1, rs2 = args
            
            funct3, funct7 = r_instructions[mnemonic]

            return Assembler.encode_r(
                Opcode.VECTOR,
                funct3,
                funct7,
                Assembler.get_register_number(rd),
                Assembler.get_register_number(rs1),
                Assembler.get_register_number(rs2),
            )
            
        if mnemonic == "vsetvli":
            rd, imm , _ = args
            
            return Assembler.encode_u(
                Opcode.VSETVLI,
                Assembler.get_register_number(rd),
                int(imm,0)
            )

        raise ValueError(f"Unknown instruction: {mnemonic}")

    @staticmethod
    def assemble(code):
        machine_code = []

        for line_number, line in enumerate(code.splitlines(), 1):
            instruction = Assembler.assemble_instruction(line)
            print(instruction)

            if instruction is not None:
                machine_code.append(instruction)

        return machine_code

    @staticmethod
    def to_bytes(code):
        code = Assembler.assemble(code)

        result = bytearray()

        for instruction in code:
            result.extend(
                instruction.to_bytes(4, byteorder="big")
            )

        return bytes(result)

    @staticmethod
    def to_hex(code):
        code = Assembler.assemble(code)
        result = []

        for i, instruction in enumerate(code):
            result.append(
                f"{i * 4:08X}: {instruction:08X}"
            )

        return "\n".join(result)

    
