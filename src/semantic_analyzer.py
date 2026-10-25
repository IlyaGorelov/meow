class SemanticError(Exception):
    pass

class SemanticAnalyzer:
    NUMERIC_TYPES = {"byte", "int", "long"}

    def __init__(self):
        self.variables = {}
        self.functions = {}

    def analyze(self, ast):
        self.variables = {}
        self.functions = {}

        for node in ast["body"]:
            if node["type"] == "function":
                name = node["name"]

                if name in self.functions:
                    self.error(
                        f"Function '{name}' is already defined",
                        node,
                    )

                self.functions[name] = {
                    "return_type": node["return_type"],
                    "params": node["params"],
                    "node": node,
                }

        for node in ast["body"]:
            self.statement(node, self.variables, None)

        return True

    def error(self, message, node=None):
        line = node.get("line") if node else None

        if line is not None:
            raise SemanticError(f"Line {line}: {message}")

        raise SemanticError(message)

    def statement(self, node, scope, function):
        kind = node["type"]

        if kind == "comment":
            return

        if kind in ("var_declaration", "const_declaration"):
            name = node["name"]
            var_type = node["var_type"]

            if name in scope:
                self.error(
                    f"Variable '{name}' is already declared",
                    node,
                )

            actual_type = self.expression(
                node["value"], scope, var_type
            )
            self.check_type(var_type, actual_type, node["value"])

            scope[name] = {
                "type": var_type,
                "constant": kind == "const_declaration",
            }
            return

        if kind == "assignment":
            target = node["target"]

            if target["type"] == "variable":
                name = target["name"]

                if name not in scope:
                    self.error(
                        f"Variable '{name}' is not declared",
                        target,
                    )

                if scope[name]["constant"]:
                    self.error(
                        f"Cannot assign to constant '{name}'",
                        target,
                    )

                target_type = scope[name]["type"]

            elif target["type"] == "index":
                target_type = self.expression(target, scope)

            else:
                self.error(
                    f"Invalid assignment target: {target['type']!r}",
                    target,
                )

            actual_type = self.expression(
                node["value"], scope, target_type
            )
            self.check_type(
                target_type, actual_type, node["value"]
            )
            return

        if kind == "function":
            self.function(node)
            return

        if kind == "call_statement":
            self.call(node["call"], scope)
            return

        if kind == "return":
            if function is None:
                self.error(
                    "Return statement outside a function",
                    node,
                )

            expected = function["return_type"]
            value = node["value"]

            if expected == "void":
                if value is not None:
                    self.error(
                        "Void function cannot return a value",
                        node,
                    )
            else:
                if value is None:
                    self.error(
                        f"Function returning {expected} must return a value",
                        node,
                    )

                actual = self.expression(value, scope, expected)
                self.check_type(expected, actual, value)

            return

        if kind in ("if", "while"):
            self.expression(node["condition"], scope)

            for statement in node["body"]:
                self.statement(statement, scope, function)

            if kind == "if" and node["else_body"] is not None:
                for statement in node["else_body"]:
                    self.statement(statement, scope, function)

            return

        if kind == "continue":
            return

        if kind == "break":
            return

        if kind == "out":
            self.expression(node["value"], scope)
            return

        self.error(f"Unsupported statement node: {kind!r}", node)

    def function(self, node):
        signature = self.functions[node["name"]]

        scope = {}

        for parameter in node["params"]:
            param_name = parameter["name"]
            param_type = parameter["param_type"]

            scope[param_name] = {
                "type": param_type,
                "constant": False,
            }

        for statement in node["body"]:
            self.statement(statement, scope, signature)

    def expression(self, node, scope, expected_type=None):
        if node is None:
            self.error("Expected an expression", node)

        kind = node["type"]

        if kind == "number":
            return expected_type if expected_type in self.NUMERIC_TYPES else "int"

        if kind == "byte":
            return "byte"

        if kind == "string":
            return "string"

        if kind == "bool":
            return "bool"

        if kind == "input":
            return "byte"

        if kind == "variable":
            name = node["name"]

            if name not in scope:
                self.error(
                    f"Variable '{name}' is not declared",
                    node,
                )

            return scope[name]["type"]

        if kind == "array_creation":
            size_type = self.expression(
                node["size"], scope, "int"
            )
            self.check_type("int", size_type, node["size"])
            return node["element_type"] + "[]"

        if kind == "index":
            array_type = self.expression(node["array"], scope)
            index_type = self.expression(
                node["index"], scope, "int"
            )

            if not array_type.endswith("[]"):
                self.error(
                    f"Cannot index a non-array value of type {array_type}",
                    node,
                )

            self.check_type("int", index_type, node["index"])
            return array_type[:-2]

        if kind == "unary":
            operand_type = self.expression(
                node["operand"], scope, expected_type
            )

            if node["operator"] == "-":
                if operand_type not in ("int", "long", "byte"):
                    self.error(
                        f"Unary '-' requires a numeric value, got {operand_type}",
                        node,
                    )
                return operand_type

            self.error(
                f"Unsupported unary operator: {node['operator']!r}",
                node,
            )

        if kind == "binary":
            operator = node["operator"]

            left_type = self.expression(
                node["left"], scope, expected_type
            )
            right_type = self.expression(
                node["right"], scope, left_type
            )

            comparisons = {"==", "!=", "<", ">", "<=", ">="}
            logical = {"&&", "||"}

            if operator in comparisons:
                self.check_type(left_type, right_type, node)

                if operator in {"<", ">", "<=", ">="}:
                    if left_type not in self.NUMERIC_TYPES:
                        self.error(
                            f"Operator '{operator}' does not accept type {left_type}",
                            node,
                        )

                return "bool"

            if operator in logical:
                self.check_type("bool", left_type, node["left"])
                self.check_type("bool", right_type, node["right"])
                return "bool"

            if operator in {"|", "&"}:
                if left_type not in ("int", "long", "byte"):
                    self.error(
                        f"Operator '{operator}' requires numbers, got {left_type}",
                        node,
                    )

                self.check_type(left_type, right_type, node["right"])
                return left_type

            if operator in {"+", "-", "*", "/", "%"}:
                if left_type not in ("int", "long", "byte"):
                    self.error(
                        f"Operator '{operator}' requires numbers, got {left_type}",
                        node,
                    )

                self.check_type(left_type, right_type, node["right"])
                return left_type

            self.error(f"Unsupported operator: {operator!r}", node)

        if kind == "function_call":
            return_type = self.call(node, scope)

            if return_type == "void":
                self.error(
                    f"Void function '{node['name']}' cannot be used as an expression",
                    node,
                )

            return return_type

        self.error(f"Unsupported expression node: {kind!r}", node)

    def call(self, node, scope):
        name = node["name"]

        if name not in self.functions:
            self.error(f"Function '{name}' is not defined", node)

        signature = self.functions[name]
        parameters = signature["params"]
        arguments = node["args"]

        if len(arguments) != len(parameters):
            self.error(
                f"Function '{name}' expects {len(parameters)} arguments, "
                f"got {len(arguments)}",
                node,
            )

        for index, (argument, parameter) in enumerate(
            zip(arguments, parameters), start=1
        ):
            expected = parameter["param_type"]
            actual = self.expression(argument, scope, expected)

            if not self.types_compatible(expected, actual):
                self.error(
                    f"Argument {index} of function '{name}': "
                    f"expected {expected}, got {actual}",
                    argument,
                )

        return signature["return_type"]

    def types_compatible(self, expected, actual):
        if expected == actual:
            return True

        if expected in self.NUMERIC_TYPES and actual in self.NUMERIC_TYPES:
            return True

        return False

    def check_type(self, expected, actual, node=None):
        if not self.types_compatible(expected, actual):
            self.error(
                f"Type mismatch: expected {expected}, got {actual}",
                node,
            )