from enum import IntEnum, IntFlag

from enum import IntEnum


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


class REG_WRITE_MUX(IntEnum):
    NONE = 0
    ALU = 1
    MEM_W = 2
    MEM_B = 3
    NEXT_PC = 4
    IN = 5


class MEM_WRITE_MUX(IntEnum):
    NONE = 0
    WRITE_B = 1
    WRITE_W = 2
    WRITE_VECTOR = 3


class AR_MUX(IntEnum):
    NONE = 0
    NEXT_AR = 1
    ALU = 2


class PC_MUX(IntEnum):
    NONE = 0
    NEXT_PC = 1
    ALU = 2


class MPC_MUX(IntEnum):
    INCREMENT = 0
    ZERO = 1
    DISPATCH = 2
    CONDITIONAL = 3


class VALU_OP(IntEnum):
    NONE = 0
    ADD = 1
    SUB = 2
    MUL = 3
    DIV = 4
    SLT = 5


class VREG_WRITE_MUX(IntEnum):
    NONE = 0
    VALU = 1
    MEM = 2


class COND(IntEnum):
    NONE = 0
    ZERO = 1
    NOT_ZERO = 2


def encode(
    alu_op=0,
    alu_left=0,
    alu_right=0,
    reg_write_mux=0,
    mem_write_mux=0,
    ar_mux=0,
    latch_ar=0,
    pc_mux=0,
    latch_pc=0,
    read_input=0,
    reg_write=0,
    latch_out=0,
    data_write=0,
    latch_mpc=0,
    mpc_mux=0,
    valu_op=0,
    vreg_write_mux=0,
    vreg_write=0,
    latch_vl=0,
    vector_lane=0,
    halt=0,
    cond=0
):
    fields = [
        (alu_op,          0,  4),
        (alu_left,        4,  2),
        (alu_right,       6,  2),
        (reg_write_mux,   8,  3),
        (mem_write_mux,  11,  2),
        (ar_mux,         13,  2),
        (latch_ar,       15,  1),
        (pc_mux,         16,  2),
        (latch_pc,       18,  1),
        (read_input,     19,  1),
        (reg_write,      20,  1),
        (latch_out,      21,  1),
        (data_write,     22,  1),
        (latch_mpc,      23,  1),
        (mpc_mux,        24,  2),
        (valu_op,        26,  3),
        (vreg_write_mux, 29,  2),
        (vreg_write,     31,  1),
        (latch_vl,       32,  1),
        (vector_lane,    33,  3),
        (halt,    36,  1),
        (cond,    37,  2)
    ]

    result = 0

    for value, shift, width in fields:
        value = int(value)

        if not 0 <= value < (1 << width):
            raise ValueError(
                f"Value {value} does not fit in {width} bits"
            )

        result |= value << shift

    return result


def decode(microinstruction):
    return {
        "alu_op":         (microinstruction >> 0) & 0xF,
        "alu_left":       (microinstruction >> 4) & 0x3,
        "alu_right":      (microinstruction >> 6) & 0x3,
        "reg_write_mux":  (microinstruction >> 8) & 0x7,
        "mem_write_mux":  (microinstruction >> 11) & 0x3,
        "ar_mux":         (microinstruction >> 13) & 0x3,
        "latch_ar":       (microinstruction >> 15) & 0x1,
        "pc_mux":         (microinstruction >> 16) & 0x3,
        "latch_pc":       (microinstruction >> 18) & 0x1,
        "read_input":     (microinstruction >> 19) & 0x1,
        "reg_write":      (microinstruction >> 20) & 0x1,
        "latch_out":      (microinstruction >> 21) & 0x1,
        "data_write":     (microinstruction >> 22) & 0x1,
        "latch_mpc":      (microinstruction >> 23) & 0x1,
        "mpc_mux":        (microinstruction >> 24) & 0x3,
        "valu_op":        (microinstruction >> 26) & 0x7,
        "vreg_write_mux": (microinstruction >> 29) & 0x3,
        "vreg_write":     (microinstruction >> 31) & 0x1,
        "latch_vl":       (microinstruction >> 32) & 0x1,
        "vector_lane":    (microinstruction >> 33) & 0x7,
        "halt":    (microinstruction >> 36) & 0x1,
        "cond":    (microinstruction >> 37) & 0x3
    }


