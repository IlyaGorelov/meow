# Makes an AST tree of nodes
#
# Node is a dictionary of: 
#               -type 
#               -line 
#               -char 
#               -extra fields

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

TYPE_TOKENS = {
        "INT": "int",
        "LONG": "long",
        "BYTE": "byte",
        "STRING": "string",
        "BOOL": "bool",
    }

ARRAY_TYPE_TOKENS = {"INT", "LONG", "BYTE", "BOOL"}

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

PUNCTUATION = {
    "(": "LPAREN",
    ")": "RPAREN",
    "{": "LBRACE",
    "}": "RBRACE",
    "[": "LBRACKET",
    "]": "RBRACKET",
    ",": "COMMA",
    ";": "SEMICOLON",
}

EOF = "EOF"
COMMENT = "COMMENT"
STRING_LITERAL="STRING_LITERAL"
CHAR_LITERAL ="CHAR_LITERAL"
NUMBER_LITERAL = "NUMBER_LITERAL"
BOOL_LITERAL = "BOOL_LITERAL"
IDENTIFIER = "IDENTIFIER"
CONST="CONST"
WHILE="WHILE"
IF="IF"
CONTINUE="CONTINUE"
BREAK="BREAK"
RETURN="RETURN"
MEOW="MEOW"
VOID="VOID"
HEAR="HEAR"
NEW="NEW"

class ParserError(Exception):
    pass

