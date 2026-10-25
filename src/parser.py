
class ParserError(Exception):
    pass


class Parser:
    TYPE_TOKENS = {
        "INT": "int",
        "LONG": "long",
        "BYTE": "byte",
        "STRING_TYPE": "string",
    }

    ARRAY_TYPE_TOKENS = {"INT", "LONG", "BYTE"}

    BINARY_OPERATORS = {
        "LOGICAL_OR": ("||", 1),
        "LOGICAL_AND": ("&&", 2),
        "BITWISE_OR": ("|", 3),
        "BITWISE_AND": ("&", 4),
        "EQUAL": ("==", 5),
        "NOT_EQUAL": ("!=", 5),
        "LESS": ("<", 6),
        "GREATER": (">", 6),
        "LESS_EQUAL": ("<=", 6),
        "GREATER_EQUAL": (">=", 6),
        "PLUS": ("+", 7),
        "MINUS": ("-", 7),
        "MULTIPLY": ("*", 8),
        "DIVIDE": ("/", 8),
        "MODULO": ("%", 8),
    }

    def __init__(self, tokens):
        self.tokens = list(tokens)

        if not self.tokens or self.tokens[-1][0] != "EOF":
            token = self.tokens[-1] if self.tokens else (None, None, 1, 0)
            self.tokens.append(("EOF", None, token[2], token[3]))

        self.pos = 0

    def current(self):
        if self.pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[self.pos]

    def peek(self, offset=1):
        # be default: peeks next token
        index = self.pos + offset
        if index >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[index]

    def is_current_token_in_tuple(self, *types):
        return self.current()[0] in types

    def advance(self):
        token = self.current()
        if token[0] != "EOF":
            self.pos += 1
        return token

    def match(self, *types):
        if self.is_current_token_in_tuple(*types):
            return self.advance()
        return None

    def error(self, message):
        line = self.current()[2]
        char = self.current()[3]
        raise ParserError(f"Line {line}:{char}: {message}")

    def expect(self, token_type, description=None):
        if not self.is_current_token_in_tuple(token_type):
            actual_type, actual_value, line, char = self.current()
            expected = description or token_type
            raise ParserError(
                f"Line {line}:{char}: expected {expected}, "
                f"got {actual_type} ({actual_value!r})"
            )
        return self.advance()

    def node(self, node_type, **fields):
        return {
            "type": node_type,
            "line": self.tokens[max(0, self.pos - 1)][2],
            "char": self.tokens[max(0, self.pos - 1)][3],
            **fields,
        }

    def parse(self):
        body = []

        while not self.is_current_token_in_tuple("EOF"):
            body.append(self.parse_term())

        return self.node("program", body=body)

    def parse_term(self):
        if self.is_current_token_in_tuple("COMMENT"):
            return self.parse_comment()

        if self.is_current_token_in_tuple("CONST"):
            return self.parse_const_declaration()

        if self.is_current_token_in_tuple("WHILE"):
            return self.parse_cycle()

        if self.is_current_token_in_tuple("IF"):
            return self.parse_branch()

        if self.is_current_token_in_tuple("CONTINUE"):
            return self.parse_continue()

        if self.is_current_token_in_tuple("BREAK"):
            return self.parse_break()

        if self.is_current_token_in_tuple("RETURN"):
            return self.parse_return()

        if self.is_current_token_in_tuple("MEOW"):
            return self.parse_output()

        if self.is_current_token_in_tuple("INT", "LONG", "BYTE", "STRING_TYPE"):
            return self.parse_declaration_or_function()

        if self.is_current_token_in_tuple("VOID"):
            return self.parse_function()

        if self.is_current_token_in_tuple("IDENT"):
            if self.peek()[0] == "LPAREN":
                return self.parse_call_statement()
            return self.parse_assignment()

        self.error(f"unexpected token {self.current()}")
    
    def parse_type(self, allow_void=False):
        if allow_void and self.match("VOID"):
            return "void"

        token_type = self.current()[0]

        if token_type not in self.TYPE_TOKENS:
            self.error(f"expected a type, got {self.current()}")

        base_type = self.TYPE_TOKENS[self.advance()[0]]

        if self.match("LBRACKET"):
            if base_type not in {"int", "long", "byte"}:
                self.error(f"arrays of {base_type} are not allowed yet")

            self.expect("RBRACKET", "']' in array type")

            if self.is_current_token_in_tuple("LBRACKET"):
                self.error("nested arrays are not allowed yet")

            return base_type + "[]"

        return base_type

    def parse_array_element_type(self):
        token_type = self.current()[0]

        if token_type not in self.ARRAY_TYPE_TOKENS:
            self.error(
                "array creation requires int, long, or byte; "
                f"got {self.current()}"
            )

        return self.TYPE_TOKENS[self.advance()[0]]

    def parse_declaration_or_function(self):
        start = self.pos
        declared_type = self.parse_type()

        if self.is_current_token_in_tuple("IDENT") and self.peek()[0] == "LPAREN":
            name = self.expect("IDENT", "function name")[1]
            return self.parse_function_after_name(declared_type, name)

        self.pos = start
        return self.parse_var_declaration()

    def parse_var_declaration(self):
        var_type = self.parse_type()
        name = self.expect("IDENT", "variable name")[1]
        self.expect("ASSIGN", "'='")
        value = self.parse_initializer()
        self.expect("SEMICOLON", "';'")

        return self.node(
            "var_declaration",
            var_type=var_type,
            name=name,
            value=value,
        )

    def parse_const_declaration(self):
        self.expect("CONST")
        declaration = self.parse_var_declaration()

        return self.node(
            "const_declaration",
            var_type=declaration["var_type"],
            name=declaration["name"],
            value=declaration["value"],
        )

    def parse_initializer(self):
        if self.is_current_token_in_tuple("HEAR"):
            return self.parse_input_call()

        if self.is_current_token_in_tuple("NEW"):
            return self.parse_array_creation()

        return self.parse_expression()

    def parse_assignment(self):
        target = self.parse_lvalue()
        self.expect("ASSIGN", "'='")
        value = self.parse_initializer()
        self.expect("SEMICOLON", "';'")

        return self.node(
            "assignment",
            target=target,
            value=value,
        )

    def parse_lvalue(self):
        name = self.expect("IDENT", "variable name")[1]
        target = self.node("variable", name=name)

        if self.match("LBRACKET"):
            index = self.parse_expression()
            self.expect("RBRACKET", "']'")
            target = self.node("index", array=target, index=index)

        return target

    def parse_input_call(self):
        token_type = self.advance()[0]
        self.expect("LPAREN", "'('")
        self.expect("RPAREN", "')'")

        return self.node(
            "input",
            input_type="hear",
        )

    def parse_array_creation(self):
        self.expect("NEW")
        element_type = self.parse_array_element_type()
        self.expect("LBRACKET", "'['")
        size = self.parse_expression()
        self.expect("RBRACKET", "']'")

        return self.node(
            "array_creation",
            element_type=element_type,
            size=size,
        )

    def parse_call_statement(self):
        call = self.parse_function_call()
        self.expect("SEMICOLON", "';'")
        return self.node("call_statement", call=call)

    def parse_output(self):
        self.expect("MEOW")
        self.expect("LPAREN", "'('")

        if self.is_current_token_in_tuple("STRING_LITERAL", "BYTE_LITERAL"):
            value = self.parse_primary()
        else:
            value = self.parse_expression()

        self.expect("RPAREN", "')'")
        self.expect("SEMICOLON", "';'")

        return self.node("out", value=value)

    def parse_continue(self):
        self.expect("CONTINUE")
        self.expect("SEMICOLON", "';'")
        return self.node("continue")

    def parse_break(self):
        self.expect("BREAK")
        self.expect("SEMICOLON", "';'")
        return self.node("break")

    def parse_return(self):
        self.expect("RETURN")

        value = None
        if not self.is_current_token_in_tuple("SEMICOLON"):
            value = self.parse_expression()

        self.expect("SEMICOLON", "';'")
        return self.node("return", value=value)

    def parse_comment(self):
        _, value, _, _ = self.advance()
        return self.node("comment", value=value)

    def parse_function(self):
        return_type = self.parse_type(allow_void=True)
        name = self.expect("IDENT", "function name")[1]
        return self.parse_function_after_name(return_type, name)

    def parse_function_after_name(self, return_type, name):
        self.expect("LPAREN", "'('")
        parameters = []

        if not self.is_current_token_in_tuple("RPAREN"):
            parameters.append(self.parse_parameter())

            while self.match("COMMA"):
                parameters.append(self.parse_parameter())

        self.expect("RPAREN", "')'")
        self.expect("LBRACE", "'{'")

        body = []
        while not self.is_current_token_in_tuple("RBRACE", "EOF"):
            body.append(self.parse_body_term())

        self.expect("RBRACE", "'}'")

        return self.node(
            "function",
            return_type=return_type,
            name=name,
            params=parameters,
            body=body,
        )

    def parse_parameter(self):
        param_type = self.parse_type()
        name = self.expect("IDENT", "parameter name")[1]

        return self.node(
            "parameter",
            param_type=param_type,
            name=name,
        )

    def parse_body_term(self):
        if self.is_current_token_in_tuple("COMMENT"):
            return self.parse_comment()
        if self.is_current_token_in_tuple("CONST"):
            return self.parse_const_declaration()
        if self.is_current_token_in_tuple("WHILE"):
            return self.parse_cycle()
        if self.is_current_token_in_tuple("IF"):
            return self.parse_branch()
        if self.is_current_token_in_tuple("CONTINUE"):
            return self.parse_continue()
        if self.is_current_token_in_tuple("BREAK"):
            return self.parse_break()
        if self.is_current_token_in_tuple("RETURN"):
            return self.parse_return()
        if self.is_current_token_in_tuple("MEOW"):
            return self.parse_output()
        if self.is_current_token_in_tuple("INT", "LONG", "BYTE", "STRING_TYPE"):
            return self.parse_var_declaration()
        if self.is_current_token_in_tuple("IDENT"):
            if self.peek()[0] == "LPAREN":
                return self.parse_call_statement()
            return self.parse_assignment()

        self.error(
            f"unexpected token in function body: {self.current()}"
        )

    def parse_cycle(self):
        self.expect("WHILE")
        self.expect("LPAREN", "'('")
        condition = self.parse_expression()
        self.expect("RPAREN", "')'")
        body = self.parse_block()

        return self.node("while", condition=condition, body=body)

    def parse_branch(self):
        self.expect("IF")
        self.expect("LPAREN", "'('")
        condition = self.parse_expression()
        self.expect("RPAREN", "')'")
        then_body = self.parse_block()

        else_body = None
        if self.match("ELSE"):
            else_body = self.parse_block()

        return self.node(
            "if",
            condition=condition,
            body=then_body,
            else_body=else_body,
        )

    def parse_block(self):
        self.expect("LBRACE", "'{'")
        body = []

        while not self.is_current_token_in_tuple("RBRACE", "EOF"):
            body.append(self.parse_body_term())

        self.expect("RBRACE", "'}'")
        return body

    def parse_expression(self, min_precedence=1):
        left = self.parse_unary()

        while True:
            token_type = self.current()[0]
            operator_info = self.BINARY_OPERATORS.get(token_type)

            if operator_info is None:
                break

            operator, precedence = operator_info
            if precedence < min_precedence:
                break

            self.advance()
            right = self.parse_expression(precedence + 1)

            left = self.node(
                "binary",
                operator=operator,
                left=left,
                right=right,
            )

        return left

    def parse_unary(self):
        if self.match("MINUS"):
            return self.node(
                "unary",
                operator="-",
                operand=self.parse_unary(),
            )

        return self.parse_postfix()

    def parse_postfix(self):
        expression = self.parse_primary()

        while self.match("LBRACKET"):
            index = self.parse_expression()
            self.expect("RBRACKET", "']'")

            expression = self.node(
                "index",
                array=expression,
                index=index,
            )

        return expression

    def parse_primary(self):
        token_type, value, line, char = self.current()

        if token_type == "NUMBER":
            self.advance()
            return self.node("number", value=value)

        if token_type == "STRING_LITERAL":
            self.advance()
            return self.node("string", value=value)

        if token_type == "BYTE_LITERAL":
            self.advance()
            return self.node("byte", value=value)

        if token_type == "IDENT":
            if self.peek()[0] == "LPAREN":
                return self.parse_function_call()

            self.advance()
            return self.node("variable", name=value)

        if self.match("LPAREN"):
            expression = self.parse_expression()
            self.expect("RPAREN", "')'")
            return expression

        self.error(f"expected an expression, got {self.current()}")

    def parse_function_call(self):
        name = self.expect("IDENT", "function name")[1]
        self.expect("LPAREN", "'('")
        args = []

        if not self.is_current_token_in_tuple("RPAREN"):
            args.append(self.parse_expression())

            while self.match("COMMA"):
                args.append(self.parse_expression())

        self.expect("RPAREN", "')'")

        return self.node(
            "function_call",
            name=name,
            args=args,
        )
