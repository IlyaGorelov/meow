from data_generator import from_bytes

class DataPath:
    def __init__(self, data_memory_size, data, input_buffer):
        assert data_memory_size > 0, "Data_memory size should be non-zero"
        
        self.data_memory_size = data_memory_size

        self.regs = [0] * 32

        self.pc = 0
        self.ar = 0

        self.reg1 = 0
        self.reg2 = 0

        self.alu_left = 0
        self.alu_right = 0
        self.alu_result = 0

        initiated_mem = bytearray(from_bytes(data))

        assert len(initiated_mem) <= data_memory_size

        self.data_memory = initiated_mem
        self.data_memory.extend(
            b"\x00" * (data_memory_size - len(initiated_mem))
        )

        self.input_buffer = input_buffer
        self.input_data = 0
        self.output_buffer = []

    
    def latch_pc(self, pc_sel):
        if pc_sel == "next":
            self.pc = (self.pc + 4) & 0xFFFFFFFF
        elif pc_sel == "alu":
            self.pc = self.alu_result & 0xFFFFFFFF
        else:
            raise ValueError("Incorrect pc_sel: {}".format(pc_sel))

    def latch_ar(self):
        self.ar = self.alu_result

    def reg1_sel(self, reg1_sel):
        self.reg1 = self.regs[reg1_sel]

    def reg2_sel(self, reg2_sel):
        self.reg2 = self.regs[reg2_sel]

    def reg_write(self, reg_write_sel, rd):
        if rd == 0:
            return

        if reg_write_sel == "alu":
            value = self.alu_result

        elif reg_write_sel == "memory":
            value = self.data_read(4)

        elif reg_write_sel == "memory_byte":
            value = self.data_read(1)

        elif reg_write_sel == "pc":
            value = self.pc + 4

        elif reg_write_sel == "input":
            value = self.input_data
        else:
            raise ValueError(f"Unknown register write source: {reg_write_sel}")

        self.regs[rd] = value

    def left_alu_sel(self, left_alu_sel):
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

    def right_alu_sel(self, right_alu_sel, imm=None):
        if right_alu_sel == "reg2":
            self.alu_right = self.reg2

        elif right_alu_sel == "imm":
            if imm is None:
                raise ValueError("Immediate value is required")

            self.alu_right = imm

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

    def data_write(self, data_size, data_write_sel):
        assert data_size in (1, 4)

        if data_write_sel == "reg2":
            value = self.reg2

        elif data_write_sel == "alu":
            value = self.alu_result

        else:
            raise ValueError(
                "Incorrect data_write_sel: {}".format(data_write_sel)
            )

        value &= (1 << (data_size * 8)) - 1

        address = self.ar

        self.data_memory[address:address + data_size] = (
            value.to_bytes(data_size, byteorder="big")
        )

    def input_read(self):
        if not self.input_buffer:
            raise EOFError("Input buffer is empty")

        value = self.input_buffer.pop(0)

        if isinstance(value, str):
            value = ord(value)

        self.input_data = value

    def latch_out(self):
        self.output_buffer.append(self.reg1)

    def signed_value(self, value):
        value &= 0xFFFFFFFF
        if value >= 0x80000000:
            return value - 0x100000000
        return value