class Parser:
    def __init__(self, tokens):
        self.tokens = list(tokens)

        if not self.tokens or self.tokens[-1][0] != EOF:
            token = self.tokens[-1] if self.tokens else (None, None, 1, 0)
            self.tokens.append((EOF, None, token[2], token[3]))

        self.pos = 0

    def current(self):
        if self.pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[self.pos]

    def peek(self, offset=1):
        # by default: peeks next token
        index = self.pos + offset
        if index >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[index]

    def is_current_token_in(self, *types):
        return self.current()[0] in types

    def advance(self):
        token = self.current()
        if token[0] != EOF:
            self.pos += 1
        return token

    def match(self, *types):
        if self.is_current_token_in(*types):
            return self.advance()
        return None

    def error(self, message):
        line = self.current()[2]
        char = self.current()[3]
        raise ParserError(f"Line {line}:{char}: {message}")

    def expect(self, token_type, description=None):
        if not self.is_current_token_in(token_type):
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

        while not self.is_current_token_in(EOF):
            body.append(self.parse_token())

        return self.node(PROGRAM, body=body)

    def parse_token(self):
        if self.is_current_token_in(COMMENT):
            return self.parse_comment()

        if self.is_current_token_in(CONTINUE):
                    return self.parse_continue()
        
        if self.is_current_token_in(BREAK):
            return self.parse_break()

        if self.is_current_token_in(CONST):
            return self.parse_const_declaration()

        if self.is_current_token_in(WHILE):
            return self.parse_cycle()

        if self.is_current_token_in(IF):
            return self.parse_branch()


        if self.is_current_token_in(RETURN):
            return self.parse_return()

        if self.is_current_token_in(MEOW):
            return self.parse_output()

        if self.is_current_token_in(*TYPE_TOKENS.keys()):
            return self.parse_declaration_or_function()

        if self.is_current_token_in(VOID):
            return self.parse_function()

        if self.is_current_token_in(IDENTIFIER):
            if self.peek()[0] == PUNCTUATION["("]:
                return self.parse_call_statement()
            return self.parse_assignment()

        self.error(f"unexpected token {self.current()}")
    
    def parse_type(self, allow_void=False):
        if allow_void and self.match(VOID):
            return "void"

        token_type = self.current()[0]

        if token_type not in TYPE_TOKENS:
            self.error(f"expected a type, got {self.current()}")

        base_type = TYPE_TOKENS[self.advance()[0]]

        if self.match(PUNCTUATION["["]):
            if base_type not in {"int", "long", "byte", "bool"}:
                self.error(f"arrays of {base_type} are not allowed yet")

            self.expect(PUNCTUATION["]"], "']' in array type")

            if self.is_current_token_in(PUNCTUATION["["]):
                self.error("nested arrays are not allowed yet")

            return base_type + "[]"

        return base_type

    def parse_array_element_type(self):
        token_type = self.current()[0]

        if token_type not in ARRAY_TYPE_TOKENS:
            self.error(
                "array creation requires int, long, byte or bool; "
                f"got {self.current()}"
            )

        return TYPE_TOKENS[self.advance()[0]]

    def parse_declaration_or_function(self):
        start = self.pos
        declared_type = self.parse_type()

        if self.is_current_token_in(IDENTIFIER) and self.peek()[0] == PUNCTUATION["("]:
            name = self.expect(IDENTIFIER, "function name")[1]
            return self.parse_function_after_name(declared_type, name)

        self.pos = start
        return self.parse_var_declaration()

    def parse_var_declaration(self):
        var_type = self.parse_type()
        name = self.expect(IDENTIFIER, "variable name")[1]
        self.expect("ASSIGN", "'='")
        value = self.parse_initializer()
        self.expect("SEMICOLON", "';'")

        return self.node(
            VAR_DECLARATION,
            var_type=var_type,
            name=name,
            value=value,
        )

    def parse_const_declaration(self):
        self.advance()
        declaration = self.parse_var_declaration()

        return self.node(
            CONST_DECLARATION,
            var_type=declaration["var_type"],
            name=declaration["name"],
            value=declaration["value"],
        )

    def parse_initializer(self):
        if self.is_current_token_in(HEAR):
            return self.parse_input_call()

        if self.is_current_token_in(NEW):
            return self.parse_array_creation()

        return self.parse_expression()

    def parse_assignment(self):
        target = self.parse_lvalue()
        self.expect("ASSIGN", "'='")
        value = self.parse_initializer()
        self.expect("SEMICOLON", "';'")

        return self.node(
            ASSIGNMENT,
            target=target,
            value=value,
        )

    def parse_lvalue(self):
        name = self.expect(IDENTIFIER, "variable name")[1]
        target = self.node(VARIABLE, name=name)

        if self.match("LBRACKET"):
            index = self.parse_expression()
            self.expect("RBRACKET", "']'")
            target = self.node(INDEX, array=target, index=index)

        return target

    def parse_input_call(self):
        token_type = self.advance()[0]
        self.expect("LPAREN", "'('")
        self.expect("RPAREN", "')'")

        return self.node(INPUT)

    def parse_array_creation(self):
        self.expect("NEW")
        element_type = self.parse_array_element_type()
        self.expect("LBRACKET", "'['")
        size = self.parse_expression()
        self.expect("RBRACKET", "']'")

        return self.node(
            ARRAY_CREATION,
            element_type=element_type,
            size=size,
        )

    def parse_call_statement(self):
        call = self.parse_function_call()
        self.expect("SEMICOLON", "';'")
        return self.node(CALL_STATEMENT, call=call)

    def parse_output(self):
        self.expect("MEOW")
        self.expect("LPAREN", "'('")

        if self.is_current_token_in(STRING_LITERAL, CHAR_LITERAL):
            value = self.parse_primary()
        else:
            value = self.parse_expression()

        self.expect("RPAREN", "')'")
        self.expect("SEMICOLON", "';'")

        return self.node(OUTPUT, value=value)

    def parse_continue(self):
        self.expect("CONTINUE")
        self.expect("SEMICOLON", "';'")
        return self.node(CONTINUE_NODE)

    def parse_break(self):
        self.expect("BREAK")
        self.expect("SEMICOLON", "';'")
        return self.node(BREAK_NODE)

    def parse_return(self):
        self.expect("RETURN")

        value = None
        if not self.is_current_token_in("SEMICOLON"):
            value = self.parse_expression()

        self.expect("SEMICOLON", "';'")
        return self.node(RETURN_NODE, value=value)

    def parse_comment(self):
        _, value, _, _ = self.advance()
        return self.node(COMMENT_NODE, value=value)

    def parse_function(self):
        return_type = self.parse_type(allow_void=True)
        name = self.expect(IDENTIFIER, "function name")[1]
        return self.parse_function_after_name(return_type, name)

    def parse_function_after_name(self, return_type, name):
        self.expect("LPAREN", "'('")
        parameters = []

        if not self.is_current_token_in("RPAREN"):
            parameters.append(self.parse_parameter())

            while self.match("COMMA"):
                parameters.append(self.parse_parameter())

        self.expect("RPAREN", "')'")
        self.expect("LBRACE", "'{'")

        body = []
        while not self.is_current_token_in("RBRACE", "EOF"):
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
        name = self.expect(IDENTIFIER, "parameter name")[1]

        return self.node(
            PARAMETER,
            param_type=param_type,
            name=name,
        )

    def parse_body_term(self):
        if self.is_current_token_in("COMMENT"):
            return self.parse_comment()
        if self.is_current_token_in("CONST"):
            return self.parse_const_declaration()
        if self.is_current_token_in("WHILE"):
            return self.parse_cycle()
        if self.is_current_token_in("IF"):
            return self.parse_branch()
        if self.is_current_token_in("CONTINUE"):
            return self.parse_continue()
        if self.is_current_token_in("BREAK"):
            return self.parse_break()
        if self.is_current_token_in("RETURN"):
            return self.parse_return()
        if self.is_current_token_in("MEOW"):
            return self.parse_output()
        if self.is_current_token_in(*TYPE_TOKENS.keys()):
            return self.parse_var_declaration()
        if self.is_current_token_in(IDENTIFIER):
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

        return self.node(WHILE_NODE, condition=condition, body=body)

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
            IF_NODE,
            condition=condition,
            body=then_body,
            else_body=else_body,
        )

    def parse_block(self):
        self.expect("LBRACE", "'{'")
        body = []

        while not self.is_current_token_in("RBRACE", "EOF"):
            body.append(self.parse_body_term())

        self.expect("RBRACE", "'}'")
        return body

    def parse_expression(self, min_precedence=1):
        left = self.parse_unary()

        while True:
            token_type = self.current()[0]
            operator_info = BINARY_OPERATORS.get(token_type)

            if operator_info is None:
                break

            operator, precedence = operator_info
            if precedence < min_precedence:
                break

            self.advance()
            right = self.parse_expression(precedence + 1)

            left = self.node(
                BINARY,
                operator=operator,
                left=left,
                right=right,
            )

        return left

    def parse_unary(self):
        if self.match("MINUS"):
            return self.node(
                UNARY,
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

        if token_type == NUMBER_LITERAL:
            self.advance()

            number = int(value)
            if number>2_147_483_647 or number<-2_147_483_648:
                return self.node(LONG, value=number)
            return self.node(INT, value=number)

        if token_type == STRING_LITERAL:
            self.advance()
            return self.node(STRING, value=value)

        if token_type == CHAR_LITERAL:
            self.advance()
            return self.node(BYTE, value=value)

        if token_type == BOOL_LITERAL:
            self.advance()
            return self.node(BOOL, value=value)

        if token_type == IDENTIFIER:
            if self.peek()[0] == PUNCTUATION["("]:
                return self.parse_function_call()

            self.advance()
            return self.node("variable", name=value)

        if self.match(PUNCTUATION["("]):
            expression = self.parse_expression()
            self.expect("RPAREN", "')'")
            return expression

        self.error(f"expected an expression, got {self.current()}")

    def parse_function_call(self):
        name = self.expect(IDENTIFIER, "function name")[1]
        self.expect("LPAREN", "'('")
        args = []

        if not self.is_current_token_in("RPAREN"):
            args.append(self.parse_expression())

            while self.match("COMMA"):
                args.append(self.parse_expression())

        self.expect("RPAREN", "')'")

        return self.node(
            FUNCTION_CALL,
            name=name,
            args=args,
        )
