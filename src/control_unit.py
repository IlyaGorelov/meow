from microcode_mem import *
from data_path import DataPath
from isa import Opcode, opcode_to_binary, binary_to_opcode

microcode_data = setup_micro_memory()


class ControlUnit:
    addresses = microcode_data[2]

    dispatch_table = {
        # Immediate instructions
        (Opcode.OPIMM, 0b000): addresses["ADDI"],
        (Opcode.OPIMM, 0b001): addresses["SLTI"],
        (Opcode.OPIMM, 0b010): addresses["SLTIU"],
        (Opcode.OPIMM, 0b011): addresses["XORI"],

        # Upper immediate
        Opcode.LUI: addresses["LUI"],

        # Register instructions: funct3, funct7
        (Opcode.OP, 0b000, 0b0000000): addresses["ADD"],
        (Opcode.OP, 0b001, 0b0000000): addresses["SUB"],
        (Opcode.OP, 0b010, 0b0000000): addresses["SLT"],
        (Opcode.OP, 0b011, 0b0000000): addresses["SLTU"],
        (Opcode.OP, 0b100, 0b0000000): addresses["AND"],
        (Opcode.OP, 0b101, 0b0000000): addresses["XOR"],
        (Opcode.OP, 0b110, 0b0000000): addresses["OR"],
        (Opcode.OP, 0b111, 0b0000000): addresses["SLL"],
        (Opcode.OP, 0b001, 0b0000001): addresses["SRL"],
        (Opcode.OP, 0b010, 0b0000001): addresses["SRA"],
        (Opcode.OP, 0b011, 0b0000001): addresses["MUL"],
        (Opcode.OP, 0b100, 0b0000001): addresses["MULH"],
        (Opcode.OP, 0b101, 0b0000001): addresses["DIV"],
        (Opcode.OP, 0b110, 0b0000001): addresses["REM"],

        # Jumps
        Opcode.JAL: addresses["JAL"],
        Opcode.JALR: addresses["JALR"],

        # Halt
        Opcode.HALT: addresses["HALT"],

        # Branches
        (Opcode.BRANCH, 0b000): addresses["BLT"],
        (Opcode.BRANCH, 0b001): addresses["BGE"],
        (Opcode.BRANCH, 0b010): addresses["BEQ"],
        (Opcode.BRANCH, 0b011): addresses["BNE"],
        (Opcode.BRANCH, 0b100): addresses["BLTU"],

        # Loads
        (Opcode.LOAD, 0b000): addresses["LW"],
        (Opcode.LOAD, 0b001): addresses["LB"],

        # Stores
        (Opcode.STORE, 0b000): addresses["SW"],
        (Opcode.STORE, 0b001): addresses["SB"],

        # I/O
        Opcode.IN: addresses["IN"],
        Opcode.OUT: addresses["OUT"],

        # Vector arithmetic
        (Opcode.VECTOR, 0b000): addresses["VADD"],
        (Opcode.VECTOR, 0b001): addresses["VSUB"],
        (Opcode.VECTOR, 0b010): addresses["VMUL"],
        (Opcode.VECTOR, 0b011): addresses["VDIV"],
        (Opcode.VECTOR, 0b100): addresses["VSLT"],

        # Vector memory
        (Opcode.VLOAD, 1): addresses["VLOAD1"],
        (Opcode.VLOAD, 2): addresses["VLOAD2"],
        (Opcode.VLOAD, 3): addresses["VLOAD3"],
        (Opcode.VLOAD, 4): addresses["VLOAD4"],

        (Opcode.VSTORE, 1): addresses["VSTORE1"],
        (Opcode.VSTORE, 2): addresses["VSTORE2"],
        (Opcode.VSTORE, 3): addresses["VSTORE3"],
        (Opcode.VSTORE, 4): addresses["VSTORE4"],

        # Vector length
        Opcode.VSETVLI: addresses["VSETVLI"],
    }

    def __init__(self, data_path: DataPath):
        self.data_path = data_path
        self.microcode = microcode_data[0]
        self.mc_descriptions = microcode_data[1]

        self.micro_pc = 0
        self._tick = 0

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def process_next_tick(self):
        micro_instr = self.microcode[self.micro_pc]

        self.execute_micro_instr(micro_instr)

    def execute_micro_instr(self, micro_instr):
        decoded = decode(micro_instr)
        signals = []

        if decoded["mpc_mux"] == MPC_MUX.DISPATCH:
            signals.append((self.dispatch, 0))

        if decoded["read_input"]:
            signals.append((self.data_path.input_read, 1))

        if decoded["alu_left"] != ALU_LEFT.NONE:
            t = ALU_LEFT(decoded["alu_left"])
            signals.append((
                lambda t=t: self.data_path.left_alu_sel(t.name.lower()),
                2
            ))

        if decoded["alu_right"] != ALU_RIGHT.NONE:
            t = ALU_RIGHT(decoded["alu_right"])
            signals.append((
                lambda t=t: self.data_path.right_alu_sel(t.name.lower()),
                2
            ))

        if decoded["alu_op"] != ALU_OP.NONE:
            t = ALU_OP(decoded["alu_op"])
            signals.append((
                lambda t=t: self.data_path.alu(t.name.lower()),
                3
            ))

        if decoded["valu_op"] != VALU_OP.NONE:
            t = VALU_OP(decoded["valu_op"])
            signals.append((
                lambda t=t: self.data_path.vector_alu(t.name.lower()),
                3
            ))

        if decoded["latch_vl"]:
            signals.append((self.data_path.latch_vl, 4))

        if decoded["data_write"]:
            t = MEM_WRITE_MUX(decoded["mem_write_mux"])
            lane = decoded["vector_lane"]

            if t == MEM_WRITE_MUX.WRITE_B:
                signals.append((
                    lambda: self.data_path.data_write("write_b"),
                    5
                ))

            elif t == MEM_WRITE_MUX.WRITE_W:
                signals.append((
                    lambda: self.data_path.data_write("write_w"),
                    5
                ))

            elif t == MEM_WRITE_MUX.WRITE_VECTOR:
                signals.append((
                    lambda lane=lane: self.data_path.data_write(
                        "write_vector", lane
                    ),
                    5
                ))

        if decoded["reg_write"]:
            t = REG_WRITE_MUX(decoded["reg_write_mux"])

            signals.append((
                lambda: self.data_path.reg_write(t.name.lower()),
                6
            ))

        if decoded["vreg_write"]:
            t = VREG_WRITE_MUX(decoded["vreg_write_mux"])
            lane = decoded["vector_lane"]

            signals.append((
                lambda t=t, lane=lane:
                    self.data_path.vreg_write(t.name.lower(), lane),
                6
            ))

        if decoded["latch_ar"]:
            t = AR_MUX(decoded["ar_mux"])
            signals.append((
                lambda t=t: self.data_path.latch_ar(t.name.lower()),
                7
            ))

        if decoded["latch_pc"]:
            t = PC_MUX(decoded["pc_mux"])
            signals.append((
                lambda t=t: self.data_path.latch_pc(t.name.lower()),
                8
            ))

        if decoded["latch_out"]:
            signals.append((self.data_path.latch_out, 9))

        signals.sort(key=lambda x: x[1])

        for method, priority in signals:
            method()

        if decoded["halt"]:
            raise StopIteration("Halt")

        mpc_mux = MPC_MUX(decoded["mpc_mux"])

        if mpc_mux == MPC_MUX.INCREMENT:
            self.micro_pc += 1

        elif mpc_mux == MPC_MUX.ZERO:
            self.micro_pc = 0

        elif mpc_mux == MPC_MUX.CONDITIONAL:
            cond = COND(decoded["cond"])

            condition_met = (
                self.data_path.alu_result == 0
                if cond == COND.ZERO
                else self.data_path.alu_result != 0
            )

            self.micro_pc += 2 if condition_met else 1

        self.tick()

    def dispatch(self):
        instr = self.data_path.instruction_read()
        opcode = binary_to_opcode[instr & 0x1F]
        funct3 = (instr >> 12) & 0b111
        funct7 = (instr >> 25) & 0b1111111  

        if opcode == Opcode.OP:
            key = (opcode,funct3,funct7)

        elif opcode in (Opcode.OPIMM, Opcode.LOAD, Opcode.STORE, Opcode.BRANCH):
            key = (opcode, funct3)
            
        elif opcode in (Opcode.VLOAD, Opcode.VSTORE):
            key = (opcode, self.data_path.vl)

        else:
            key = opcode

        self.micro_pc = self.dispatch_table[key]

    def __repr__(self):
        state_repr = "TICK: {:3} PC: {:3}/{} RA: {:3}".format(
            self._tick,
            self.data_path.pc,
            self.micro_pc,
            self.data_path.ar,
        )

        instr_repr = self.mc_descriptions[self.micro_pc]
        # if self.current_instr:
        #     opcode = self.current_instr["opcode"]
        #     instr_repr = str(opcode)

        return "{} \t{}".format(state_repr, instr_repr)