def setup_micro_memory():
    microcode = []
    descriptions = []
    addresses = {}

    def add_microinstruction(
        description,
        alu_op=ALU_OP.NONE,
        alu_left=ALU_LEFT.NONE,
        alu_right=ALU_RIGHT.NONE,
        reg_write_mux=REG_WRITE_MUX.NONE,
        mem_write_mux=MEM_WRITE_MUX.NONE,
        ar_mux=AR_MUX.NONE,
        latch_ar=0,
        pc_mux=PC_MUX.NONE,
        latch_pc=0,
        read_input=0,
        reg_write=0,
        latch_out=0,
        data_write=0,
        latch_mpc=0,
        mpc_mux=MPC_MUX.INCREMENT,
        valu_op=VALU_OP.NONE,
        vreg_write_mux=VREG_WRITE_MUX.NONE,
        vreg_write=0,
        latch_vl=0,
        vector_lane=0,
        halt=0,
        cond=0
    ):
        index = len(microcode)

        microcode.append(encode(
            alu_op=alu_op,
            alu_left=alu_left,
            alu_right=alu_right,
            reg_write_mux=reg_write_mux,
            mem_write_mux=mem_write_mux,
            ar_mux=ar_mux,
            latch_ar=latch_ar,
            pc_mux=pc_mux,
            latch_pc=latch_pc,
            read_input=read_input,
            reg_write=reg_write,
            latch_out=latch_out,
            data_write=data_write,
            latch_mpc=latch_mpc,
            mpc_mux=mpc_mux,
            valu_op=valu_op,
            vreg_write_mux=vreg_write_mux,
            vreg_write=vreg_write,
            latch_vl=latch_vl,
            vector_lane=vector_lane,
            halt=halt,
            cond=cond
        ))

        descriptions.append(description)

        return index

    addresses["FETCH"] = add_microinstruction(
        "FETCH: Dispatch, PC+=1",
        mpc_mux=MPC_MUX.DISPATCH,
        latch_mpc=1,
        pc_mux=PC_MUX.NEXT_PC,
        latch_pc=1
    )

    addresses["ADDI"] = add_microinstruction(
        "ADDI, goto FETCH",
        alu_op=ALU_OP.ADD,
        alu_left=ALU_LEFT.REG1,
        alu_right=ALU_RIGHT.IMM,
        reg_write_mux=REG_WRITE_MUX.ALU,
        reg_write=1,
        mpc_mux=MPC_MUX.ZERO,
        latch_mpc=1
    )

    addresses["SLTI"] = add_microinstruction(
        "SLTI, goto FETCH",
        alu_op=ALU_OP.SLT,
        alu_left=ALU_LEFT.REG1,
        alu_right=ALU_RIGHT.IMM,
        reg_write_mux=REG_WRITE_MUX.ALU,
        reg_write=1,
        mpc_mux=MPC_MUX.ZERO,
        latch_mpc=1
    )

    addresses["SLTIU"] = add_microinstruction(
        "SLTIU, goto FETCH",
        alu_op=ALU_OP.SLTU,
        alu_left=ALU_LEFT.REG1,
        alu_right=ALU_RIGHT.IMM,
        reg_write_mux=REG_WRITE_MUX.ALU,
        reg_write=1,
        mpc_mux=MPC_MUX.ZERO,
        latch_mpc=1
    )

    addresses["XORI"] = add_microinstruction(
        "XORI, goto FETCH",
        alu_op=ALU_OP.XOR,
        alu_left=ALU_LEFT.REG1,
        alu_right=ALU_RIGHT.IMM,
        reg_write_mux=REG_WRITE_MUX.ALU,
        reg_write=1,
        mpc_mux=MPC_MUX.ZERO,
        latch_mpc=1
    )

    addresses["LUI"] = add_microinstruction(
        "LUI, goto FETCH",
        alu_op=ALU_OP.ADD,
        alu_left=ALU_LEFT.ZERO,
        alu_right=ALU_RIGHT.IMM,
        reg_write_mux=REG_WRITE_MUX.ALU,
        reg_write=1,
        mpc_mux=MPC_MUX.ZERO,
        latch_mpc=1
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
        ("MUL", ALU_OP.MUL),
        ("MULH", ALU_OP.MULH),
        ("DIV", ALU_OP.DIV),
        ("REM", ALU_OP.REM),
    ]

    for name, operation in reg_instructions:
        addresses[name] = add_microinstruction(
            f"{name}, goto FETCH",
            alu_op=operation,
            alu_left=ALU_LEFT.REG1,
            alu_right=ALU_RIGHT.REG2,
            reg_write_mux=REG_WRITE_MUX.ALU,
            reg_write=1,
            mpc_mux=MPC_MUX.ZERO,
            latch_mpc=1
        )

    addresses["JAL"] = add_microinstruction(
        "JAL, goto FETCH",
        alu_op=ALU_OP.ADD,
        alu_left=ALU_LEFT.PC,
        alu_right=ALU_RIGHT.IMM,
        reg_write_mux=REG_WRITE_MUX.NEXT_PC,
        reg_write=1,
        pc_mux=PC_MUX.ALU,
        latch_pc=1,
        mpc_mux=MPC_MUX.ZERO,
        latch_mpc=1
    )

    addresses["JALR"] = add_microinstruction(
        "JALR, goto FETCH",
        alu_op=ALU_OP.ADD,
        alu_left=ALU_LEFT.REG1,
        alu_right=ALU_RIGHT.IMM,
        reg_write_mux=REG_WRITE_MUX.NEXT_PC,
        reg_write=1,
        pc_mux=PC_MUX.ALU,
        latch_pc=1,
        mpc_mux=MPC_MUX.ZERO,
        latch_mpc=1
    )

    addresses["HALT"] = add_microinstruction(
        "HALT",
        halt=1
    )

    def add_branch(name, operation, condition):
        branch_addr = add_microinstruction(
            f"{name}: compare registers",
            alu_op=operation,
            alu_left=ALU_LEFT.REG1,
            alu_right=ALU_RIGHT.REG2,
            mpc_mux=MPC_MUX.CONDITIONAL,
            latch_mpc=1,
            cond=condition
        )

        add_microinstruction(
            f"{name}: branch not taken, goto FETCH",
            mpc_mux=MPC_MUX.ZERO,
            latch_mpc=1
        )

        add_microinstruction(
            f"{name}: branch taken, PC += immediate, goto FETCH",
            alu_op=ALU_OP.ADD,
            alu_left=ALU_LEFT.PC,
            alu_right=ALU_RIGHT.IMM,
            pc_mux=PC_MUX.ALU,
            latch_pc=1,
            mpc_mux=MPC_MUX.ZERO,
            latch_mpc=1
        )

        addresses[name] = branch_addr
        return branch_addr

    add_branch("BEQ",  ALU_OP.SUB,  COND.ZERO)
    add_branch("BNE",  ALU_OP.SUB,  COND.NOT_ZERO)
    add_branch("BLT",  ALU_OP.SLT,  COND.NOT_ZERO)
    add_branch("BGE",  ALU_OP.SLT,  COND.ZERO)
    add_branch("BLTU", ALU_OP.SLTU, COND.NOT_ZERO)
    add_branch("BGEU", ALU_OP.SLTU, COND.ZERO)

    def add_memory_instruction(name, mem_operation, write_operation):
        address = add_microinstruction(
            f"{name}: AR = rs1 + imm",
            alu_op=ALU_OP.ADD,
            alu_left=ALU_LEFT.REG1,
            alu_right=ALU_RIGHT.IMM,
            ar_mux=AR_MUX.ALU,
            latch_ar=1
        )

        add_microinstruction(
            f"{name}: MEMORY OPERATION, goto FETCH",
            reg_write_mux=write_operation,
            reg_write=1 if write_operation != REG_WRITE_MUX.NONE else 0,
            mem_write_mux=mem_operation,
            data_write=1 if mem_operation != MEM_WRITE_MUX.NONE else 0,
            alu_left=ALU_LEFT.ZERO,
            alu_right=ALU_RIGHT.REG2,
            mpc_mux=MPC_MUX.ZERO,
            latch_mpc=1
        )

        addresses[name] = address

    add_memory_instruction("SW", MEM_WRITE_MUX.WRITE_W, REG_WRITE_MUX.NONE)
    add_memory_instruction("SB", MEM_WRITE_MUX.WRITE_B, REG_WRITE_MUX.NONE)
    add_memory_instruction("LW", MEM_WRITE_MUX.NONE, REG_WRITE_MUX.MEM_W)
    add_memory_instruction("LB", MEM_WRITE_MUX.NONE, REG_WRITE_MUX.MEM_B)

    addresses["IN"] = add_microinstruction(
        "IN, goto FETCH",
        read_input=1,
        reg_write_mux=REG_WRITE_MUX.IN,
        reg_write=1,
        mpc_mux=MPC_MUX.ZERO,
        latch_mpc=1
    )

    addresses["OUT"] = add_microinstruction(
        "OUT, goto FETCH",
        alu_left=ALU_LEFT.REG1,
        latch_out=1,
        mpc_mux=MPC_MUX.ZERO,
        latch_mpc=1
    )

    vreg_instructions = [
        ("VADD", VALU_OP.ADD),
        ("VSUB", VALU_OP.SUB),
        ("VSLT", VALU_OP.SLT),
        ("VMUL", VALU_OP.MUL),
        ("VDIV", VALU_OP.DIV),
    ]

    for name, operation in vreg_instructions:
        addresses[name] = add_microinstruction(
            f"{name}, goto FETCH",
            valu_op=operation,
            vreg_write_mux=VREG_WRITE_MUX.VALU,
            vreg_write=1,
            mpc_mux=MPC_MUX.ZERO,
            latch_mpc=1
        )

    addresses["VSETVLI"] = add_microinstruction(
        "VSETVLI, goto FETCH",
        alu_op=ALU_OP.ADD,
        alu_left=ALU_LEFT.ZERO,
        alu_right=ALU_RIGHT.IMM,
        latch_vl=1,
        mpc_mux=MPC_MUX.ZERO,
        latch_mpc=1
    )

    def add_vload(name, lane_count):
        address = add_microinstruction(
            f"{name}: AR = rs1 + imm",
            alu_op=ALU_OP.ADD,
            alu_left=ALU_LEFT.REG1,
            alu_right=ALU_RIGHT.IMM,
            ar_mux=AR_MUX.ALU,
            latch_ar=1
        )

        for lane in range(lane_count):
            add_microinstruction(
                f"{name}: load lane {lane}",
                vreg_write_mux=VREG_WRITE_MUX.MEM,
                vreg_write=1,
                vector_lane=lane,
                ar_mux=AR_MUX.NEXT_AR if lane < lane_count - 1 else AR_MUX.NONE,
                latch_ar=1 if lane < lane_count - 1 else 0,
                mpc_mux=MPC_MUX.ZERO if lane == lane_count - 1 else MPC_MUX.INCREMENT,
                latch_mpc=1
            )

        addresses[name] = address

    add_vload("VLOAD1", 1)
    add_vload("VLOAD2", 2)
    add_vload("VLOAD3", 3)
    add_vload("VLOAD4", 4)

    def add_vstore(name, lane_count):
        address = add_microinstruction(
            f"{name}: AR = rs1 + imm",
            alu_op=ALU_OP.ADD,
            alu_left=ALU_LEFT.REG1,
            alu_right=ALU_RIGHT.IMM,
            ar_mux=AR_MUX.ALU,
            latch_ar=1
        )

        for lane in range(lane_count):
            add_microinstruction(
                f"{name}: store lane {lane}",
                mem_write_mux=MEM_WRITE_MUX.WRITE_VECTOR,
                data_write=1,
                vector_lane=lane,
                ar_mux=AR_MUX.NEXT_AR if lane < lane_count - 1 else AR_MUX.NONE,
                latch_ar=1 if lane < lane_count - 1 else 0,
                mpc_mux=MPC_MUX.ZERO if lane == lane_count - 1 else MPC_MUX.INCREMENT,
                latch_mpc=1
            )

        addresses[name] = address

    add_vstore("VSTORE1", 1)
    add_vstore("VSTORE2", 2)
    add_vstore("VSTORE3", 3)
    add_vstore("VSTORE4", 4)

    return (microcode, descriptions, addresses)
