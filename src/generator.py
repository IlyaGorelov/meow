from parser_node_types import (
    ARRAY_CREATION,
    ARRAY_CREATION_WITH_ELEMENTS,
    ASSIGNMENT,
    BINARY,
    BOOL,
    BREAK_NODE,
    BYTE,
    CALL_STATEMENT,
    COMMENT_NODE,
    CONST_DECLARATION,
    CONTINUE_NODE,
    FUNCTION,
    FUNCTION_CALL,
    IF_NODE,
    INDEX,
    INPUT,
    INT,
    LONG,
    OUTPUT,
    RETURN_NODE,
    SET_VECTOR_LENGTH,
    UNARY,
    VAR_DECLARATION,
    VARIABLE,
    WHILE_NODE,
)


class CodeGeneratorError(Exception):
    pass


class CodeGenerator:
    def __init__(self, ast):
        self.ast = ast
        self.code = []
        self.data = []
        self.functions = {}
        self.globals = {}
        self.scopes = []
        self.stack_depth = 0
        self.loop_stack = []

        self.vl = 4

        self.current_function = None
        self.current_function_end = None

        self.array_counter = 0

        self.label_counter = 0

    def generate(self):
        body = self.ast.get("body", [])

        for node in body:
            if node["type"] == FUNCTION:
                name = node["name"]
                self.functions[name] = node

        self.append_label("_start")
        self.load_immediate("sp", 4000)

        for node in body:
            if node["type"] == FUNCTION:
                continue

            self.generate_statement(node)

        self.append("halt")

        for func_node in self.functions.values():
            self.generate_function(func_node)

        output = []

        if self.data:
            output.append(".data")
            output.extend(self.data)

        output.append(".text")
        output.extend(self.code)

        return "\n".join(output) + "\n"

    def error(self, message, node=None):
        line = node.get("line") if node is not None else None

        if line is not None:
            raise CodeGeneratorError(f"Line {line}: {message}")  # noqa TRY003

        raise CodeGeneratorError(message)

    def append(self, instruction):
        self.code.append(f"\t{instruction}")

    def append_label(self, label):
        self.code.append(f"{label}:")

    def generate_statement(self, node):  # noqa C901
        node_type = node.get("type")

        if node_type in (VAR_DECLARATION, CONST_DECLARATION):
            self.generate_declaration(node)

        elif node_type == ASSIGNMENT:
            self.generate_assignment(node)

        elif node_type == OUTPUT:
            self.generate_output(node)

        elif node_type == CONTINUE_NODE:
            self.generate_continue(node)

        elif node_type == BREAK_NODE:
            self.generate_break(node)

        elif node_type == CALL_STATEMENT:
            self.generate_expression(node["call"])

        elif node_type == RETURN_NODE:
            self.generate_return(node)

        elif node_type == COMMENT_NODE:
            pass

        elif node_type == WHILE_NODE:
            self.generate_while(node)

        elif node_type == IF_NODE:
            self.generate_if(node)

        elif node_type == SET_VECTOR_LENGTH:
            self.generate_set_vector_length(node)

        else:
            self.error(
                f"Unsupported statement: {node_type}",
                node,
            )

    def generate_declaration(self, node):
        name = node["name"]
        type_name = str(node["var_type"])

        if self.current_function is None:
            self.generate_global_declaration(node, name, type_name)
            return

        if type_name.endswith("[]"):
            self.generate_local_array_declaration(node, name, type_name)
            return

        self.generate_local_variable_declaration(node, name, type_name)

    def generate_global_declaration(self, node, name, type_name):
        is_const = node["type"] == CONST_DECLARATION
        value = node.get("value")
        label = f"global_{name}"

        if name in self.globals:
            self.error(f"{name} is already defined", node)

        self.globals[name] = {
            "type": type_name,
            "label": label,
            "storage": "global",
            "is_const": is_const,
        }

        if type_name.endswith("[]"):
            self.declare_array(node)
            return

        if self.declare_global_storage(label, type_name, value):
            return

        if value is None:
            self.error("Decalaration without a value", node)

        self.initialize_global_variable(name, label, type_name, value)

    def declare_global_storage(self, label, type_name, value):
        if type_name == LONG:
            self.data.append(f"{label}: .long 0")

        elif type_name in (BYTE, BOOL):
            self.data.append(f"{label}: .byte 0")

        elif type_name == INT:
            self.data.append(f"{label}: .word 0")

        elif type_name == "int128":
            if value["type"] == ARRAY_CREATION_WITH_ELEMENTS:
                elements = [str(e["value"]) for e in value["elements"]]
                elements += ["0"] * (4 - len(elements))
                self.data.append(f"{label}: .word {', '.join(elements)}")
                return True

            self.data.append(f"{label}: .word 0, 0, 0, 0")

        return False

    def initialize_global_variable(self, name, label, type_name, value):
        is_long = type_name == LONG
        is_vector = type_name == "int128"

        if is_long and self.expression_type(value) != LONG:
            self.append("addi t1, zero, 0")

        if is_vector:
            self.generate_vector_expression(value)
        else:
            self.generate_expression(value)

        if is_long:
            if self.expression_type(value) != LONG:
                self.append("mv t1, t0")
                self.append("addi t0, zero, 0")

            self.store_long_global(label)

        elif is_vector:
            self.store_vector_global(label)

        else:
            self.store_variable(name, "t0")

    def generate_local_array_declaration(self, node, name, type_name):
        label = f"local_{self.current_function}_{name}_{self.array_counter}"
        self.array_counter += 1

        self.scopes[-1][name] = {
            "type": type_name,
            "label": label,
            "storage": "static_array",
        }

        self.declare_array(node, label)

    def generate_local_variable_declaration(self, node, name, type_name):
        offset = node["_slot_offset"]

        self.scopes[-1][name] = {
            "type": type_name,
            "offset": offset,
            "storage": "local",
        }

        value = node.get("value")

        if type_name == "int128":
            self.generate_vector_expression(value)
        else:
            self.generate_expression(value)

        if self.base_type(type_name) == LONG:
            self.store_long("t0", "t1", offset)

        elif type_name == "int128":
            self.append(f"vstore v0, {offset}(s0)")

        else:
            self.store_register_to_local("t0", offset, type_name)

    def store_long(self, high_register, low_register, offset):
        self.append(f"sw {high_register}, {offset}(s0)")
        self.append(f"sw {low_register}, {offset + 4}(s0)")

    def store_register_to_local(self, register, offset, type_name):
        base = self.base_type(type_name)

        instruction = "sb" if base in (BYTE, BOOL) else "sw"

        self.append(f"{instruction} {register}, {offset}(s0)")

    def declare_array(self, node, label=None):
        element_type = node["var_type"][:-2]
        value = node["value"]
        name = node["name"]

        if label is None:
            label = f"global_{name}"

        data_label = f"{label}_data"

        directives = {INT: ".word", LONG: ".long", BYTE: ".byte"}

        directive = directives.get(element_type)

        self.data.append(f"{label}: .word 0")
        if value["type"] == ARRAY_CREATION_WITH_ELEMENTS:
            elements = [str(e["value"]) for e in value["elements"]] + ["0"]
        elif value["type"] == ARRAY_CREATION:
            size_node = value["size"]

            if size_node["type"] != INT:
                self.error("Array expects a constant length", node)

            size = size_node["value"]

            elements = ["0"] * (size + 1)  # data + null-terminator
        elif value["type"] == FUNCTION_CALL:
            self.generate_expression(value)
            self.load_global_address("t1", label)
            self.append("sw t0, 0(t1)")

        if value["type"] != FUNCTION_CALL:
            self.data.append(f"{data_label}: {directive} {', '.join(elements)}")
            self.load_global_address("t0", data_label)
            self.load_global_address("t1", label)
            self.append("sw t0, 0(t1)")

    def generate_assignment(self, node):
        target = node["target"]
        value = node["value"]

        if target["type"] == VARIABLE:
            self.generate_variable_assignment(target, value, node)
        elif target["type"] == INDEX:
            self.generate_index_assignment(target, value)

    def generate_variable_assignment(self, target, value, node):
        name = target["name"]
        info = self.lookup_variable(name)

        if info.get("is_const", False):
            self.error("Can't assign to const", node)

        if info["type"] == "int128":
            self.generate_vector_expression(value)
        else:
            self.generate_expression(value)

        if info["type"] == LONG:
            self.store_long_variable(info)
        elif info["type"] == "int128":
            self.store_vector_variable(info)
        else:
            self.store_variable(name, "t0")

    def store_long_variable(self, info):
        if info["storage"] == "global":
            self.store_long_global(info["label"])

        elif info["storage"] == "argument_register":
            index = info["register_index"]
            self.append(f"mv a{index}, t0")
            self.append(f"mv a{index + 1}, t1")

        else:
            offset = info["offset"]
            self.append(f"sw t0, {offset}(s0)")
            self.append(f"sw t1, {offset + 4}(s0)")

    def store_vector_variable(self, info):
        if info["storage"] == "global":
            self.store_vector_global(info["label"])
        else:
            self.append(f"vstore v0, {info['offset']}(s0)")

    def generate_index_assignment(self, target, value):
        if self.expression_type(value) == "int128":
            self.generate_vector_expression(value)
            self.generate_array_address(target)
            self.append("vstore v0, 0(t2)")
            return

        self.generate_array_address(target)
        self.push("t2")

        self.generate_expression(value)

        self.pop("t2")

        element_type = self.expression_type(target)
        self.store_array_element(element_type)

    def store_array_element(self, element_type):
        if element_type == LONG:
            self.append("sw t0, 0(t2)")
            self.append("sw t1, 4(t2)")

        elif element_type in (BYTE, BOOL):
            self.append("sb t0, 0(t2)")

        else:
            self.append("sw t0, 0(t2)")

    def generate_output(self, node):
        self.generate_expression(node["value"])
        self.append("out t0, 1")

    def generate_continue(self, node):
        start_label, _ = self.loop_stack[-1]
        self.append(f"j {start_label}")
        return

    def generate_break(self, node):
        _, end_label = self.loop_stack[-1]
        self.append(f"j {end_label}")
        return

    def generate_return(self, node):
        value = node.get("value")

        if value is not None:
            self.generate_expression(value)

            return_type = self.functions[self.current_function]["return_type"]

            if return_type == LONG:
                self.append("mv a0, t0")
                self.append("mv a1, t1")
            else:
                self.append("mv a0, t0")

        self.append(f"j {self.current_function_end}")

    def generate_while(self, node):
        start_label = self.label_with_prefix("while_start")
        end_label = self.label_with_prefix("while_end")

        self.append_label(f"{start_label}")
        self.generate_expression(node["condition"])
        self.append(f"beq t0, zero, {end_label}")

        self.loop_stack.append((start_label, end_label))

        for statement in node["body"]:
            self.generate_statement(statement)

        self.loop_stack.pop()

        self.append(f"j {start_label}")
        self.append_label(f"{end_label}")

        return

    def generate_if(self, node):
        else_label = self.label_with_prefix("else")
        end_label = self.label_with_prefix("endif")

        self.generate_expression(node["condition"])
        self.append(f"beq t0, zero, {else_label}")

        for statement in node["body"]:
            self.generate_statement(statement)
        self.append(f"j {end_label}")

        self.append_label(else_label)

        else_body = node.get("else_body")
        if else_body is not None:
            for statement in else_body:
                self.generate_statement(statement)

        self.append_label(end_label)

    def generate_set_vector_length(self, node):
        value = node["value"]

        if value["type"] != INT:
            self.error(f"setLength expects number not {value['type']}", node)

        self.append(f"vsetvli s1, {value['value']}")
        self.vl = value["value"]
        return

    def generate_expression(self, node):  # noqa: C901
        node_type = node.get("type")

        if node_type in (INT, BYTE):
            self.load_immediate("t0", int(node["value"]))

        elif node_type == LONG:
            self.load_long_immediate("t0", "t1", int(node["value"]))

        elif node_type == BOOL:
            value = node["value"]
            value = value.lower() == "true"
            self.load_immediate("t0", int(bool(value)))

        elif node_type == VARIABLE:
            self.load_variable(node["name"], node)

        elif node_type == INDEX:
            self.generate_array_access(node)

        elif node_type == BINARY:
            self.generate_binary(node)

        elif node_type == UNARY:
            self.generate_unary(node)

        elif node_type == FUNCTION_CALL:
            self.generate_function_call(node)

        elif node_type == INPUT:
            self.append("in t0, 0")
        return

    def generate_vector_expression(self, node):
        node_type = node["type"]

        if node_type == INDEX:
            self.generate_array_address(node)
            self.append("vload v0, 0(t2)")
            return

        if node_type == VARIABLE:
            self.load_variable(node["name"], node)
            return

        if node_type == BINARY:
            self.generate_vector_binary(node)
            return

    def generate_binary(self, node):  # noqa: C901
        operator = node["operator"]

        left_type = self.expression_type(node["left"])
        right_type = self.expression_type(node["right"])

        is_long = self.base_type(left_type) == LONG or self.base_type(right_type) == LONG

        is_vector = self.base_type(left_type) == "int128" or self.base_type(right_type) == "int128"

        if is_long:
            self.generate_long_binary(node)
            return

        if is_vector:
            self.generate_vector_binary(node)
            return

        if operator in ("&&", "||"):
            result = self.label_with_prefix("logic_result")
            end_label = self.label_with_prefix("logic_end")
            self.generate_expression(node["left"])

            if operator == "&&":
                self.append(f"beq t0, zero, {result}")
                result_when_skipped = 0
            else:
                self.append(f"bne t0, zero, {result}")
                result_when_skipped = 1

            self.generate_expression(node["right"])
            self.append("sltu t0, zero, t0")
            self.append(f"j {end_label}")
            self.append_label(result)
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
        return

    def generate_long_binary(self, node):  # noqa: C901
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
            return

        else:
            self.error(f"Unsupported long operator: {operator}", node)

        return

    def generate_vector_binary(self, node):
        operator = node["operator"]

        self.generate_vector_expression(node["right"])
        self.push_vector("v0")

        self.generate_vector_expression(node["left"])
        self.pop_vector("v1")

        operations = {"+": "vadd", "-": "vsub", "*": "vmul", "/": "vdiv"}

        if operator in operations:
            self.append(f"{operations[operator]} v0, v0, v1")
            return

        if operator == "<":
            self.append("vslt v0, v1, v0")

        elif operator == ">":
            self.append("vslt v0, v0, v1")

    def generate_unary(self, node):
        operand_type = self.expression_type(node["operand"])

        self.generate_expression(node["operand"])

        if self.base_type(operand_type) == LONG:
            self.append("sub t1, zero, t1")
            self.append("sltu t2, zero, t1")
            self.append("sub t0, zero, t0")
            self.append("sub t0, t0, t2")
        else:
            self.append("sub t0, zero, t0")
        return

    def generate_function_call(self, node):
        function_name = node["name"]
        args = node.get("args", [])

        function = self.functions[function_name]

        reg_index = 0

        for arg in args:
            arg_type = self.expression_type(arg)
            self.generate_expression(arg)

            reg_index = self.pass_function_argument(arg_type, reg_index)

        self.append(f"jal ra, fn_{function_name}")

        self.load_function_return(function["return_type"])

        for i in range(reg_index - 1, -1, -1):
            self.pop(f"a{i}")

        return

    def pass_function_argument(self, arg_type, reg_index):
        if arg_type == LONG:
            self.push(f"a{reg_index}")
            self.append(f"mv a{reg_index}, t0")
            reg_index += 1

            self.push(f"a{reg_index}")
            self.append(f"mv a{reg_index}, t1")
            reg_index += 1

        elif arg_type in (BYTE, BOOL, INT) or arg_type.endswith("[]"):
            self.push(f"a{reg_index}")
            self.append(f"mv a{reg_index}, t0")
            reg_index += 1

        return reg_index

    def load_function_return(self, return_type):
        if self.base_type(return_type) == LONG:
            self.append("mv t0, a0")
            self.append("mv t1, a1")

        elif return_type != "void":
            self.append("mv t0, a0")

    def generate_function(self, node):
        name = node["name"]
        params = node.get("params", [])
        body = node.get("body", [])

        self.scopes = [{}]

        frame_size = self.calculate_frame(node)
        self.current_function_end = self.label_with_prefix(f"{name}_end")
        self.current_function = name

        self.append_label(f"fn_{name}")
        self.append(f"addi sp, sp, -{frame_size}")
        self.append(f"sw ra, {frame_size - 4}(sp)")
        self.append(f"sw s0, {frame_size - 8}(sp)")
        self.append("mv s0, sp")

        reg_index = 0
        for parameter in params:
            param_name = parameter["name"]
            param_type = parameter["param_type"]

            self.scopes[-1][param_name] = {
                "type": param_type,
                "storage": "argument_register",
                "register_index": reg_index,
            }

            reg_index += 2 if param_type == LONG else 1

        self.scopes.append({})
        for statement in body:
            self.generate_statement(statement)
        self.scopes.pop()

        self.append_label(self.current_function_end)

        self.append(f"lw ra, {frame_size - 4}(s0)")
        self.append(f"lw t0, {frame_size - 8}(s0)")
        self.append(f"addi sp, s0, {frame_size}")
        self.append("mv s0, t0")
        self.append("jalr zero, 0(ra)")
        return

    def calculate_frame(self, func_node):
        slots = self.collect_local_declarations(func_node.get("body", []))
        offset = 0

        for node in slots:
            node["_slot_offset"] = offset
            offset += self.local_storage_size(node)

        return offset + 8  # ra and s0

    def local_storage_size(self, node):
        type_name = node["var_type"]

        if not type_name.endswith("[]"):
            return self.type_size(type_name)

        return 0

    def collect_local_declarations(self, body):  # noqa: C901
        declarations = []

        def visit_statement(node):
            node_type = node["type"]

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

    def store_long_global(self, label, high_register="t0", low_register="t1"):
        self.load_global_address("t2", label)
        self.append(f"sw {high_register}, 0(t2)")
        self.append(f"sw {low_register}, 4(t2)")

    def load_global_address(self, register, label):
        self.append(f"lui {register}, %hi({label})")
        self.append(f"addi {register}, {register}, %lo({label})")

    def store_variable(self, name, register="t0"):
        info = self.lookup_variable(name)

        if info["type"].endswith("[]"):
            if info["storage"] == "argument_register":
                index = info["register_index"]
                self.append(f"mv a{index}, {register}")
            else:
                self.load_global_address("t2", info["label"])
                self.append(f"sw {register}, 0(t2)")

            return

        type_name = self.base_type(info["type"])

        if info["storage"] == "argument_register":
            register_index = info["register_index"]
            self.append(f"mv a{register_index}, {register}")
            return

        instruction = "sb" if type_name in (BYTE, BOOL) else "sw"

        if info["storage"] == "global":
            self.load_global_address("t2", info["label"])
            self.append(f"{instruction} {register}, 0(t2)")

        elif info["storage"] == "local":
            self.append(f"{instruction} {register}, {info['offset']}(s0)")

    def store_vector_global(self, label, register="v0"):
        self.load_global_address("t2", label)
        self.append(f"vstore {register}, 0(t2)")

    def lookup_variable(self, name):
        found = None
        for scope in reversed(self.scopes):
            if name in scope:
                found = scope[name]

        if name in self.globals:
            found = self.globals[name]

        if not found:
            self.error(f"{name} doesnt exist")

        return found

    def generate_array_address(self, node):
        array_node = node["array"]
        index_node = node["index"]

        array_type = self.expression_type(array_node)
        element_size = self.type_size(array_type[:-2])

        self.generate_expression(array_node)
        self.append("mv t2, t0")

        self.push("t2")

        self.generate_expression(index_node)

        if element_size != 1:
            self.load_immediate("t1", element_size)
            self.append("mul t0, t0, t1")

        self.append("mv t1, t0")
        self.pop("t2")

        self.append("add t2, t2, t1")

    def expression_type(self, node):  # noqa: C901
        node_type = node.get("type")

        if node_type in (INT, LONG, BYTE, BOOL):
            return node_type

        if node_type == VARIABLE:
            return self.lookup_variable(node["name"])["type"]

        if node_type == INDEX:
            array_type = self.expression_type(node["array"])
            return array_type[:-2]

        if node_type == ARRAY_CREATION:
            return node["element_type"] + "[]"

        if node_type == ARRAY_CREATION_WITH_ELEMENTS:
            return node["elements"][0]["type"] + "[]"

        if node_type == INPUT:
            return INT

        if node_type == "function_call":
            function = self.functions.get(node["name"])

            if function is not None:
                return function["return_type"]

            self.error(
                f"Unknown function '{node['name']}'",
                node,
            )

        if node_type == UNARY:
            return self.expression_type(node["operand"])

        if node_type == BINARY:
            left = self.expression_type(node["left"])
            right = self.expression_type(node["right"])

            if "int128" in (self.base_type(left), self.base_type(right)):
                return "int128"

            if node["operator"] in (
                "==",
                "!=",
                "<",
                ">",
                "<=",
                ">=",
                "&&",
                "||",
            ):
                return BOOL

            if LONG in (self.base_type(left), self.base_type(right)):
                return LONG

            return INT

        return None

    def type_size(self, type_name):
        if str(type_name).endswith("[]"):
            return 4

        sizes = {"byte": 1, "bool": 1, "int": 4, "long": 8, "int128": 16}

        return sizes[type_name]

    def push(self, register):
        self.append("addi sp, sp, -4")
        self.append(f"sw {register}, 0(sp)")
        self.stack_depth += 4

    def push_vector(self, register):
        self.append(f"addi sp, sp, {-4 * self.vl}")
        self.append(f"vstore {register}, 0(sp)")
        self.stack_depth += 4 * self.vl

    def pop(self, register):
        self.append(f"lw {register}, 0(sp)")
        self.append("addi sp, sp, 4")
        self.stack_depth -= 4

    def pop_vector(self, register):
        self.append(f"vload {register}, 0(sp)")
        self.append(f"addi sp, sp, {4 * self.vl}")
        self.stack_depth -= 4 * self.vl

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

    def label_with_prefix(self, prefix="L"):
        label = f".{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label

    def load_long_immediate(self, high_register, low_register, value):
        high, low = self.split_long(value)

        self.load_immediate(high_register, high)
        self.load_immediate(low_register, low)

    def split_long(self, value):
        value &= 0xFFFFFFFFFFFFFFFF

        high = (value >> 32) & 0xFFFFFFFF
        low = value & 0xFFFFFFFF

        if high >= 0x80000000:
            high -= 0x100000000

        if low >= 0x80000000:
            low -= 0x100000000

        return high, low

    def load_variable(self, name, node=None):
        info = self.lookup_variable(name)
        var_type = self.base_type(info["type"])

        if info["type"].endswith("[]"):
            self.load_array_variable(info)
        elif info["storage"] == "argument_register":
            self.load_argument_variable(info, var_type)
        elif info["storage"] == "local":
            self.load_local_variable(info, var_type)
        elif info["storage"] == "global":
            self.load_global_variable(info, var_type)

    def load_array_variable(self, info):
        if info["storage"] == "argument_register":
            self.append(f"mv t0, a{info['register_index']}")
        else:
            self.load_global_address("t2", info["label"])
            self.append("lw t0, 0(t2)")

    def load_argument_variable(self, info, var_type):
        register_index = info["register_index"]

        self.append(f"mv t0, a{register_index}")

        if var_type == LONG:
            self.append(f"mv t1, a{register_index + 1}")

    def load_local_variable(self, info, var_type):
        offset = info["offset"]

        if var_type == LONG:
            self.append(f"lw t0, {offset}(s0)")
            self.append(f"lw t1, {offset + 4}(s0)")
            return

        if var_type == "int128":
            self.append(f"vload v0, {offset}(s0)")
            return

        instruction = "lb" if var_type in (BYTE, BOOL) else "lw"
        self.append(f"{instruction} t0, {offset}(s0)")

    def load_global_variable(self, info, var_type):
        self.load_global_address("t2", info["label"])

        if var_type == LONG:
            self.append("lw t0, 0(t2)")
            self.append("lw t1, 4(t2)")
            return

        if var_type == "int128":
            self.append("vload v0, 0(t2)")
            return

        instruction = "lw" if var_type in (INT, LONG) else "lb"
        self.append(f"{instruction} t0, 0(t2)")

    def generate_array_access(self, node):
        array_type = self.expression_type(node["array"])
        element_type = array_type[:-2]

        self.generate_array_address(node)
        if element_type == LONG:
            self.append("lw t0, 0(t2)")
            self.append("lw t1, 4(t2)")
        elif element_type in (BYTE, BOOL):
            self.append("lb t0, 0(t2)")
        else:
            self.append("lw t0, 0(t2)")

    def base_type(self, type_name):
        if type_name.endswith("[]"):
            return type_name[:-2]
        return type_name

    @staticmethod
    def get_code_addresses(code: str):
        addresses = {}
        address = 0
        in_text = False

        for line in code.splitlines():
            text = line.strip()

            if text == ".text":
                in_text = True
                continue

            if not in_text or not text:
                continue

            if text.endswith(":"):
                addresses[text[:-1]] = address
                continue

            address += 4

        return addresses

    @staticmethod
    def resolve_code_addresses(code: str):
        addresses = CodeGenerator.get_code_addresses(code)
        in_text = False
        result = []
        address = 0

        for line in code.splitlines():
            text = line.strip()

            if text == ".text":
                result.append(line)
                in_text = True
                continue

            if text.startswith(".") or text.endswith(":") or not in_text:
                result.append(line)
                continue

            parts = text.split()
            instruction = parts[0]

            if instruction == "j":
                label = parts[1]
                parts[1] = str(addresses[label] - address - 4)

            elif instruction == "jal":
                label = parts[2]
                parts[2] = str(addresses[label] - address - 4)

            elif instruction in ("beq", "bne", "blt", "bge", "bltu", "bgeu"):
                label = parts[3]
                parts[3] = str(addresses[label] - address - 4)

            result.append(" ".join(parts))
            address += 4

        return "\n".join(result)

    @staticmethod
    def get_data_addresses(code: str):
        addresses = {}
        address = 0

        for line in code.splitlines():
            text = line.strip()

            if text == ".text":
                break

            if ":" not in text:
                continue

            label, directive = text.split(":", 1)
            directive = directive.strip()

            addresses[label] = address

            if directive.startswith(".byte"):
                size = len(directive[5:].strip().split(","))

            elif directive.startswith(".word"):
                size = 4 * len(directive[5:].strip().split(","))

            elif directive.startswith(".long"):
                size = 8 * len(directive[5:].strip().split(","))

            address += size

        return addresses

    @staticmethod
    def split_address(value):
        upper = (value + 0x800) >> 12
        lower = value - (upper << 12)

        return upper, lower

    @staticmethod
    def resolve_data_references(code: str):
        addresses = CodeGenerator.get_data_addresses(code)

        result = []

        for line in code.splitlines():
            parts = line.split()

            for i, part in enumerate(parts):
                if part.startswith("%hi("):
                    label = part[4:-1]
                    upper, _ = CodeGenerator.split_address(addresses[label])
                    parts[i] = str(upper)

                elif part.startswith("%lo("):
                    label = part[4:-1]
                    _, lower = CodeGenerator.split_address(addresses[label])
                    parts[i] = str(lower)

            result.append(" ".join(parts))

        return "\n".join(result)
