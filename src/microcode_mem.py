from enum import IntEnum


class AluOp(IntEnum):
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


class AluLeft(IntEnum):
    NONE = 0
    ZERO = 1
    REG1 = 2
    PC = 3


class AluRight(IntEnum):
    NONE = 0
    REG2 = 1
    IMM = 2


class RegWriteMux(IntEnum):
    NONE = 0
    ALU = 1
    MEM_W = 2
    MEM_B = 3
    NEXT_PC = 4
    IN = 5


class MemWriteMux(IntEnum):
    NONE = 0
    WRITE_B = 1
    WRITE_W = 2
    WRITE_VECTOR = 3


class ARMux(IntEnum):
    NONE = 0
    NEXT_AR = 1
    ALU = 2


class PCMux(IntEnum):
    NONE = 0
    NEXT_PC = 1
    ALU = 2


class MPCMux(IntEnum):
    INCREMENT = 0
    ZERO = 1
    DISPATCH = 2
    CONDITIONAL = 3


class ValuOp(IntEnum):
    NONE = 0
    ADD = 1
    SUB = 2
    MUL = 3
    DIV = 4
    SLT = 5


class VregWriteMux(IntEnum):
    NONE = 0
    VALU = 1
    MEM = 2


class Cond(IntEnum):
    NONE = 0
    ZERO = 1
    NOT_ZERO = 2


