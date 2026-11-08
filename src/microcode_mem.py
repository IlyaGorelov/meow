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
    ALU_RES = 1
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
            "alu_cond":    (microinstruction >> 28) & 0x4,
            "alu_left":  (microinstruction >> 25) & 0x7,
            "alu_right": (microinstruction >> 22) & 0x7,
            "reg_write": (microinstruction >> 19) & 0x7,
            "mem":       (microinstruction >> 16) & 0x7,
            "pc":        (microinstruction >> 13) & 0x7,
            "ctrl":      (microinstruction >> 4) & 0x1FF,
        }

def setup_micro_memory():
    microcode = []

    #fetch
    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.NONE,
                            ALU_RIGHT.NONE,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NEXT_PC,
                            CTRL.DISPATCH))
    # -------------------------
    # Immmediate instr.

    #addi
    microcode.append(encode(0,
                            ALU_OP.ADD,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.IMM,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL))

    #slti
    microcode.append(encode(0,
                            ALU_OP.SLT,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.IMM,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL))

    #lui
    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.ZERO,
                            ALU_RIGHT.IMM,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    #xori
    microcode.append(encode(0,
                            ALU_OP.XOR,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.IMM,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    #sltiu
    microcode.append(encode(0,
                            ALU_OP.SLTU,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.IMM,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    #add
    microcode.append(encode(0,
                            ALU_OP.SLTU,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.IMM,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))
    #------------
    # Reg to reg instr

    # add rd, rs1, rs2
    microcode.append(encode(0,
                            ALU_OP.ADD,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL | CTRL.REG2_SEL))

    # sub rd, rs1, rs2
    microcode.append(encode(0,
                            ALU_OP.SUB,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL | CTRL.REG2_SEL))

    # slt rd, rs1, rs2
    microcode.append(encode(0,
                            ALU_OP.SLT,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL | CTRL.REG2_SEL))

    # sltu rd, rs1, rs2
    microcode.append(encode(0,
                            ALU_OP.SLTU,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL | CTRL.REG2_SEL))

    # and rd, rs1, rs2
    microcode.append(encode(0,
                            ALU_OP.AND,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL | CTRL.REG2_SEL))

    # or rd, rs1, rs2
    microcode.append(encode(0,
                            ALU_OP.OR,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL | CTRL.REG2_SEL))

    # xor rd, rs1, rs2
    microcode.append(encode(0,
                            ALU_OP.XOR,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL | CTRL.REG2_SEL))

    # sll rd, rs1, rs2
    microcode.append(encode(0,
                            ALU_OP.SLL,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL | CTRL.REG2_SEL))

    # srl rd, rs1, rs2
    microcode.append(encode(0,
                            ALU_OP.SRL,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL | CTRL.REG2_SEL))

    # sra rd, rs1, rs2
    microcode.append(encode(0,
                            ALU_OP.SRA,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.ALU_RES,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG1_SEL | CTRL.REG2_SEL))

    # unconditional flow controls
    # jal
    microcode.append(encode(0,
                            ALU_OP.ADD,
                            COND.NONE,
                            ALU_LEFT.PC,
                            ALU_RIGHT.IMM,
                            REG_WRITE.NEXT_PC,
                            MEM.NONE,
                            PC.ALU,
                            CTRL.NONE))

    # jalr
    microcode.append(encode(0,
                            ALU_OP.ADD,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.IMM,
                            REG_WRITE.NEXT_PC,
                            MEM.NONE,
                            PC.ALU,
                            CTRL.REG1_SEL))

    # halt
    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.NONE,
                            ALU_RIGHT.NONE,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.ALU,
                            CTRL.HALT))

    # branches

    # blt
    microcode.append(encode(22,
                            ALU_OP.SLT,
                            COND.NOT_ZERO,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    # jump to microinstr[0]
    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.NONE,
                            ALU_RIGHT.NONE,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    # microcode[22]
    microcode.append(encode(0,
                            ALU_OP.ADD,
                            COND.NONE,
                            ALU_LEFT.PC,
                            ALU_RIGHT.IMM,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.ALU,
                            CTRL.NONE))

    microcode.append(encode(22,
                            ALU_OP.SLTU,
                            COND.ZERO,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.NONE,
                            ALU_RIGHT.NONE,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    # bge
    microcode.append(encode(22,
                            ALU_OP.SLT,
                            COND.ZERO,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.NONE,
                            ALU_RIGHT.NONE,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    # beq
    microcode.append(encode(22,
                            ALU_OP.SUB,
                            COND.ZERO,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.NONE,
                            ALU_RIGHT.NONE,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    # bne
    microcode.append(encode(22,
                            ALU_OP.SUB,
                            COND.NOT_ZERO,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.REG2,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.NONE,
                            ALU_RIGHT.NONE,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))


    # load and store

    # sw
    microcode.append(encode(30,
                            ALU_OP.ADD,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.IMM,
                            REG_WRITE.NONE,
                            MEM.LATCH_AR,
                            PC.NONE,
                            CTRL.REG1_SEL))

    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.ZERO,
                            ALU_RIGHT.REG2,
                            REG_WRITE.NONE,
                            MEM.WRITE_W,
                            PC.NONE,
                            CTRL.REG2_SEL))

    # sb
    microcode.append(encode(32,
                            ALU_OP.ADD,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.IMM,
                            REG_WRITE.NONE,
                            MEM.LATCH_AR,
                            PC.NONE,
                            CTRL.REG1_SEL))

    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.ZERO,
                            ALU_RIGHT.REG2,
                            REG_WRITE.NONE,
                            MEM.WRITE_B,
                            PC.NONE,
                            CTRL.REG2_SEL))

    # lw
    microcode.append(encode(34,
                            ALU_OP.ADD,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.IMM,
                            REG_WRITE.NONE,
                            MEM.LATCH_AR,
                            PC.NONE,
                            CTRL.REG1_SEL))

    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.ZERO,
                            ALU_RIGHT.REG2,
                            REG_WRITE.MEM_W,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG2_SEL))

    # lb
    microcode.append(encode(34,
                            ALU_OP.ADD,
                            COND.NONE,
                            ALU_LEFT.REG1,
                            ALU_RIGHT.IMM,
                            REG_WRITE.NONE,
                            MEM.LATCH_AR,
                            PC.NONE,
                            CTRL.REG1_SEL))

    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.NONE,
                            ALU_RIGHT.NONE,
                            REG_WRITE.MEM_B,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.REG2_SEL))

    # IO
    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.NONE,
                            ALU_RIGHT.NONE,
                            REG_WRITE.IN,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.NONE))

    microcode.append(encode(0,
                            ALU_OP.NONE,
                            COND.NONE,
                            ALU_LEFT.NONE,
                            ALU_RIGHT.NONE,
                            REG_WRITE.NONE,
                            MEM.NONE,
                            PC.NONE,
                            CTRL.OUTPUT | CTRL.REG1_SEL))

    return microcode