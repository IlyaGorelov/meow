KEYWORDS = {
    "int": "INT",
    "int128": "INT128",
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
    "setLength": "SET_LENGTH"
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
    ".": "DOT"
}

EOF = "EOF"
COMMENT = "COMMENT"
STRING_LITERAL="STRING_LITERAL"
CHAR_LITERAL ="CHAR_LITERAL"
NUMBER_LITERAL = "NUMBER_LITERAL"
IDENTIFIER = "IDENTIFIER"