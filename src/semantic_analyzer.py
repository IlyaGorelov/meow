#Types of nodes:
PROGRAM = "program" #extra: body
VAR_DECLARATION="var_declaration" #extra: var_type, name, value
CONST_DECLARATION="const_declaration" #extra: look at VAR_DECLARATION
ASSIGNMENT = "assignment" #extra: target, value
VARIABLE = "variable" #extra: name
INDEX="index" #extra: array, index
INPUT="input"
OUTPUT="output"
CONTINUE_NODE="continue"
BREAK_NODE="break"
ARRAY_CREATION="array_creation" #element_type, size
CALL_STATEMENT="call_statement" #call
FUNCTION_CALL = "function_call" #name, args
RETURN_NODE = "return" #value
COMMENT_NODE="comment" #value
FUNCTION = "function" #return_type, name, params, body
PARAMETER = "parameter" #param_type, name
WHILE_NODE = "while" #condition, body
IF_NODE = "if" #condition, body, else_body
BINARY="binary" #operator, left, right
UNARY="unary" #operator="-", operand
INT = "int" #value
LONG = "long" #value
STRING = "string" #value
BYTE = "byte" #value
BOOL = "bool" #value

class SemanticError(Exception):
    pass

class SemanticAnalyzer:
    NUMERIC_TYPES = {BYTE, INT, LONG}

    def __init__(self):
        self.variables = {}
        self.functions = {}

    def analyze(self, ast):
        self.variables = {}
        self.functions = {}

        for node in ast["body"]:
            if node["type"] == FUNCTION:
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

        if kind == COMMENT_NODE:
            return

        if kind in (VAR_DECLARATION, CONST_DECLARATION):
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

        if kind == ASSIGNMENT:
            target = node["target"]

            if target["type"] == VARIABLE:
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

            elif target["type"] == INDEX:
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

        if kind == FUNCTION:
            self.function(node)
            return

        if kind == CALL_STATEMENT:
            self.call(node["call"], scope)
            return

        if kind == RETURN_NODE:
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

        if kind in (IF_NODE, WHILE_NODE):
            self.expression(node["condition"], scope)

            for statement in node["body"]:
                self.statement(statement, scope, function)

            if kind == IF_NODE and node["else_body"] is not None:
                for statement in node["else_body"]:
                    self.statement(statement, scope, function)

            return

        if kind == CONTINUE_NODE:
            return

        if kind == BREAK_NODE:
            return

        if kind == OUTPUT:
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

        if kind == INT or kind==LONG:
            return expected_type if expected_type in self.NUMERIC_TYPES else "int"

        if kind == BYTE:
            return BYTE

        if kind == STRING:
            return STRING

        if kind == BOOL:
            return BOOL

        if kind == INPUT:
            return BYTE

        if kind == VARIABLE:
            name = node["name"]

            if name not in scope:
                self.error(
                    f"Variable '{name}' is not declared",
                    node,
                )

            return scope[name]["type"]

        if kind == ARRAY_CREATION:
            size_type = self.expression(
                node["size"], scope, INT
            )
            self.check_type(INT, size_type, node["size"])
            return node["element_type"] + "[]"

        if kind == "index":
            array_type = self.expression(node["array"], scope)
            index_type = self.expression(
                node["index"], scope, "int"
            )

            self.check_type("int", index_type, node["index"])

            if array_type == STRING:
                return BYTE

            if array_type.endswith("[]"):
                return array_type[:-2]

            self.error(
                f"Cannot index a non-iterable value of type {array_type}",
                node,
            )

       
        if kind == UNARY:
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

        if kind == BINARY:
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

                return BOOL

            if operator in logical:
                self.check_type(BOOL, left_type, node["left"])
                self.check_type(BOOL, right_type, node["right"])
                return BOOL

            if operator in {"|", "&"}:
                if left_type not in self.NUMERIC_TYPES:
                    self.error(
                        f"Operator '{operator}' requires numbers, got {left_type}",
                        node,
                    )

                self.check_type(left_type, right_type, node["right"])
                return left_type

            if operator in {"+", "-", "*", "/", "%"}:
                if left_type not in self.NUMERIC_TYPES:
                    self.error(
                        f"Operator '{operator}' requires numbers, got {left_type}",
                        node,
                    )

                self.check_type(left_type, right_type, node["right"])
                return left_type

            self.error(f"Unsupported operator: {operator!r}", node)

        if kind == FUNCTION_CALL:
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