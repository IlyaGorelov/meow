# Transform meow-file into a list of tokens below
# 
# Token is a tuple of:
#       -type, 
#       -value, 
#       -line number,
#       -character number in this line

KEYWORDS = {
    "int": "INT",
    "long": "LONG",
    "byte": "BYTE",
    "string": "STRING",
    "bool": "BOOL",
    "true": "BOOL_LITERAL",
    "false": "BOOL_LITERAL",
    "void": "VOID",
    "const": "CONST",
    "while": "WHILE",
    "if": "IF",
    "else": "ELSE",
    "new": "NEW",
    "hear": "HEAR",
    "meow": "MEOW",
    "continue": "CONTINUE",
    "break": "BREAK",
    "return": "RETURN",
}

OPERATORS = {
    "||": "LOGICAL_OR",
    "&&": "LOGICAL_AND",
    "==": "EQUAL",
    "!=": "NOT_EQUAL",
    "<=": "LESS_EQUAL",
    ">=": "GREATER_EQUAL",
    "=": "ASSIGN",
    "|": "BITWISE_OR",
    "&": "BITWISE_AND",
    "<": "LESS",
    ">": "GREATER",
    "+": "PLUS",
    "-": "MINUS",
    "*": "MULTIPLY",
    "/": "DIVIDE",
    "%": "MODULO",
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

# some extra tokens:
EOF = "EOF"
COMMENT = "COMMENT"
STRING_LITERAL="STRING_LITERAL"
CHAR_LITERAL ="CHAR_LITERAL"
NUMBER_LITERAL = "NUMBER_LITERAL"
IDENTIFIER = "IDENTIFIER"

class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.line = 1
        self.pos_in_line=0
        self.tokens = []

    def add_token(self, token_type, value):
        self.tokens.append((token_type, 
                            value, 
                            self.line,
                            self.pos_in_line-1))

    def tokenize(self):
        while self.pos < len(self.source):
            char = self.source[self.pos]

            if char.isspace():
                if char == "\n":
                    self.line += 1
                    self.pos_in_line=0
                else:
                    self.pos_in_line +=1 
                    
                self.pos += 1
                continue

            if char == '#':
                self.read_comment()
                continue

            if char == '"':
                self.read_string()
                continue

            if char == "'":
                self.read_char()
                continue

            if char.isdigit():
                self.read_number()
                continue

            if char.isalpha() or char == "_":
                self.read_identifier()
                continue

            operator = self.try_get_operator()

            if operator is not None:
                self.add_token(OPERATORS[operator], operator)
                self.pos += len(operator)
                self.pos_in_line += len(operator)
                continue

            if char in PUNCTUATION:
                self.add_token(PUNCTUATION[char], char)
                self.pos += 1
                self.pos_in_line += 1
                continue

            print(self.pos_in_line, self.pos)

            raise SyntaxError(
                f"Unknown character {char!r} at line {self.line}:{self.pos_in_line}"
            )

        self.add_token(EOF, None)
        return self.tokens

    def read_comment(self):
        start = self.pos

        while (
            self.pos < len(self.source)
            and self.source[self.pos] != "\n"
        ):
            self.pos += 1
            self.pos_in_line += 1

        self.add_token(
            COMMENT,
            self.source[start:self.pos]
        )

    def read_string(self):
        self.pos += 1
        self.pos_in_line += 1
        start = self.pos

        while self.pos < len(self.source):
            char = self.source[self.pos]

            if char == '"':
                value = self.source[start:self.pos]
                self.pos += 1
                self.pos_in_line += 1
                self.add_token(STRING_LITERAL, value)
                return

            if char == "\n":
                raise SyntaxError(
                    f"Unterminated string at line {self.line}:{self.pos_in_line}"
                )

            self.pos += 1
            self.pos_in_line += 1

        raise SyntaxError(
            f"Unterminated string at line {self.line}:{self.pos_in_line}"
        )

    def read_char(self):
        self.pos += 1
        self.pos_in_line += 1

        if self.pos >= len(self.source):
            raise SyntaxError(
                f"Unterminated character literal at line {self.line}:{self.pos_in_line}"
            )

        char = self.source[self.pos]

        if char in ("'", "\n"):
            raise SyntaxError(
                f"Invalid character literal at line {self.line}:{self.pos_in_line}:{self.pos}"
            )

        self.pos += 1
        self.pos_in_line+=1

        if (
            self.pos >= len(self.source)
            or self.source[self.pos] != "'"
        ):
            raise SyntaxError(
                f"Character literal must contain exactly one "
                f"character at line {self.line}:{self.pos_in_line}"
            )

        self.pos += 1
        self.pos_in_line+=1
        self.add_token(CHAR_LITERAL, char)

    def read_number(self):
        start = self.pos

        while (
            self.pos < len(self.source)
            and self.source[self.pos].isdigit()
        ):
            self.pos += 1
            self.pos_in_line+=1

        self.add_token(
            NUMBER_LITERAL,
            self.source[start:self.pos]
        )

    def read_identifier(self):
        start = self.pos

        while self.pos < len(self.source):
            char = self.source[self.pos]

            if char.isalnum() or char == "_":
                self.pos += 1
                self.pos_in_line+=1
            else:
                break

        value = self.source[start:self.pos]
        token_type = KEYWORDS.get(value, IDENTIFIER)

        self.add_token(token_type, value)

    def try_get_operator(self):
        operator = None
        for op in sorted(OPERATORS, key=len, reverse=True):
            if self.source.startswith(op, self.pos):
                operator = op
                break

        return operator
