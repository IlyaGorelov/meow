class DataGenerator:
    DIRECTIVES = {
        ".byte": 1,
        ".word": 4,
        ".long": 8
    }

    def __init__(self):
        self.data = bytearray()
        self.labels = {}

    def add_label(self, name):
        self.labels[name] = len(self.data)

    def add_value(self, directive, value):
        size = self.DIRECTIVES[directive]
        number = int(value.strip(), 0)

        number &= (1 << (size * 8)) - 1

        self.data.extend(
            number.to_bytes(size, byteorder="big")
        )

    def generate(self, code):
        self.data = bytearray()
        self.labels = {}

        in_data = False

        for line_number, line in enumerate(code.splitlines(), 1):
            line = line.strip()

            if not line:
                continue

            if line == ".data":
                in_data = True
                continue

            if line == ".text":
                in_data = False
                continue

            if not in_data:
                continue

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

    def get_label_address(self, label, base_address=0):
        return base_address + self.labels[label]