class Microcode:
    def __init__(self):
        self.microcode = []
        self.descriptions = []
        self.addresses = {}

        self.add_fetch()
        self.add_immediate_instructions()
        self.add_register_instructions()
        self.add_jump_instructions()
        self.add_halt()
        self.add_branch_instructions()
        self.add_memory_instructions()
        self.add_io_instructions()
        self.add_vector_instructions()
        self.add_vector_load_instructions()
        self.add_vector_store_instructions()

    @staticmethod
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
        reg_write=0,
        port_write=0,
        data_write=0,
        latch_mpc=0,
        mpc_mux=0,
        valu_op=0,
        vreg_write_mux=0,
        vreg_write=0,
        latch_vl=0,
        vector_lane=0,
        halt=0,
        cond=0,
    ):
        fields = [
            (alu_op, 0, 4),
            (alu_left, 4, 2),
            (alu_right, 6, 2),
            (reg_write_mux, 8, 3),
            (mem_write_mux, 11, 2),
            (ar_mux, 13, 2),
            (latch_ar, 15, 1),
            (pc_mux, 16, 2),
            (latch_pc, 18, 1),
            (reg_write, 19, 1),
            (port_write, 20, 1),
            (data_write, 21, 1),
            (latch_mpc, 22, 1),
            (mpc_mux, 23, 2),
            (valu_op, 25, 3),
            (vreg_write_mux, 28, 2),
            (vreg_write, 30, 1),
            (latch_vl, 31, 1),
            (vector_lane, 32, 3),
            (halt, 35, 1),
            (cond, 36, 2),
        ]

        result = 0

        for value, shift, width in fields:
            value = int(value)

            if not 0 <= value < (1 << width):
                msg = f"Value {value} does not fit in {width} bits"
                raise ValueError(msg)

            result |= value << shift

        return result

    @staticmethod
    def decode(microinstruction):
        return {
            "alu_op": (microinstruction >> 0) & 0xF,
            "alu_left": (microinstruction >> 4) & 0x3,
            "alu_right": (microinstruction >> 6) & 0x3,
            "reg_write_mux": (microinstruction >> 8) & 0x7,
            "mem_write_mux": (microinstruction >> 11) & 0x3,
            "ar_mux": (microinstruction >> 13) & 0x3,
            "latch_ar": (microinstruction >> 15) & 0x1,
            "pc_mux": (microinstruction >> 16) & 0x3,
            "latch_pc": (microinstruction >> 18) & 0x1,
            "reg_write": (microinstruction >> 19) & 0x1,
            "port_write": (microinstruction >> 20) & 0x1,
            "data_write": (microinstruction >> 21) & 0x1,
            "latch_mpc": (microinstruction >> 22) & 0x1,
            "mpc_mux": (microinstruction >> 23) & 0x3,
            "valu_op": (microinstruction >> 25) & 0x7,
            "vreg_write_mux": (microinstruction >> 28) & 0x3,
            "vreg_write": (microinstruction >> 30) & 0x1,
            "latch_vl": (microinstruction >> 31) & 0x1,
            "vector_lane": (microinstruction >> 32) & 0x7,
            "halt": (microinstruction >> 35) & 0x1,
            "cond": (microinstruction >> 36) & 0x3,
        }

    def add_microinstruction(
        self,
        description,
        alu_op=AluOp.NONE,
        alu_left=AluLeft.NONE,
        alu_right=AluRight.NONE,
        reg_write_mux=RegWriteMux.NONE,
        mem_write_mux=MemWriteMux.NONE,
        ar_mux=ARMux.NONE,
        latch_ar=0,
        pc_mux=PCMux.NONE,
        latch_pc=0,
        reg_write=0,
        port_write=0,
        data_write=0,
        latch_mpc=1,
        mpc_mux=MPCMux.INCREMENT,
        valu_op=ValuOp.NONE,
        vreg_write_mux=VregWriteMux.NONE,
        vreg_write=0,
        latch_vl=0,
        vector_lane=0,
        halt=0,
        cond=0,
    ):
        index = len(self.microcode)

        self.microcode.append(
            self.encode(
                alu_op=alu_op,
                alu_left=alu_left,
                alu_right=alu_right,
                reg_write_mux=reg_write_mux,
                mem_write_mux=mem_write_mux,
                ar_mux=ar_mux,
                latch_ar=latch_ar,
                pc_mux=pc_mux,
                latch_pc=latch_pc,
                reg_write=reg_write,
                port_write=port_write,
                data_write=data_write,
                latch_mpc=latch_mpc,
                mpc_mux=mpc_mux,
                valu_op=valu_op,
                vreg_write_mux=vreg_write_mux,
                vreg_write=vreg_write,
                latch_vl=latch_vl,
                vector_lane=vector_lane,
                halt=halt,
                cond=cond,
            )
        )

        self.descriptions.append(description)

        return index

    def add_fetch(self):
        self.addresses["FETCH"] = self.add_microinstruction(
            "FETCH: Dispatch, PC+=4",
            mpc_mux=MPCMux.DISPATCH,
            latch_mpc=1,
            pc_mux=PCMux.NEXT_PC,
            latch_pc=1,
        )

    def add_immediate_instructions(self):
        instructions = [
            ("ADDI", AluOp.ADD, AluLeft.REG1),
            ("SLTI", AluOp.SLT, AluLeft.REG1),
            ("SLTIU", AluOp.SLTU, AluLeft.REG1),
            ("XORI", AluOp.XOR, AluLeft.REG1),
            ("LUI", AluOp.ADD, AluLeft.ZERO),
        ]

        for name, operation, left in instructions:
            self.addresses[name] = self.add_microinstruction(
                f"{name}, goto FETCH",
                alu_op=operation,
                alu_left=left,
                alu_right=AluRight.IMM,
                reg_write_mux=RegWriteMux.ALU,
                reg_write=1,
                mpc_mux=MPCMux.ZERO,
                latch_mpc=1,
            )

    def add_register_instructions(self):
        instructions = [
            ("ADD", AluOp.ADD),
            ("SUB", AluOp.SUB),
            ("SLT", AluOp.SLT),
            ("SLTU", AluOp.SLTU),
            ("AND", AluOp.AND),
            ("OR", AluOp.OR),
            ("XOR", AluOp.XOR),
            ("SLL", AluOp.SLL),
            ("SRL", AluOp.SRL),
            ("SRA", AluOp.SRA),
            ("MUL", AluOp.MUL),
            ("MULH", AluOp.MULH),
            ("DIV", AluOp.DIV),
            ("REM", AluOp.REM),
        ]

        for name, operation in instructions:
            self.addresses[name] = self.add_microinstruction(
                f"{name}, goto FETCH",
                alu_op=operation,
                alu_left=AluLeft.REG1,
                alu_right=AluRight.REG2,
                reg_write_mux=RegWriteMux.ALU,
                reg_write=1,
                mpc_mux=MPCMux.ZERO,
                latch_mpc=1,
            )

    def add_jump_instructions(self):
        instructions = [
            ("JAL", AluLeft.PC),
            ("JALR", AluLeft.REG1),
        ]

        for name, left in instructions:
            self.addresses[name] = self.add_microinstruction(
                f"{name}, goto FETCH",
                alu_op=AluOp.ADD,
                alu_left=left,
                alu_right=AluRight.IMM,
                reg_write_mux=RegWriteMux.NEXT_PC,
                reg_write=1,
                pc_mux=PCMux.ALU,
                latch_pc=1,
                mpc_mux=MPCMux.ZERO,
                latch_mpc=1,
            )

    def add_halt(self):
        self.addresses["HALT"] = self.add_microinstruction("HALT", halt=1)

    def add_branch_instructions(self):
        instructions = [
            ("BEQ", AluOp.SUB, Cond.ZERO),
            ("BNE", AluOp.SUB, Cond.NOT_ZERO),
            ("BLT", AluOp.SLT, Cond.NOT_ZERO),
            ("BGE", AluOp.SLT, Cond.ZERO),
            ("BLTU", AluOp.SLTU, Cond.NOT_ZERO),
            ("BGEU", AluOp.SLTU, Cond.ZERO),
        ]

        for name, operation, condition in instructions:
            self.addresses[name] = self.add_branch(name, operation, condition)

    def add_branch(self, name, operation, condition):
        address = self.add_microinstruction(
            f"{name}: compare registers",
            alu_op=operation,
            alu_left=AluLeft.REG1,
            alu_right=AluRight.REG2,
            mpc_mux=MPCMux.CONDITIONAL,
            latch_mpc=1,
            cond=condition,
        )

        self.add_microinstruction(
            f"{name}: branch not taken, goto FETCH",
            mpc_mux=MPCMux.ZERO,
            latch_mpc=1,
        )

        self.add_microinstruction(
            f"{name}: branch taken, PC += immediate, goto FETCH",
            alu_op=AluOp.ADD,
            alu_left=AluLeft.PC,
            alu_right=AluRight.IMM,
            pc_mux=PCMux.ALU,
            latch_pc=1,
            mpc_mux=MPCMux.ZERO,
            latch_mpc=1,
        )

        return address

    def add_memory_instructions(self):
        instructions = [
            ("SW", MemWriteMux.WRITE_W, RegWriteMux.NONE),
            ("SB", MemWriteMux.WRITE_B, RegWriteMux.NONE),
            ("LW", MemWriteMux.NONE, RegWriteMux.MEM_W),
            ("LB", MemWriteMux.NONE, RegWriteMux.MEM_B),
        ]

        for name, mem_operation, write_operation in instructions:
            self.addresses[name] = self.add_memory_instruction(name, mem_operation, write_operation)

    def add_memory_instruction(self, name, mem_operation, write_operation):
        address = self.add_microinstruction(
            f"{name}: AR = rs1 + imm",
            alu_op=AluOp.ADD,
            alu_left=AluLeft.REG1,
            alu_right=AluRight.IMM,
            ar_mux=ARMux.ALU,
            latch_ar=1,
        )

        self.add_microinstruction(
            f"{name}: MEMORY OPERATION, goto FETCH",
            reg_write_mux=write_operation,
            reg_write=int(write_operation != RegWriteMux.NONE),
            mem_write_mux=mem_operation,
            data_write=int(mem_operation != MemWriteMux.NONE),
            alu_left=AluLeft.ZERO,
            alu_right=AluRight.REG2,
            mpc_mux=MPCMux.ZERO,
            latch_mpc=1,
        )

        return address

    def add_io_instructions(self):
        self.addresses["IN"] = self.add_microinstruction(
            "IN, goto FETCH",
            reg_write_mux=RegWriteMux.IN,
            reg_write=1,
            mpc_mux=MPCMux.ZERO,
            latch_mpc=1,
        )

        self.addresses["OUT"] = self.add_microinstruction(
            "OUT, goto FETCH",
            alu_left=AluLeft.REG1,
            port_write=1,
            mpc_mux=MPCMux.ZERO,
            latch_mpc=1,
        )

    def add_vector_instructions(self):
        instructions = [
            ("VADD", ValuOp.ADD),
            ("VSUB", ValuOp.SUB),
            ("VSLT", ValuOp.SLT),
            ("VMUL", ValuOp.MUL),
            ("VDIV", ValuOp.DIV),
        ]

        for name, operation in instructions:
            self.addresses[name] = self.add_microinstruction(
                f"{name}, goto FETCH",
                valu_op=operation,
                vreg_write_mux=VregWriteMux.VALU,
                vreg_write=1,
                mpc_mux=MPCMux.ZERO,
                latch_mpc=1,
            )

        self.addresses["VSETVLI"] = self.add_microinstruction(
            "VSETVLI, goto FETCH",
            alu_op=AluOp.ADD,
            alu_left=AluLeft.ZERO,
            alu_right=AluRight.IMM,
            latch_vl=1,
            mpc_mux=MPCMux.ZERO,
            latch_mpc=1,
        )

    def add_vector_load_instructions(self):
        for lane_count in range(1, 5):
            name = f"VLOAD{lane_count}"
            self.addresses[name] = self.add_vector_load(name, lane_count)

    def add_vector_load(self, name, lane_count):
        address = self.add_microinstruction(
            f"{name}: AR = rs1 + imm",
            alu_op=AluOp.ADD,
            alu_left=AluLeft.REG1,
            alu_right=AluRight.IMM,
            ar_mux=ARMux.ALU,
            latch_ar=1,
        )

        for lane in range(lane_count):
            is_last = lane == lane_count - 1

            self.add_microinstruction(
                f"{name}: load lane {lane}",
                vreg_write_mux=VregWriteMux.MEM,
                vreg_write=1,
                vector_lane=lane,
                ar_mux=ARMux.NONE if is_last else ARMux.NEXT_AR,
                latch_ar=int(not is_last),
                mpc_mux=MPCMux.ZERO if is_last else MPCMux.INCREMENT,
                latch_mpc=1,
            )

        return address

    def add_vector_store_instructions(self):
        for lane_count in range(1, 5):
            name = f"VSTORE{lane_count}"
            self.addresses[name] = self.add_vector_store(name, lane_count)

    def add_vector_store(self, name, lane_count):
        address = self.add_microinstruction(
            f"{name}: AR = rs1 + imm",
            alu_op=AluOp.ADD,
            alu_left=AluLeft.REG1,
            alu_right=AluRight.IMM,
            ar_mux=ARMux.ALU,
            latch_ar=1,
        )

        for lane in range(lane_count):
            is_last = lane == lane_count - 1

            self.add_microinstruction(
                f"{name}: store lane {lane}",
                mem_write_mux=MemWriteMux.WRITE_VECTOR,
                data_write=1,
                vector_lane=lane,
                ar_mux=ARMux.NONE if is_last else ARMux.NEXT_AR,
                latch_ar=int(not is_last),
                mpc_mux=MPCMux.ZERO if is_last else MPCMux.INCREMENT,
                latch_mpc=1,
            )

        return address
