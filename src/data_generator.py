class DataGenerator:
    def __init__(self):
        self.DIRECTIVES = {".byte": 1, ".word": 4, ".long": 8}
        self.data = bytearray()
        self.labels = {}

    def add_label(self, name):
        self.labels[name] = len(self.data)

    def add_value(self, directive, value):
        size = self.DIRECTIVES[directive]
        number = int(value.strip(), 0)

        number &= (1 << (size * 8)) - 1

        self.data.extend(number.to_bytes(size, byteorder="big"))

    def generate(self, code):
        self.data = bytearray()
        self.labels = {}

        for line_number, line in enumerate(code.splitlines()):
            line = line.strip()

            if line == ".data":
                continue

            if line == ".text":
                break

            if ":" in line:
                label, line = line.split(":", 1)
                self.add_label(label.strip())
                line = line.strip()

            parts = line.split(maxsplit=1)
            directive = parts[0]

            values = parts[1].split(",")

            for value in values:
                self.add_value(directive, value)

        return bytes(self.data)

    def to_hex(self, binary_data):
        result = []

        for i in range(0, len(binary_data), 4):
            chunk = binary_data[i : i + 4]

            address = i
            hex_value = chunk.hex().upper()

            result.append(f"{address:08X} - {hex_value}")

        return "\n".join(result)
