from microcode_mem import *
from data_path import DataPath
from isa import Opcode, opcode_to_binary

class ControlUnit:
    dispatch_table = {
        # Immediate instructions
        (Opcode.OPIMM, 0b000): 1,  # addi
        (Opcode.OPIMM, 0b010): 2,  # slti
        Opcode.LUI: 3,
        (Opcode.OPIMM, 0b100): 4,  # xori
        (Opcode.OPIMM, 0b011): 5,  # sltiu

        # Register-register instructions
        (Opcode.OP, 0b000, 0b0000000): 7,   # add
        (Opcode.OP, 0b000, 0b0100000): 8,   # sub
        (Opcode.OP, 0b010, 0b0000000): 9,   # slt
        (Opcode.OP, 0b011, 0b0000000): 10,  # sltu
        (Opcode.OP, 0b111, 0b0000000): 11,  # and
        (Opcode.OP, 0b110, 0b0000000): 12,  # or
        (Opcode.OP, 0b100, 0b0000000): 13,  # xor
        (Opcode.OP, 0b001, 0b0000000): 14,  # sll
        (Opcode.OP, 0b101, 0b0000000): 15,  # srl
        (Opcode.OP, 0b101, 0b0100000): 16,  # sra

        # Jumps
        Opcode.JAL: 17,
        Opcode.JALR: 18,

        # Halt
        Opcode.HALT: 19,

        # Branches
        (Opcode.BRANCH, 0b100): 20,  # blt
        (Opcode.BRANCH, 0b110): 23,  # bltu
        (Opcode.BRANCH, 0b101): 25,  # bge
        (Opcode.BRANCH, 0b000): 27,  # beq
        (Opcode.BRANCH, 0b001): 29,  # bne

        # Loads and stores
        (Opcode.STORE, 0b010): 31,  # sw
        (Opcode.STORE, 0b000): 33,  # sb
        (Opcode.LOAD, 0b010): 35,   # lw
        (Opcode.LOAD, 0b000): 37,   # lb
    }

    def __init__(self, program, data_path : DataPath, microcode):
        self.program = program
        self.program_counter = 0

        self.data_path = data_path
        self.microcode = microcode

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
                lambda: self.data_path.reg2_sel(self.current_instr["rs2"]),
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
                    lambda: self.data_path.data_write(4, "reg2"), 4
                ))
            elif t == MEM.WRITE_B:
                signals.append((
                    lambda: self.data_path.data_write(1, "reg2"), 4
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
                signals.append((lambda: self.data_path.latch_pc("next"), 6))
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
            self.micro_pc = decoded["next"]

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
        state_repr = "TICK: {:3} PC: {:3}/{} ADDR: {:3} MEM_OUT: {}".format(
            self._tick,
            self.program_counter,
            self.micro_pc,
            self.data_path.ar,
            self.data_path.data_memory[self.data_path.ar],
        )

        instr = self.program[self.program_counter]
        opcode = instr["opcode"]
        instr_repr = str(opcode)

        if "arg" in instr:
            instr_repr += " {}".format(instr["arg"])

        instr_hex = f"{opcode_to_binary[opcode] << 28 | (instr.get('arg', 0) & 0x0FFFFFFF):08X}"

        return "{} \t{} [{}]".format(state_repr, instr_repr, instr_hex)