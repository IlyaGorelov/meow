from enum import IntEnum, IntFlag

class ALU_OP(IntEnum):
    NONE = 0
    ADD = 1
    SUB = 2
    MUL = 3
    MULH = 4
    DIV = 5
    REM = 6
    AND = 7
    OR = 8
    XOR = 9
    SLL = 10
    SRL = 11
    SRA = 12
    SLT = 13
    SLTU = 14

class ALU_LEFT(IntEnum):
    NONE = 0
    ZERO = 1
    REG1 = 2
    PC = 3

class ALU_RIGHT(IntEnum):
    NONE = 0
    REG2 = 1
    IMM = 2

class REG_WRITE(IntEnum):
    NONE = 0
    ALU = 1
    MEM_W = 2
    MEM_B = 3
    NEXT_PC = 4
    IN = 5

class MEM(IntEnum):
    NONE = 0
    LATCH_AR = 1
    WRITE_W = 2
    WRITE_B = 3

class PC(IntEnum):
    NONE = 0
    NEXT_PC = 1
    ALU = 2

class CTRL(IntFlag):
    NONE = 0
    REG1_SEL = 1 << 0
    REG2_SEL = 1 << 1
    DISPATCH = 1 << 2
    INPUT_READ = 1 << 3
    OUTPUT = 1 << 4
    HALT = 1 << 5

class COND(IntEnum):
    NONE = 0
    ZERO = 1
    NOT_ZERO = 2

def encode(
        next_addr, # 8 bit
        alu_op, # 4 bit
        alu_cond, # 2 bit
        alu_left, # 3 bit
        alu_right, # 3 bit
        reg_write, # 3 bit
        mem, # 3 bit
        pc, # 3 bit
        ctrl, # 9 bits
        ):
        return (
            (next_addr << 34) |
            (alu_op << 30) |
            (alu_cond << 28) |
            (alu_left << 25) |
            (alu_right << 22) |
            (reg_write << 19) |
            (mem << 16) |
            (pc << 13) |
            (ctrl << 4))

def decode(microinstruction):
        return {
            "next":      (microinstruction >> 34) & 0xFF,
            "alu_op":    (microinstruction >> 30) & 0xF,
            "cond":    (microinstruction >> 28) & 0x3,
            "alu_left":  (microinstruction >> 25) & 0x7,
            "alu_right": (microinstruction >> 22) & 0x7,
            "reg_write": (microinstruction >> 19) & 0x7,
            "mem":       (microinstruction >> 16) & 0x7,
            "pc":        (microinstruction >> 13) & 0x7,
            "ctrl":      (microinstruction >> 4) & 0x1FF,
        }


