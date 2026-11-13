from isa import Opcode, binary_to_opcode

class DataPath:
    def __init__(self, code, data_memory_size, data_mem, input_buffer):
        assert data_memory_size > 0, "Data_memory size should be non-zero"

        self.code_memory = code

        self.data_memory_size = data_memory_size

        assert len(data_mem) <= data_memory_size

        self.data_memory = bytearray(data_mem)
        self.data_memory.extend(
            b"\x00" * (data_memory_size - len(data_mem))
        )

        self.regs = [0] * 32

        self.vector_regs = [[0, 0, 0, 0] for _ in range(8)]

        self.pc = 0
        self.ar = 0
        self.vl = 4

        self.reg1 = 0
        self.reg2 = 0

        self.vreg1 = (0, 0, 0, 0)
        self.vreg2 = (0, 0, 0, 0)

        self.alu_left = 0
        self.alu_right = 0
        self.alu_result = 0

        self.valu_result = (0, 0, 0, 0)

        self.input_buffer = input_buffer
        self.input_data = 0
        self.output_buffer = []

        self.instruction = 0
        self.rd = 0
        self.rs1 = 0
        self.rs2 = 0

    def latch_pc(self, pc_sel):
        if pc_sel == "next_pc":
            self.pc = self.pc + 4
        elif pc_sel == "alu":
            self.pc = self.alu_result
        else:
            raise ValueError("Incorrect pc_sel: {}".format(pc_sel))

    def instruction_read(self):
        instruction_bytes = self.code_memory[self.pc:self.pc + 4]
        self.instruction = int.from_bytes(instruction_bytes, byteorder="big")

        self.rd = (self.instruction >> 7) & 0x1F
        self.rs1 = (self.instruction >> 15) & 0x1F
        self.rs2 = (self.instruction >> 20) & 0x1F
        
        return self.instruction

    def latch_ar(self, ar_sel):
        if ar_sel == "next_ar":
            self.ar = self.ar + 4
        elif ar_sel == "alu":
            self.ar = self.alu_result
        else:
            raise ValueError("Incorrect pc_sel: {}".format(ar_sel))

    def reg_write(self, reg_write_sel):
        if self.rd == 0:
            return

        if reg_write_sel == "alu":
            value = self.alu_result

        elif reg_write_sel == "mem_w":
            value = self.data_read(4)

        elif reg_write_sel == "mem_b":
            value = self.data_read(1)

        elif reg_write_sel == "next_pc":
            value = self.pc

        elif reg_write_sel == "in":
            value = self.input_data
        else:
            raise ValueError(f"Unknown register write source: {reg_write_sel}")

        self.regs[self.rd] = value

    def left_alu_sel(self, left_alu_sel):
        self.reg1 = self.regs[self.rs1]

        if left_alu_sel == "zero":
            self.alu_left = 0

        elif left_alu_sel == "reg1":
            self.alu_left = self.reg1

        elif left_alu_sel == "pc":
            self.alu_left = self.pc

        else:
            raise ValueError(
                "Incorrect left_alu_sel: {}".format(left_alu_sel)
            )

    def right_alu_sel(self, right_alu_sel):
        self.reg2 = self.regs[self.rs2]

        if right_alu_sel == "reg2":
            self.alu_right = self.reg2

        elif right_alu_sel == "imm":
            self.alu_right = self.generate_immediate(self.instruction)

        else:
            raise ValueError(
                "Incorrect right_alu_sel: {}".format(right_alu_sel)
            )

    def alu(self, alu_op):
        a = self.alu_left
        b = self.alu_right

        if alu_op == "add":
            result = a + b

        elif alu_op == "sub":
            result = a - b

        elif alu_op == "mul":
            result = a * b

        elif alu_op == "mulh":
            result = (self.signed_value(a) * self.signed_value(b)) >> 32

        elif alu_op == "div":
            a = self.signed_value(a)
            b = self.signed_value(b)

            if b == 0:
                raise ZeroDivisionError("Division by zero")

            result = abs(a) // abs(b)
            if (a < 0) != (b < 0):
                result = -result

        elif alu_op == "rem":
            a = self.signed_value(a)
            b = self.signed_value(b)

            if b == 0:
                raise ZeroDivisionError("Division by zero")

            quotient = abs(a) // abs(b)
            if (a < 0) != (b < 0):
                quotient = -quotient

            result = a - quotient * b

        elif alu_op == "and":
            result = a & b

        elif alu_op == "or":
            result = a | b

        elif alu_op == "xor":
            result = a ^ b

        elif alu_op == "sll":
            result = a << (b & 0x1F)

        elif alu_op == "srl":
            result = (a & 0xFFFFFFFF) >> (b & 0x1F)

        elif alu_op == "sra":
            result = self.signed_value(a) >> (b & 0x1F)

        elif alu_op == "slt":
            result = int(self.signed_value(a) < self.signed_value(b))

        elif alu_op in ("sltu", "sltiu"):
            result = int((a & 0xFFFFFFFF) < (b & 0xFFFFFFFF))

        else:
            raise ValueError("Incorrect alu_op: {}".format(alu_op))

        self.alu_result = result & 0xFFFFFFFF
        return self.alu_result

    def data_read(self, data_size):
        assert data_size in (1, 4)

        address = self.ar
        data = int.from_bytes(
            self.data_memory[address:address + data_size],
            byteorder="big",
            signed=(data_size == 1)
        )

        return data

    def data_write(self, mem_write_sel, lane = 0):
        self.reg2 = self.regs[self.rs2]
        self.vreg2 = self.vector_regs[self.rs2]

        if mem_write_sel == "write_b":
            value = (self.regs[self.rs2] & 0xFF).to_bytes(1, "big")
        elif mem_write_sel == "write_w":
            value = (self.regs[self.rs2] & 0xFFFFFFFF).to_bytes(4, "big")
        elif mem_write_sel == "write_vector":
            value = (
                self.vreg2[lane] & 0xFFFFFFFF
            ).to_bytes(4, "big")

        else:
            raise ValueError(
                f"Unknown memory write source: {mem_write_sel}"
            )

        self.data_memory[self.ar:self.ar + len(value)] = value

    def input_read(self):
        if not self.input_buffer:
            raise EOFError("Input buffer is empty")

        value = self.input_buffer.pop(0)

        if isinstance(value, str):
            value = ord(value)

        self.input_data = value

    def latch_out(self):
        self.output_buffer.append(chr(self.reg1))

    def latch_vl(self):
        assert 1 <= self.alu_result <= 4, "Vector Length must be [1;4]"
        self.vl = self.alu_result

    def vreg_write(self, reg_write_sel, lane_number):
        if self.rd == 0:
            return

        if reg_write_sel == "valu":
            self.vector_regs[self.rd] = list(self.valu_result)

        elif reg_write_sel == "mem":
            value = self.data_read(4)
            self.vector_regs[self.rd][lane_number] = value
        else:
            raise ValueError(f"Unknown register write source: {reg_write_sel}")

    def vector_alu(self, alu_op):
        a = self.vector_regs[self.rs1]
        b = self.vector_regs[self.rs2]

        if alu_op == "add":
            result = tuple(x + y for x, y in zip(a, b))

        elif alu_op == "sub":
            result = tuple(x-y for x, y in zip(a, b))

        elif alu_op == "mul":
            result = tuple(x*y for x, y in zip(a, b))

        elif alu_op == "div":
            if any(y == 0 for y in b):
                raise ZeroDivisionError("Division by zero")
            result = tuple(
                (abs(x) // abs(y)) * (-1 if (x < 0) != (y < 0) else 1)
                for x, y in zip(
                    map(self.signed_value, a),
                    map(self.signed_value, b)
                )
            )

        elif alu_op == "slt":
            result = tuple(
                int(self.signed_value(x) < self.signed_value(y))
                for x, y in zip(a, b)
            )

        else:
            raise ValueError("Incorrect alu_op: {}".format(alu_op))

        self.valu_result = tuple(x & 0xFFFFFFFF for x in result)
        return self.valu_result

    def signed_value(self, value):
        value &= 0xFFFFFFFF
        if value >= 0x80000000:
            return value - 0x100000000
        return value

    def print_data_memory(self, filename="out/data_memory.txt"):
        with open(filename, "w") as file:
            for i in range(0, len(self.data_memory), 4):
                chunk = self.data_memory[i:i + 4]
                line = " ".join(f"{byte:02X}" for byte in chunk)
                file.write(line + "\n")
                
                
    def generate_immediate(self,instr):
        opcode = binary_to_opcode[instr & 0x1F]

        if opcode in (Opcode.OPIMM, Opcode.LOAD, Opcode.JALR):
            instr_type = "I"
        elif opcode == Opcode.STORE:
            instr_type = "S"
        elif opcode == Opcode.BRANCH:
            instr_type = "B"
        elif opcode == Opcode.LUI:
            instr_type = "U"
        elif opcode == Opcode.JAL:
            instr_type = "J"
        else:
            raise ValueError(f"Instruction has no immediate: {instr:#010x}")

        if instr_type == "I":
            imm = (instr >> 20) & 0xFFF
            return self.sign_extend(imm, 12)

        elif instr_type == "S":
            imm = (((instr >> 25) & 0x7F) << 5) | ((instr >> 7) & 0x1F)
            return self.sign_extend(imm, 12)

        elif instr_type == "B":
            imm = (
                ((instr >> 31) & 1) << 12 |
                ((instr >> 25) & 0x3F) << 5 |
                ((instr >> 8) & 0xF) << 1 |
                ((instr >> 7) & 1) << 11
            )
            return self.sign_extend(imm, 13)

        elif instr_type == "U":
            return self.sign_extend(instr & 0xFFFFF000, 32)

        elif instr_type == "J":
            imm = (
                ((instr >> 31) & 1) << 20 |
                ((instr >> 21) & 0x3FF) << 1 |
                ((instr >> 20) & 1) << 11 |
                ((instr >> 12) & 0xFF) << 12
            )
            return self.sign_extend(imm, 21)

    def sign_extend(self, value, bits):
        sign_bit = 1 << (bits - 1)
        return (value ^ sign_bit) - sign_bit
