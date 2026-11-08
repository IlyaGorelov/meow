from microcode_mem import *
from data_path import DataPath
from isa import Opcode, opcode_to_binary

microcode_data = setup_micro_memory()

class ControlUnit:
    addresses = microcode_data[2]

    dispatch_table = {
        # Immediate instructions
        (Opcode.OPIMM, 0b000): addresses["ADDI"],
        (Opcode.OPIMM, 0b010): addresses["SLTI"],
        Opcode.LUI: addresses["LUI"],
        (Opcode.OPIMM, 0b100): addresses["XORI"],
        (Opcode.OPIMM, 0b011): addresses["SLTIU"],

        # Register instructions
        (Opcode.OP, 0b000, 0b0000000): addresses["ADD"],
        (Opcode.OP, 0b000, 0b0100000): addresses["SUB"],
        (Opcode.OP, 0b010, 0b0000000): addresses["SLT"],
        (Opcode.OP, 0b011, 0b0000000): addresses["SLTU"],
        (Opcode.OP, 0b111, 0b0000000): addresses["AND"],
        (Opcode.OP, 0b110, 0b0000000): addresses["OR"],
        (Opcode.OP, 0b100, 0b0000000): addresses["XOR"],
        (Opcode.OP, 0b001, 0b0000000): addresses["SLL"],
        (Opcode.OP, 0b101, 0b0000000): addresses["SRL"],
        (Opcode.OP, 0b101, 0b0100000): addresses["SRA"],

        # Jumps
        Opcode.JAL: addresses["JAL"],
        Opcode.JALR: addresses["JALR"],

        # Halt
        Opcode.HALT: addresses["HALT"],

        # Branches
        (Opcode.BRANCH, 0b100): addresses["BLT"],
        (Opcode.BRANCH, 0b110): addresses["BLTU"],
        (Opcode.BRANCH, 0b101): addresses["BGE"],
        (Opcode.BRANCH, 0b000): addresses["BEQ"],
        (Opcode.BRANCH, 0b001): addresses["BNE"],

        # Loads and stores
        (Opcode.STORE, 0b010): addresses["SW"],
        (Opcode.STORE, 0b000): addresses["SB"],
        (Opcode.LOAD, 0b010): addresses["LW"],
        (Opcode.LOAD, 0b000): addresses["LB"],

        # IO
        Opcode.IN: addresses["IN"],
        Opcode.OUT: addresses["OUT"]
    }

    def __init__(self, program, data_path : DataPath):
        self.program = program

        self.data_path = data_path
        self.microcode = microcode_data[0]
        self.mc_descriptions = microcode_data[1]

        self.current_instr = None

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

        ctrl = CTRL(decoded["ctrl"])

        if ctrl & CTRL.DISPATCH:
            signals.append((self.dispatch, 0))

        if ctrl & CTRL.REG1_SEL:
            signals.append((
                lambda: self.data_path.reg1_sel(self.current_instr["rs1"]),
                1
            ))

        if ctrl & CTRL.REG2_SEL:
            signals.append((
                lambda: self.data_path.reg2_sel(
                    self.current_instr.get("rs2", self.current_instr["rs1"])
                    ),
                1
            ))

        if ctrl & CTRL.INPUT_READ:
            signals.append((self.data_path.input_read, 1))

        if decoded["alu_left"] != ALU_LEFT.NONE:
            t = ALU_LEFT(decoded["alu_left"])
            signals.append((
                lambda t=t: self.data_path.left_alu_sel(t.name.lower()),
                2
            ))

        if decoded["alu_right"] != ALU_RIGHT.NONE:
            t = ALU_RIGHT(decoded["alu_right"])

            if t == ALU_RIGHT.IMM:
                signals.append((
                    lambda: self.data_path.right_alu_sel(
                        "imm", self.current_instr["imm"]
                    ),
                    2
                ))
            else:
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

        if decoded["mem"] != MEM.NONE:
            t = MEM(decoded["mem"])

            if t == MEM.LATCH_AR:
                signals.append((self.data_path.latch_ar, 4))
            elif t == MEM.WRITE_W:
                signals.append((
                    lambda: self.data_path.data_write(4), 4
                ))
            elif t == MEM.WRITE_B:
                signals.append((
                    lambda: self.data_path.data_write(1), 4
                ))

        if decoded["reg_write"] != REG_WRITE.NONE:
            t = REG_WRITE(decoded["reg_write"])
            signals.append((
                lambda t=t: self.data_path.reg_write(
                    t.name.lower(), self.current_instr["rd"]
                ),
                5
            ))

        if decoded["pc"] != PC.NONE:
            t = PC(decoded["pc"])

            if t == PC.NEXT_PC:
                signals.append((lambda: self.data_path.latch_pc("next_pc"), 6))
            elif t == PC.ALU:
                signals.append((lambda: self.data_path.latch_pc("alu"), 6))

        if ctrl & CTRL.OUTPUT:
            signals.append((self.data_path.latch_out, 7))

        signals.sort(key=lambda x: x[1])

        for method, priority in signals:
            method()

        if ctrl & CTRL.HALT:
            raise StopIteration("Halt")

        elif decoded["cond"] != COND.NONE:
            cond = COND(decoded["cond"])

            condition_met = (
                self.data_path.alu_result == 0
                if cond == COND.ZERO
                else self.data_path.alu_result != 0
            )

            if condition_met:
                self.micro_pc = decoded["next"]
            else:
                self.micro_pc += 1

        else:
            if not (ctrl & CTRL.DISPATCH):
                self.micro_pc = decoded["next"]

        self.tick()

    

    def dispatch(self):
        self.current_instr = self.program[self.data_path.pc // 4]

        instr = self.current_instr
        opcode = instr["opcode"]

        if opcode == Opcode.OP:
            key = (opcode, instr["funct3"], instr["funct7"])

        elif opcode in (Opcode.OPIMM, Opcode.LOAD, Opcode.STORE, Opcode.BRANCH):
            key = (opcode, instr["funct3"])

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