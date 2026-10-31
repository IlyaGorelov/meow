class CodeGeneratorError(Exception):
    pass

class CodeGenerator:
    REGISTER_ALIASES = {
        0: "zero",
        1: "ra",
        2: "sp",
        3: "gb",
        4: "tp",
        5: "t0",
        6: "t1",
        7: "t2",
        8: "s0",
        9: "s1",
        10: "a0",
        11: "a1",
        12: "a2",
        13: "a3",
        14: "a4",
        15: "a5",
        16: "a6",
        17: "a7",
        18: "s2",
        19: "s3",
        20: "s4",
        21: "s5",
        22: "s6",
        23: "s7",
        24: "s8",
        25: "s9",
        26: "s10",
        27: "s11",
        28: "t3",
        29: "t4",
        30: "t5",
        31: "t6",
    }

    def __init__(self):
        self.code = []
        self.data = []

        self.globals = {}

        self.functions = {}

        self.scopes = []

        self.current_function = None
        self.current_function_end = None
        self.current_frame_size = 0

        self.temp_stack_depth = 0

        self.label_counter = 0
        self.string_counter = 0

        self.loop_stack = []

    def error(self, message, node=None):
        line = node.get("line")

        if line is not None:
            raise CodeGeneratorError(f"Line {line}: {message}")

        raise CodeGeneratorError(message)

    def append(self, instruction):
        self.code.append(f"     {instruction}")

    def append_label(self, label):
        self.code.append(f"{label}:")

    def label_with_prefix(self, prefix="L"):
        label = f".{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label

    def push(self, register):
        self.append("addi sp, sp, -4")
        self.append(f"sw {register}, 0(sp)")
        self.temp_stack_depth += 4

    def pop(self, register):
        if self.temp_stack_depth < 4:
            self.error("stack underflow")

        self.append(f"lw {register}, 0(sp)")
        self.append("addi sp, sp, 4")
        self.temp_stack_depth -= 4

    def load_immediate(self, register, value):
        value &= 0xFFFFFFFF

        if value >= 0x80000000:
            value -= 0x100000000

        if -2048 <= value <= 2047:
            self.append(f"addi {register}, zero, {value}")
            return

        upper = (value + 0x800) >> 12
        lower = value - (upper << 12)

        upper &= 0xFFFFF
        if upper >= 0x80000:
            upper -= 0x100000

        self.append(f"lui {register}, {upper}")

        if lower != 0:
            self.append(f"addi {register}, {register}, {lower}")

    def base_type(self, type_name):
        if type_name.endswith("[]"):
            return type_name[:-2]
        return type_name

    def is_array_type(self, type_name):
        return type_name.endswith("[]")

    def is_pointer_type(self, type_name):
        return type_name == "string" or self.is_array_type(type_name)

    def type_size(self, type_name):
        if self.is_pointer_type(type_name):
            return 4

        sizes = {"byte": 1, "bool": 1, "int": 4, "long": 8}

        return sizes[type_name]

    def element_size(self, type_name):
        if type_name == "string":
            return 1
        if self.is_array_type(type_name):
            return self.type_size(self.base_type(type_name))

    def type_alignment(self, type_name):
        return min(self.type_size(type_name), 8)

    def split_long(self, value):
        value &= 0xFFFFFFFFFFFFFFFF

        high = (value >> 32) & 0xFFFFFFFF
        low = value & 0xFFFFFFFF

        if high >= 0x80000000:
            high -= 0x100000000

        if low >= 0x80000000:
            low -= 0x100000000

        return high, low

    def load_long_immediate(self, high_register, low_register, value):
        high, low = self.split_long(value)

        self.load_immediate(high_register, high)
        self.load_immediate(low_register, low)

    def load_long(self, offset, high_register="t0", low_register="t1"):
        self.append(f"lw {high_register}, {offset}(s0)")
        self.append(f"lw {low_register}, {offset + 4}(s0)")

    def store_long(self, high_register, low_register, offset):
        self.append(f"sw {high_register}, {offset}(s0)")
        self.append(f"sw {low_register}, {offset + 4}(s0)")

    def load_long_global(self, label):
        self.load_global_address("t2", label)
        self.append("lw t0, 0(t2)")
        self.append("lw t1, 4(t2)")

    def store_long_global(self, label, high_register="t0", low_register="t1"):
        self.load_global_address("t2", label)
        self.append(f"sw {high_register}, 0(t2)")
        self.append(f"sw {low_register}, 4(t2)")

    def decode_char(self,value):
        if len(value) == 1:
            return ord(value)

        if len(value) >= 2 and value[0] in ("'", '"'):
            quote = value[0]

            if value[-1] == quote:
                inner = value[1:-1]

                escapes = {
                    r"\n": "\n",
                    r"\r": "\r",
                    r"\t": "\t",
                    r"\0": "\0",
                    r"\\": "\\",
                    r"\'": "'",
                    r'\"': '"',
                }

                if inner in escapes:
                    return ord(escapes[inner])

                if len(inner) == 1:
                    return ord(inner)

        escapes = {
            r"\n": "\n",
            r"\r": "\r",
            r"\t": "\t",
            r"\0": "\0",
            r"\\": "\\",
            r"\'": "'",
            r'\"': '"',
        }

        if value in escapes:
            return ord(escapes[value])

    def argument_slot_size(self, type_name):
        return max(4, self.type_size(type_name))

    def argument_word_count(self, type_name):
        return 2 if self.type_size(type_name) == 8 else 1

    def calculate_argument_layout(self, type_names):
        layout = []
        register_index = 0
        stack_offset = 0
        stack_started = False

        for type_name in type_names:
            size = self.type_size(type_name)
            slot_size = self.argument_slot_size(type_name)
            word_count = self.argument_word_count(type_name)

            if (
                not stack_started
                and register_index + word_count <= 8
            ):
                item = {
                    "type": type_name,
                    "size": size,
                    "slot_size": slot_size,
                    "location": "register",
                    "register_index": register_index,
                    "stack_offset": None,
                }

                register_index += word_count

            else:
                stack_started = True

                item = {
                    "type": type_name,
                    "size": size,
                    "slot_size": slot_size,
                    "location": "stack",
                    "register_index": None,
                    "stack_offset": stack_offset,
                }

                stack_offset += slot_size

            layout.append(item)

        return layout

    def generate(self, ast):
        self.code = []
        self.data = []
        self.globals = {}
        self.functions = {}
        self.scopes = []
        self.current_function = None
        self.current_function_end = None
        self.current_frame_size = 0
        self.temp_stack_depth = 0
        self.label_counter = 0
        self.string_counter = 0
        self.loop_stack = []

        body = ast.get("body", [])

        for node in body:
            if node.get("type") == "function":
                name = node["name"]
                self.functions[name] = node

        self.append_label("_start")
        self.append("lui s1, 1") # init heap pointer

        for node in body:
            if node.get("type") == "function":
                continue

            self.generate_statement(node)

        self.append("halt")

        for name, function_node in self.functions.items():
            self.generate_function(function_node)

        output = []

        if self.data:
            output.append(".data")
            output.extend(self.data)

        output.append(".text")
        output.extend(self.code)

        return "\n".join(output) + "\n"

    def collect_local_declarations(self, body):
        declarations = []

        def visit_statement(node):
            node_type = node.get("type")

            if node_type in ("var_declaration", "const_declaration"):
                declarations.append(node)
                return

            if node_type == "if":
                for statement in node.get("body", []):
                    visit_statement(statement)

                for statement in node.get("else_body") or []:
                    visit_statement(statement)

                return

            if node_type == "while":
                for statement in node.get("body", []):
                    visit_statement(statement)

                return

        for statement in body:
            visit_statement(statement)

        return declarations

    def prepare_function_frame(self, function_node):
        slots = self.collect_local_declarations(
            function_node.get("body", [])
        )

        offset = 0

        for node in slots:
            alignment = self.type_alignment(node["var_type"])
            offset = (offset + alignment - 1) & ~(alignment - 1)
            node["_slot_offset"] = offset
            offset += self.type_size(node["var_type"])

        frame_size = (offset + 8 + 7) & ~7

        self.current_frame_size = frame_size
        return slots, frame_size
    
    def generate_function(self, node):
        name = node["name"]
        params = node.get("params", [])
        body = node.get("body", [])

        previous_function = self.current_function
        previous_end = self.current_function_end
        previous_frame_size = self.current_frame_size

        _, frame_size = self.prepare_function_frame(node)
        previous_scopes = self.scopes
        previous_temp_depth = self.temp_stack_depth

        self.current_function = name
        self.current_function_end = self.label_with_prefix(f"{name}_end")
        self.current_frame_size = frame_size
        self.scopes = [{}]
        self.temp_stack_depth = 0

        self.append_label(f"fn_{name}")

        self.append(f"addi sp, sp, -{frame_size}")
        self.append(f"sw ra, {frame_size - 4}(sp)")
        self.append(f"sw s0, {frame_size - 8}(sp)")
        self.append("mv s0, sp")

        param_types = [
            parameter["param_type"]
            for parameter in params
        ]

        layout = self.calculate_argument_layout(param_types)

        for parameter, item in zip(params, layout):
            param_name = parameter["name"]
            param_type = parameter["param_type"]

            if item["location"] == "register":
                self.scopes[-1][param_name] = {
                    "type": param_type,
                    "storage": "argument_register",
                    "register_index": item["register_index"],
                }
            else:
                self.scopes[-1][param_name] = {
                    "type": param_type,
                    "storage": "argument_stack",
                    "offset": frame_size + item["stack_offset"],
                }

        self.generate_scoped_block(body)

        self.append_label(self.current_function_end)

        self.append(f"lw ra, {frame_size - 4}(s0)")
        self.append(f"lw t0, {frame_size - 8}(s0)")
        self.append(f"addi sp, s0, {frame_size}")
        self.append("mv s0, t0")
        self.append("jalr zero, 0(ra)")

        self.current_function = previous_function
        self.current_function_end = previous_end
        self.current_frame_size = previous_frame_size
        self.scopes = previous_scopes
        self.temp_stack_depth = previous_temp_depth

    def store_register_to_local(self, register, offset, type_name):
        base = self.base_type(type_name)

        if self.is_pointer_type(type_name) or base == "int":
            self.append(f"sw {register}, {offset}(s0)")
        else:
            self.append(f"sb {register}, {offset}(s0)")
    
    def lookup_variable(self, name, node=None):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]

        if name in self.globals:
            return self.globals[name]

    def load_global_address(self, register, label):
        self.append(f"lui {register}, %hi({label})")
        self.append(f"addi {register}, {register}, %lo({label})")

    def load_variable(self, name, node=None):
        info = self.lookup_variable(name, node)
        base = self.base_type(info["type"])

        if info["storage"] == "argument_register":
            register_index = info["register_index"]

            if base == "long":
                self.append(f"mv t0, a{register_index}")
                self.append(f"mv t1, a{register_index + 1}")
            else:
                self.append(f"mv t0, a{register_index}")

            return

        instruction = "lb" if base in ("byte", "bool") and not self.is_pointer_type(info["type"]) else "lw"

        if info["storage"] == "global":
            self.load_global_address("t2", info["label"])
            if base == "long":
                self.append("lw t0, 0(t2)")
                self.append("lw t1, 4(t2)")
            else:
                self.append(f"{instruction} t0, 0(t2)")
        elif base == "long":
            self.append(f"lw t0, {info['offset']}(s0)")
            self.append(f"lw t1, {info['offset'] + 4}(s0)")
        else:
            self.append(f"{instruction} t0, {info['offset']}(s0)")
    
    def store_variable(self, name, register, node=None):
        info = self.lookup_variable(name, node)
        base = self.base_type(info["type"])

        if info["storage"] == "argument_register":
            register_index = info["register_index"]
            self.append(f"mv a{register_index}, {register}")
            return

        instruction = "sb" if base in ("byte", "bool") and not self.is_pointer_type(info["type"]) else "sw"

        if info["storage"] == "global":
            self.load_global_address("t2", info["label"])
            self.append(f"{instruction} {register}, 0(t2)")
        else:
            self.append(f"{instruction} {register}, {info['offset']}(s0)")

    def generate_statement(self, node):
        node_type = node.get("type")

        if node_type in ("var_declaration", "const_declaration"):
            self.generate_declaration(node)

        elif node_type == "assignment":
            self.generate_assignment(node)

        elif node_type == "if":
            self.generate_if(node)

        elif node_type == "while":
            self.generate_while(node)

        elif node_type == "continue":
            self.generate_continue(node)

        elif node_type == "break":
            self.generate_break(node)

        elif node_type == "return":
            self.generate_return(node)

        elif node_type == "call_statement":
            self.generate_expression(node["call"])

        elif node_type == "output":
            self.generate_output(node["value"], node)

        elif node_type == "comment":
            pass

        elif node_type == "function":
            pass

        else:
            self.error(
                f"Unsupported statement type: {node_type}",
                node,
            )

    def generate_declaration(self, node):
        name = node["name"]
        type_name = node["var_type"]
        value = node.get("value")

        if self.current_function is None:
            label = f"global_{name}"

            self.globals[name] = {
                "type": type_name,
                "label": label,
                "storage": "global",
            }

            if type_name == "long":
                self.data.append(f"{label}: .long 0")
            elif type_name in ("byte", "bool"):
                self.data.append(f"{label}: .byte 0")
            elif type_name in ("int", "string") or self.is_array_type(type_name):
                self.data.append(f"{label}: .word 0")
            else:
                self.error(f"Unsupported data type: {type_name}", node)

            if value is not None:
                self.generate_expression(value)
                if type_name == "long":
                    self.store_long_global(label)
                else:
                    self.store_variable(name, "t0", node)

            return

        offset = node["_slot_offset"]

        self.scopes[-1][name] = {
            "type": type_name,
            "offset": offset,
            "storage": "local",
        }

        if value is not None:
            self.generate_expression(value)
            if self.base_type(type_name) == "long":
                self.store_long("t0", "t1", offset)
            else:
                self.store_register_to_local("t0", offset, type_name)

    def generate_assignment(self, node):
        target = node["target"]
        value = node["value"]

        if target["type"] == "variable":
            name = target["name"]
            info = self.lookup_variable(name, target)

            self.generate_expression(value)

            if self.base_type(info["type"]) == "long":
                if info["storage"] == "global":
                    self.store_long_global(info["label"])
                elif info["storage"] == "argument_register":
                    index = info["register_index"]
                    self.append(f"mv a{index}, t0")
                    self.append(f"mv a{index + 1}, t1")
                else:
                    self.append(f"sw t0, {info['offset']}(s0)")
                    self.append(f"sw t1, {info['offset'] + 4}(s0)")
            else:
                self.store_variable(name, "t0", target)

            return

        if target["type"] == "index":
            self.generate_array_address(target)
            self.push("t2")

            self.generate_expression(value)

            self.pop("t2")

            element_type = self.expression_type(target)
            base = self.base_type(element_type)

            if base == "long":
                self.append("sw t0, 0(t2)")
                self.append("sw t1, 4(t2)")
            elif base in ("byte", "bool"):
                self.append("sb t0, 0(t2)")
            else:
                self.append("sw t0, 0(t2)")

            return

    def generate_if(self, node):
        else_label = self.label_with_prefix("else")
        end_label = self.label_with_prefix("endif")

        self.generate_expression(node["condition"])
        self.append(f"beq t0, zero, {else_label}")

        self.generate_scoped_block(node.get("body", []))
        self.append(f"j {end_label}")

        self.append_label(else_label)

        else_body = node.get("else_body")
        if else_body is not None:
            self.generate_scoped_block(else_body)

        self.append_label(end_label)

    def generate_while(self, node):
        start_label = self.label_with_prefix("while_start")
        end_label = self.label_with_prefix("while_end")

        self.append(f"{start_label}:")

        self.generate_expression(node["condition"])
        self.append(f"beq t0, zero, {end_label}")

        self.loop_stack.append((start_label, end_label))
        try:
            self.generate_scoped_block(node["body"])
        finally:
            self.loop_stack.pop()

        self.append(f"j {start_label}")
        self.append(f"{end_label}:")
    
    def generate_scoped_block(self, body):
        self.scopes.append({})
        try:
            for statement in body:
                self.generate_statement(statement)
        finally:
            self.scopes.pop()

    def generate_continue(self, node):
        if not self.loop_stack:
            self.error("'continue' used outside a loop", node)

        start_label, _ = self.loop_stack[-1]
        self.append(f"j {start_label}")

    def generate_break(self, node):
        if not self.loop_stack:
            self.error("'break' used outside a loop", node)

        _, end_label = self.loop_stack[-1]
        self.append(f"j {end_label}")

    def generate_return(self, node):
        if self.current_function is None:
            self.error("'return' used outside a function", node)

        value = node.get("value")

        if value is not None:
            self.generate_expression(value)

            return_type = self.functions[self.current_function]["return_type"]

            if self.base_type(return_type) == "long":
                self.append("mv a0, t0")
                self.append("mv a1, t1")
            else:
                self.append("mv a0, t0")

        self.append(f"j {self.current_function_end}")

    def generate_output(self, value, node=None):
        value_type = self.expression_type(value)
        if value_type != "byte":
            self.error("meow() expects a byte value", node or value)
        self.generate_expression(value)
        self.append("out 0, t0")

    def generate_expression(self, node):
        node_type = node.get("type")

        if node_type == "int":
            self.load_immediate("t0", int(node["value"]))

        elif node_type == "long":
            self.load_long_immediate("t0", "t1", int(node["value"]))

        elif node_type == "byte":
            try:
                value = self.decode_char(node["value"])
            except (ValueError, TypeError) as exc:
                self.error(str(exc), node)

            self.load_immediate("t0", value)

        elif node_type == "bool":
            value = node["value"]

            if isinstance(value, str):
                value = value.lower() == "true"

            self.load_immediate("t0", int(bool(value)))

        elif node_type == "string":
            self.generate_string(node["value"])

        elif node_type == "variable":
            self.load_variable(node["name"], node)

        elif node_type == "index":
            self.generate_array_access(node)

        elif node_type == "binary":
            self.generate_binary(node)

        elif node_type == "unary":
            self.generate_unary(node)

        elif node_type == "function_call":
            self.generate_function_call(node)

        elif node_type == "input":
            self.append("in t0, 0")

        elif node_type == "array_creation":
            self.generate_array_creation(node)

        else:
            self.error(
                f"Unsupported expression type: {node_type}",
                node,
            )
    
    def generate_string(self, value):
        label = f"string_{self.string_counter}"
        self.string_counter += 1

        string_bytes = list(value.encode("utf-8"))
        string_bytes.append(0)

        self.data.append(
            f"{label}: .byte " + ", ".join(map(str, string_bytes))
        )

        self.load_global_address("t0", label)

    def generate_unary(self, node):
        operator = node["operator"]
        operand_type = self.expression_type(node["operand"])

        self.generate_expression(node["operand"])

        if operator != "-":
            self.error(f"Unsupported unary operator: {operator}", node)

        if self.base_type(operand_type) == "long":
            self.append("sub t1, zero, t1")
            self.append("sltu t2, zero, t1")
            self.append("sub t0, zero, t0")
            self.append("sub t0, t0, t2")
        else:
            self.append("sub t0, zero, t0")

    def generate_binary(self, node):
        operator = node["operator"]

        left_type = self.expression_type(node["left"])
        right_type = self.expression_type(node["right"])

        is_long = (
            self.base_type(left_type) == "long"
            or self.base_type(right_type) == "long"
        )

        if is_long:
            self.generate_long_binary(node)
            return

        if operator in ("&&", "||"):
            true_or_false = self.label_with_prefix("logic_result")
            end_label = self.label_with_prefix("logic_end")
            self.generate_expression(node["left"])

            if operator == "&&":
                self.append(f"beq t0, zero, {true_or_false}")
                result_when_skipped = 0
            else:
                self.append(f"bne t0, zero, {true_or_false}")
                result_when_skipped = 1

            self.generate_expression(node["right"])
            self.append("sltu t0, zero, t0")
            self.append(f"j {end_label}")
            self.append_label(true_or_false)
            self.load_immediate("t0", result_when_skipped)
            self.append_label(end_label)
            return

        self.generate_expression(node["left"])
        self.push("t0")

        self.generate_expression(node["right"])
        self.append("mv t1, t0")

        self.pop("t0")

        operations = {
            "+": "add",
            "-": "sub",
            "*": "mul",
            "/": "div",
            "%": "rem",
            "&": "and",
            "|": "or",
        }

        if operator in operations:
            self.append(f"{operations[operator]} t0, t0, t1")
            return

        if operator == "==":
            self.append("xor t0, t0, t1")
            self.append("sltiu t0, t0, 1")

        elif operator == "!=":
            self.append("xor t0, t0, t1")
            self.append("sltu t0, zero, t0")

        elif operator == "<":
            self.append("slt t0, t0, t1")

        elif operator == ">":
            self.append("slt t0, t1, t0")

        elif operator == "<=":
            self.append("slt t0, t1, t0")
            self.append("xori t0, t0, 1")

        elif operator == ">=":
            self.append("slt t0, t0, t1")
            self.append("xori t0, t0, 1")

        else:
            self.error(f"Unsupported binary operator: {operator}", node)


    def generate_long_binary(self, node):
        operator = node["operator"]

        self.generate_expression(node["left"])
        if self.base_type(self.expression_type(node["left"])) != "long":
            self.append("slt t1, t0, zero")
            self.append("sub t1, zero, t1")
        self.push("t0")
        self.push("t1")

        self.generate_expression(node["right"])
        if self.base_type(self.expression_type(node["right"])) != "long":
            self.append("slt t1, t0, zero")
            self.append("sub t1, zero, t1")

        self.append("mv t2, t0")
        self.append("mv t3, t1")

        self.pop("t1")
        self.pop("t0")

        if operator == "+":
            self.append("add t4, t1, t3")
            self.append("sltu t5, t4, t1")
            self.append("add t0, t0, t2")
            self.append("add t0, t0, t5")
            self.append("mv t1, t4")

        elif operator == "-":
            self.append("sltu t4, t1, t3")
            self.append("sub t1, t1, t3")
            self.append("sub t0, t0, t2")
            self.append("sub t0, t0, t4")

        elif operator in ("&", "|"):
            instruction = "and" if operator == "&" else "or"
            self.append(f"{instruction} t0, t0, t2")
            self.append(f"{instruction} t1, t1, t3")

        elif operator in ("&&", "||"):
            self.append("or t0, t0, t1")
            self.append("sltu t0, zero, t0")
            self.append("or t2, t2, t3")
            self.append("sltu t2, zero, t2")
            instruction = "and" if operator == "&&" else "or"
            self.append(f"{instruction} t0, t0, t2")

        elif operator == "==":
            self.append("xor t0, t0, t2")
            self.append("xor t1, t1, t3")
            self.append("or t0, t0, t1")
            self.append("sltiu t0, t0, 1")

        elif operator == "!=":
            self.append("xor t0, t0, t2")
            self.append("xor t1, t1, t3")
            self.append("or t0, t0, t1")
            self.append("sltu t0, zero, t0")

        elif operator in ("<", ">", "<=", ">="):
            true_label = self.label_with_prefix("long_true")
            end_label = self.label_with_prefix("long_compare_end")

            if operator in ("<", "<="):
                self.append(f"blt t0, t2, {true_label}")
                self.append(f"blt t2, t0, {end_label}")
                self.append(f"bltu t1, t3, {true_label}")

                if operator == "<=":
                    self.append(f"beq t1, t3, {true_label}")

            else:
                self.append(f"blt t2, t0, {true_label}")
                self.append(f"blt t0, t2, {end_label}")
                self.append(f"bltu t3, t1, {true_label}")

                if operator == ">=":
                    self.append(f"beq t1, t3, {true_label}")

            self.append("addi t0, zero, 0")
            self.append(f"j {end_label}")

            self.append_label(true_label)
            self.append("addi t0, zero, 1")

            self.append_label(end_label)

        else:
            self.error(
                f"Long operator '{operator}' is not implemented",
                node,
            )
    
    def generate_array_address(self, node):
        array_node = node["array"]
        index_node = node["index"]
        array_type = self.expression_type(array_node)

        if array_type != "string" and not self.is_array_type(array_type):
            self.error("Indexing a non-array expression", node)

        element_size = self.element_size(array_type)
        self.generate_expression(array_node)
        self.push("t0")
        self.generate_expression(index_node)

        if element_size != 1:
            self.load_immediate("t1", element_size)
            self.append("mul t0, t0, t1")

        self.append("mv t1, t0")
        self.pop("t2")
        self.append("add t2, t2, t1")

    def generate_array_access(self, node):
        array_type = self.expression_type(node["array"])
        if array_type == "string":
            element_type = "byte"
        elif self.is_array_type(array_type):
            element_type = self.base_type(array_type)
        else:
            self.error("Cannot index a non-array value", node)

        self.generate_array_address(node)
        if element_type == "long":
            self.append("lw t0, 0(t2)")
            self.append("lw t1, 4(t2)")
        elif element_type in ("byte", "bool"):
            self.append("lb t0, 0(t2)")
        else:
            self.append("lw t0, 0(t2)")

    def generate_array_creation(self, node):
        element_type = node["element_type"]
        size_node = node["size"]
        element_size = self.type_size(element_type)

        self.generate_expression(size_node)
        self.load_immediate("t1", element_size)
        self.append("mul t1, t0, t1")
        self.append("mv t0, s1")
        self.append("add s1, s1, t1")


    def generate_function_call(self, node):
        function_name = node["name"]
        args = node.get("args", [])

        if function_name not in self.functions:
            self.error(f"Unknown function '{function_name}'", node)

        function = self.functions[function_name]

        if len(args) != len(function.get("params", [])):
            self.error(
                f"Function '{function_name}' expects "
                f"{len(function.get('params', []))} arguments, "
                f"got {len(args)}",
                node,
            )

        arg_types = [
            self.expression_type(arg)
            for arg in args
        ]

        layout = self.calculate_argument_layout(arg_types)

        for register_index in range(8):
            self.push(f"a{register_index}")

        for index in range(len(args) - 1, -1, -1):
            arg = args[index]
            item = layout[index]
            base = self.base_type(item["type"])
            slot_size = item["slot_size"]

            self.generate_expression(arg)

            self.append(f"addi sp, sp, -{slot_size}")

            if base == "long":
                self.append("sw t0, 0(sp)")
                self.append("sw t1, 4(sp)")

            elif base in ("byte", "bool") and not self.is_pointer_type(item["type"]):
                self.append("sb t0, 0(sp)")

            elif base in ("int", "string") or self.is_array_type(item["type"]):
                self.append("sw t0, 0(sp)")

            else:
                self.error(
                    f"Unsupported argument type: {item['type']}",
                    node,
                )

        register_bytes = 0

        for item in layout:
            if item["location"] != "register":
                break

            base = self.base_type(item["type"])
            register_index = item["register_index"]
            offset = register_bytes

            if base == "long":
                self.append(f"lw a{register_index}, {offset}(sp)")
                self.append(f"lw a{register_index + 1}, {offset + 4}(sp)")

            elif base in ("byte", "bool") and not self.is_pointer_type(item["type"]):
                self.append(f"lb a{register_index}, {offset}(sp)")

            elif base in ("int", "string") or self.is_array_type(item["type"]):
                self.append(f"lw a{register_index}, {offset}(sp)")

            register_bytes += item["slot_size"]

        if register_bytes:
            self.append(f"addi sp, sp, {register_bytes}")

        self.append(f"jal ra, fn_{function_name}")

        stack_bytes = sum(
            item["slot_size"]
            for item in layout
            if item["location"] == "stack"
        )

        if stack_bytes:
            self.append(f"addi sp, sp, {stack_bytes}")

        return_type = function["return_type"]

        if self.base_type(return_type) == "long":
            self.append("mv t0, a0")
            self.append("mv t1, a1")

        elif return_type != "void":
            self.append("mv t0, a0")

        for register_index in range(7, -1, -1):
            self.pop(f"a{register_index}")

    def expression_type(self, node):
        node_type = node.get("type")

        if node_type == "int":
            return "int"

        if node_type == "long":
            return "long"

        if node_type == "byte":
            return "byte"

        if node_type == "bool":
            return "bool"

        if node_type == "string":
            return "string"

        if node_type == "variable":
            return self.lookup_variable(node["name"], node)["type"]

        if node_type == "index":
            array_type = self.expression_type(node["array"])

            if array_type == "string":
                return "byte"

            if self.is_array_type(array_type):
                return self.base_type(array_type)

            self.error("Cannot index a non-array value", node)

        if node_type == "array_creation":
            return node["element_type"] + "[]"

        if node_type == "input":
            return "byte"

        if node_type == "function_call":
            function = self.functions.get(node["name"])

            if function is not None:
                return function["return_type"]

            self.error(
                f"Unknown function '{node['name']}'",
                node,
            )

        if node_type == "unary":
            return self.expression_type(node["operand"])

        if node_type == "binary":
            left = self.expression_type(node["left"])
            right = self.expression_type(node["right"])

            if node["operator"] in (
                "==", "!=", "<", ">", "<=", ">=",
                "&&", "||",
            ):
                return "bool"

            if "long" in (self.base_type(left), self.base_type(right)):
                return "long"

            return "int"

        self.error(
            f"Cannot determine expression type for '{node_type}'",
            node,
        )