from data_path import DataPath
from isa import Opcode, binary_to_opcode
from microcode_mem import (
    AluLeft,
    AluOp,
    AluRight,
    ARMux,
    Cond,
    MemWriteMux,
    Microcode,
    MPCMux,
    PCMux,
    RegWriteMux,
    ValuOp,
    VregWriteMux,
)

microcode = Microcode()


class ControlUnit:
    def __init__(self, data_path: DataPath):
        self.data_path = data_path
        self.microcode = microcode.microcode
        self.mc_descriptions = microcode.descriptions

        self.micro_pc = 0
        self._tick = 0

        self.addresses = microcode.addresses
        self.dispatch_table = {
            (Opcode.OPIMM, 0b000): self.addresses["ADDI"],
            (Opcode.OPIMM, 0b001): self.addresses["SLTI"],
            (Opcode.OPIMM, 0b010): self.addresses["SLTIU"],
            (Opcode.OPIMM, 0b011): self.addresses["XORI"],
            Opcode.LUI: self.addresses["LUI"],
            (Opcode.OP, 0b000, 0b0000000): self.addresses["ADD"],
            (Opcode.OP, 0b001, 0b0000000): self.addresses["SUB"],
            (Opcode.OP, 0b010, 0b0000000): self.addresses["SLT"],
            (Opcode.OP, 0b011, 0b0000000): self.addresses["SLTU"],
            (Opcode.OP, 0b100, 0b0000000): self.addresses["AND"],
            (Opcode.OP, 0b101, 0b0000000): self.addresses["XOR"],
            (Opcode.OP, 0b110, 0b0000000): self.addresses["OR"],
            (Opcode.OP, 0b111, 0b0000000): self.addresses["SLL"],
            (Opcode.OP, 0b001, 0b0000001): self.addresses["SRL"],
            (Opcode.OP, 0b010, 0b0000001): self.addresses["SRA"],
            (Opcode.OP, 0b011, 0b0000001): self.addresses["MUL"],
            (Opcode.OP, 0b100, 0b0000001): self.addresses["MULH"],
            (Opcode.OP, 0b101, 0b0000001): self.addresses["DIV"],
            (Opcode.OP, 0b110, 0b0000001): self.addresses["REM"],
            Opcode.JAL: self.addresses["JAL"],
            Opcode.JALR: self.addresses["JALR"],
            Opcode.HALT: self.addresses["HALT"],
            (Opcode.BRANCH, 0b000): self.addresses["BLT"],
            (Opcode.BRANCH, 0b001): self.addresses["BGE"],
            (Opcode.BRANCH, 0b010): self.addresses["BEQ"],
            (Opcode.BRANCH, 0b011): self.addresses["BNE"],
            (Opcode.BRANCH, 0b100): self.addresses["BLTU"],
            (Opcode.LOAD, 0b000): self.addresses["LW"],
            (Opcode.LOAD, 0b001): self.addresses["LB"],
            (Opcode.STORE, 0b000): self.addresses["SW"],
            (Opcode.STORE, 0b001): self.addresses["SB"],
            Opcode.IN: self.addresses["IN"],
            Opcode.OUT: self.addresses["OUT"],
            (Opcode.VECTOR, 0b000): self.addresses["VADD"],
            (Opcode.VECTOR, 0b001): self.addresses["VSUB"],
            (Opcode.VECTOR, 0b010): self.addresses["VMUL"],
            (Opcode.VECTOR, 0b011): self.addresses["VDIV"],
            (Opcode.VECTOR, 0b100): self.addresses["VSLT"],
            (Opcode.VLOAD, 1): self.addresses["VLOAD1"],
            (Opcode.VLOAD, 2): self.addresses["VLOAD2"],
            (Opcode.VLOAD, 3): self.addresses["VLOAD3"],
            (Opcode.VLOAD, 4): self.addresses["VLOAD4"],
            (Opcode.VSTORE, 1): self.addresses["VSTORE1"],
            (Opcode.VSTORE, 2): self.addresses["VSTORE2"],
            (Opcode.VSTORE, 3): self.addresses["VSTORE3"],
            (Opcode.VSTORE, 4): self.addresses["VSTORE4"],
            Opcode.VSETVLI: self.addresses["VSETVLI"],
        }

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def process_next_tick(self):
        micro_instr = self.microcode[self.micro_pc]

        self.execute_micro_instr(micro_instr)

    def execute_micro_instr(self, micro_instr):  # noqa: C901
        decoded = microcode.decode(micro_instr)
        signals = []

        if decoded["latch_mpc"] == 1:
            cond = Cond(decoded["cond"])
            mpc_mux = MPCMux(decoded["mpc_mux"])
            signals.append((lambda mpc_mux=mpc_mux, cond=cond: self.latch_mpc(mpc_mux, cond), 0))

        if decoded["latch_pc"]:
            t = PCMux(decoded["pc_mux"])
            signals.append((lambda t=t: self.data_path.latch_pc(t.name.lower()), 6))

        if decoded["alu_left"] != AluLeft.NONE:
            t = AluLeft(decoded["alu_left"])
            signals.append((lambda t=t: self.data_path.left_alu_sel(t.name.lower()), 2))

        if decoded["alu_right"] != AluRight.NONE:
            t = AluRight(decoded["alu_right"])
            signals.append((lambda t=t: self.data_path.right_alu_sel(t.name.lower()), 2))

        if decoded["alu_op"] != AluOp.NONE:
            t = AluOp(decoded["alu_op"])
            signals.append((lambda t=t: self.data_path.alu(t.name.lower()), 3))

        if decoded["valu_op"] != ValuOp.NONE:
            t = ValuOp(decoded["valu_op"])
            signals.append((lambda t=t: self.data_path.vector_alu(t.name.lower()), 2))

        if decoded["latch_vl"]:
            signals.append((self.data_path.latch_vl, 4))

        if decoded["data_write"]:
            t = MemWriteMux(decoded["mem_write_mux"])
            lane = decoded["vector_lane"]

            if t == MemWriteMux.WRITE_B:
                signals.append((lambda: self.data_path.data_write("write_b"), 5))

            elif t == MemWriteMux.WRITE_W:
                signals.append((lambda: self.data_path.data_write("write_w"), 5))

            elif t == MemWriteMux.WRITE_VECTOR:
                signals.append((lambda lane=lane: self.data_path.data_write("write_vector", lane), 5))

        if decoded["reg_write"]:
            reg_mux = RegWriteMux(decoded["reg_write_mux"])

            signals.append((lambda: self.data_path.reg_write(reg_mux.name.lower()), 6))

        if decoded["vreg_write"]:
            t = VregWriteMux(decoded["vreg_write_mux"])
            lane = decoded["vector_lane"]

            signals.append((lambda t=t, lane=lane: self.data_path.vreg_write(t.name.lower(), lane), 6))

        if decoded["latch_ar"]:
            t = ARMux(decoded["ar_mux"])
            signals.append((lambda t=t: self.data_path.latch_ar(t.name.lower()), 6))

        if decoded["port_write"]:
            signals.append((self.data_path.port_write, 2))

        signals.sort(key=lambda x: x[1])

        for method, priority in signals:
            method()

        if decoded["halt"]:
            raise StopIteration("Halt")

        self.tick()

    def latch_mpc(self, mpc_mux, cond):
        if mpc_mux == MPCMux.DISPATCH:
            self.dispatch()
        elif mpc_mux == MPCMux.INCREMENT:
            self.micro_pc += 1

        elif mpc_mux == MPCMux.ZERO:
            self.micro_pc = 0

        elif mpc_mux == MPCMux.CONDITIONAL:
            condition_met = self.data_path.alu_result == 0 if cond == Cond.ZERO else self.data_path.alu_result != 0

            self.micro_pc += 2 if condition_met else 1

    def dispatch(self):
        instr = self.data_path.instruction_read()
        opcode = binary_to_opcode[instr & 0x1F]
        funct3 = (instr >> 12) & 0b111
        funct7 = (instr >> 25) & 0b1111111

        if opcode == Opcode.OP:
            key = (opcode, funct3, funct7)

        elif opcode in (Opcode.OPIMM, Opcode.LOAD, Opcode.STORE, Opcode.BRANCH, Opcode.VECTOR):
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

        return "{} \t{}".format(state_repr, instr_repr)