def setup_micro_memory():
    microcode = []
    descriptions = []
    addresses = {}

    def add_microinstruction(
        description,
        next_addr=0,
        alu_op=ALU_OP.NONE,
        alu_cond=COND.NONE,
        alu_left=ALU_LEFT.NONE,
        alu_right=ALU_RIGHT.NONE,
        reg_write=REG_WRITE.NONE,
        mem=MEM.NONE,
        pc=PC.NONE,
        ctrl=CTRL.NONE
    ):
        index = len(microcode)

        microcode.append(encode(
            next_addr,
            alu_op,
            alu_cond,
            alu_left,
            alu_right,
            reg_write,
            mem,
            pc,
            ctrl
        ))

        descriptions.append(description)

        return index

    addresses["FETCH"] = add_microinstruction(
        "FETCH",
        pc=PC.NEXT_PC,
        ctrl=CTRL.DISPATCH
    )

    addresses["ADDI"] = add_microinstruction(
        "ADDI, goto FETCH",
        alu_op=ALU_OP.ADD,
        alu_left=ALU_LEFT.REG1,
        alu_right=ALU_RIGHT.IMM,
        reg_write=REG_WRITE.ALU,
        ctrl=CTRL.REG1_SEL
    )

    addresses["SLTI"] = add_microinstruction(
        "SLTI, goto FETCH",
        alu_op=ALU_OP.SLT,
        alu_left=ALU_LEFT.REG1,
        alu_right=ALU_RIGHT.IMM,
        reg_write=REG_WRITE.ALU,
        ctrl=CTRL.REG1_SEL
    )

    addresses["LUI"] = add_microinstruction(
        "LUI, goto FETCH",
        alu_left=ALU_LEFT.ZERO,
        alu_right=ALU_RIGHT.IMM,
        alu_op=ALU_OP.ADD,
        reg_write=REG_WRITE.ALU
    )

    addresses["XORI"] = add_microinstruction(
        "XORI, goto FETCH",
        alu_op=ALU_OP.XOR,
        alu_left=ALU_LEFT.REG1,
        alu_right=ALU_RIGHT.IMM,
        reg_write=REG_WRITE.ALU,
        ctrl=CTRL.REG1_SEL
    )

    addresses["SLTIU"] = add_microinstruction(
        "SLTIU, goto FETCH",
        alu_op=ALU_OP.SLTU,
        alu_left=ALU_LEFT.REG1,
        alu_right=ALU_RIGHT.IMM,
        reg_write=REG_WRITE.ALU,
        ctrl=CTRL.REG1_SEL
    )

    reg_instructions = [
        ("ADD", ALU_OP.ADD),
        ("SUB", ALU_OP.SUB),
        ("SLT", ALU_OP.SLT),
        ("SLTU", ALU_OP.SLTU),
        ("AND", ALU_OP.AND),
        ("OR", ALU_OP.OR),
        ("XOR", ALU_OP.XOR),
        ("SLL", ALU_OP.SLL),
        ("SRL", ALU_OP.SRL),
        ("SRA", ALU_OP.SRA),
    ]

    for name, operation in reg_instructions:
        addresses[name] = add_microinstruction(
            f"{name}, goto FETCH",
            alu_op=operation,
            alu_left=ALU_LEFT.REG1,
            alu_right=ALU_RIGHT.REG2,
            reg_write=REG_WRITE.ALU,
            ctrl=CTRL.REG1_SEL | CTRL.REG2_SEL
        )

    addresses["JAL"] = add_microinstruction(
        "JAL, goto FETCH",
        alu_op=ALU_OP.ADD,
        alu_left=ALU_LEFT.PC,
        alu_right=ALU_RIGHT.IMM,
        reg_write=REG_WRITE.NEXT_PC,
        pc=PC.ALU
    )

    addresses["JALR"] = add_microinstruction(
        "JALR, goto FETCH",
        alu_op=ALU_OP.ADD,
        alu_left=ALU_LEFT.REG1,
        alu_right=ALU_RIGHT.IMM,
        reg_write=REG_WRITE.NEXT_PC,
        pc=PC.ALU,
        ctrl=CTRL.REG1_SEL
    )

    addresses["HALT"] = add_microinstruction(
        "HALT",
        pc=PC.ALU,
        ctrl=CTRL.HALT
    )

    def add_branch(name, operation, condition):
        branch_addr = add_microinstruction(
            f"{name}: compare registers",
            alu_cond=condition,
            alu_op=operation,
            alu_left=ALU_LEFT.REG1,
            alu_right=ALU_RIGHT.REG2,
            ctrl=CTRL.REG1_SEL | CTRL.REG2_SEL
        )

        add_microinstruction(
            f"{name}: branch not taken, goto FETCH"
        )

        taken_addr = add_microinstruction(
            f"{name}: PC += immediate, goto FETCH",
            alu_op=ALU_OP.ADD,
            alu_left=ALU_LEFT.PC,
            alu_right=ALU_RIGHT.IMM,
            pc=PC.ALU
        )

        microcode[branch_addr] = encode(
            taken_addr,
            operation,
            condition,
            ALU_LEFT.REG1,
            ALU_RIGHT.REG2,
            REG_WRITE.NONE,
            MEM.NONE,
            PC.NONE,
            CTRL.REG1_SEL | CTRL.REG2_SEL
        )

        addresses[name] = branch_addr
        return branch_addr

    add_branch("BLT", ALU_OP.SLT, COND.NOT_ZERO)
    add_branch("BLTU", ALU_OP.SLTU, COND.NOT_ZERO)
    add_branch("BGE", ALU_OP.SLT, COND.ZERO)
    add_branch("BEQ", ALU_OP.SUB, COND.ZERO)
    add_branch("BNE", ALU_OP.SUB, COND.NOT_ZERO)

    def add_memory_instruction(name, mem_operation, write_operation):
        address = add_microinstruction(
            f"{name}: AR = rs1 + imm, goto MEMORY OPERATION",
            next_addr=len(microcode) + 1,
            alu_op=ALU_OP.ADD,
            alu_left=ALU_LEFT.REG1,
            alu_right=ALU_RIGHT.IMM,
            mem=MEM.LATCH_AR,
            ctrl=CTRL.REG1_SEL
        )

        add_microinstruction(
            f"{name}: MEMORY OPERATION",
            alu_left=ALU_LEFT.ZERO,
            alu_right=ALU_RIGHT.REG2,
            reg_write=write_operation,
            mem=mem_operation,
            ctrl=CTRL.REG2_SEL if mem_operation != MEM.NONE else CTRL.REG2_SEL
        )

        addresses[name] = address

    add_memory_instruction("SW", MEM.WRITE_W, REG_WRITE.NONE)
    add_memory_instruction("SB", MEM.WRITE_B, REG_WRITE.NONE)
    add_memory_instruction("LW", MEM.NONE, REG_WRITE.MEM_W)
    add_memory_instruction("LB", MEM.NONE, REG_WRITE.MEM_B)

    addresses["IN"] = add_microinstruction(
        "IN",
        reg_write=REG_WRITE.IN
    )

    addresses["OUT"] = add_microinstruction(
        "OUT",
        ctrl=CTRL.OUTPUT | CTRL.REG1_SEL
    )

    return (microcode, descriptions, addresses)