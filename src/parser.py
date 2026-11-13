# Makes an AST tree of nodes
#
# Node is a dictionary of:
#               -type
#               -line
#               -char
#               -extra fields

from lexer_token_types import *
from parser_node_types import *

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

TYPE_TOKENS = {
    "int": "INT",
    "int128": "INT128",
    "long": "LONG",
    "byte": "BYTE",
    "string": "STRING",
    "bool": "BOOL",
}

ARRAY_TYPES = {
    "int": "INT",
    "long": "LONG",
    "byte": "BYTE",
    "bool": "BOOL",
}

class ParserError(Exception):
    pass


class Parser:
    def __init__(self, tokens):
        self.tokens = list(tokens)

        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def next(self):
        return self.tokens[self.pos + 1]

    def is_current_token_in(self, *types):
        return self.current()["type"] in types

    def error(self, message):
        line = self.current()["line"]
        char = self.current()["char"]
        raise ParserError(f"Line {line}:{char}: {message}")

    def expect(self, token_type, description=None):
        if not self.is_current_token_in(token_type):
            actual_type = self.current()["type"]
            actual_value = self.current()["value"]
            line = self.current()["line"]
            char = self.current()["char"]

            expected = description or token_type
            raise ParserError(
                f"Line {line}:{char}: expected {expected}, "
                f"got {actual_type} ({actual_value!r})"
            )

    def node(self, node_type, **fields):
        return {
            "type": node_type,
            "line": self.tokens[max(0, self.pos - 1)]["line"],
            "char": self.tokens[max(0, self.pos - 1)]["char"],
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

        if self.is_current_token_in(KEYWORDS["continue"]):
            return self.parse_continue()

        if self.is_current_token_in(KEYWORDS["break"]):
            return self.parse_break()

        if self.is_current_token_in(KEYWORDS["const"]):
            return self.parse_const_declaration()

        if self.is_current_token_in(KEYWORDS["while"]):
            return self.parse_cycle()

        if self.is_current_token_in(KEYWORDS["if"]):
            return self.parse_branch()

        if self.is_current_token_in(KEYWORDS["return"]):
            return self.parse_return()

        if self.is_current_token_in(KEYWORDS["meow"]):
            return self.parse_output()
        
        if (
            self.is_current_token_in(TYPE_TOKENS["int128"])
            and self.next()["type"] == PUNCTUATION["."]
        ):
            self.pos += 1
            self.pos += 1
            return self.parse_int128_static_func()

        if self.is_current_token_in(*TYPE_TOKENS.values()):
            return self.parse_declaration_or_function()

        if self.is_current_token_in(KEYWORDS["void"]):
            return self.parse_function()

        if self.is_current_token_in(IDENTIFIER):
            if self.next()["type"] == PUNCTUATION["("]:
                return self.parse_call_statement()
            return self.parse_assignment()

        self.error(f"unexpected token {self.current()}")
        
    def parse_comment(self):
        _, value, _, _ = self.current()
        self.pos+=1
        return self.node(COMMENT_NODE, value=value)
    
    def parse_continue(self):
        self.pos+=1
        self.expect(PUNCTUATION[";"], "';'")
        self.pos+=1
        return self.node(CONTINUE_NODE)
    
    def parse_break(self):
        self.pos+=1
        self.expect(PUNCTUATION[";"], "';'")
        self.pos+=1
        return self.node(BREAK_NODE)
            
    def parse_const_declaration(self):
        self.pos+=1
        declaration = self.parse_var_declaration()

        return self.node(
            CONST_DECLARATION,
            var_type=declaration["var_type"],
            name=declaration["name"],
            value=declaration["value"],
        )
        
    def parse_var_declaration(self):
        var_type = self.parse_type()
        self.expect(IDENTIFIER)
        name = self.current()["value"]
        self.pos+=1
        self.expect("ASSIGN", "'='")
        self.pos+=1
        value = self.parse_initializer()
        self.expect("SEMICOLON","';'")
        self.pos+=1

        return self.node(
            VAR_DECLARATION,
            var_type=var_type,
            name=name,
            value=value,
        )

    def parse_type(self, allow_void=False):
        if allow_void and self.is_current_token_in(KEYWORDS["void"]):
            self.pos+=1
            return "void"

        token_type = self.current()["type"]

        if token_type not in TYPE_TOKENS.values():
            self.error(f"expected a type, got {self.current()}")

        self.pos+=1

        if self.is_current_token_in(PUNCTUATION["["]):
            if token_type not in ARRAY_TYPES.values():
                self.error(f"arrays of {token_type} are not allowed yet")
            self.pos+=1
            
            self.expect(PUNCTUATION["]"], "']' in array type")
            self.pos+=1
            return str(token_type).lower() + "[]"

        return str(token_type).lower()
    
    def parse_initializer(self):
        if self.is_current_token_in(KEYWORDS["new"]):
            return self.parse_array_creation()
        
        if self.is_current_token_in(PUNCTUATION["{"]):
            return self.parse_array_creation_with_elements()

        return self.parse_expression()
    
    def parse_array_creation(self):
        self.pos+=1
        element_type = self.parse_array_element_type()
        self.expect("LBRACKET", "'['")
        self.pos+=1
        size = self.parse_expression()
        self.expect("RBRACKET", "']'")
        self.pos+=1

        return self.node(
            ARRAY_CREATION,
            element_type=element_type,
            size=size,
        )
        
    def parse_array_creation_with_elements(self):
            self.pos+=1
            elements = []
            
            elements.append(self.parse_expression())
            
            while self.current()["type"] == PUNCTUATION[","]:
                self.pos+=1
                elements.append(self.parse_expression())
                
            self.expect(PUNCTUATION["}"])
            self.pos+=1
    
            return self.node(
                ARRAY_CREATION_WITH_ELEMENTS,
                elements = elements
            )

    def parse_array_element_type(self):
        token_type = self.current()["type"]

        if token_type not in ARRAY_TYPES.values():
            self.error(
                "array creation requires int, long, byte or bool; "
                f"got {self.current()}"
            )
            
        self.pos+=1

        return str(token_type).lower()
    
    def parse_expression(self, min_precedence=1):
        left = self.parse_unary()

        while True:
            token_type = self.current()['type']
            operator_info = BINARY_OPERATORS.get(token_type)

            if operator_info is None:
                break

            operator, precedence = operator_info
            if precedence < min_precedence:
                break

            self.pos+=1
            right = self.parse_expression(precedence + 1)

            left = self.node(
                BINARY,
                operator=operator,
                left=left,
                right=right,
            )

        return left
    
    def parse_unary(self):
        if self.is_current_token_in(OPERATORS["-"]):
            self.pos+=1
            return self.node(
                UNARY,
                operator="-",
                operand=self.parse_unary(),
            )

        return self.parse_postfix()
    
    def parse_postfix(self):
        expression = self.parse_primary()

        while self.is_current_token_in(PUNCTUATION["["]):
            self.pos+=1
            index = self.parse_expression()
            self.expect("RBRACKET", "']'")
            self.pos+=1

            expression = self.node(
                "index",
                array=expression,
                index=index,
            )

        return expression
    
    def parse_primary(self):
        token_type = self.current()["type"]
        value = self.current()["value"]

        if token_type == NUMBER_LITERAL:
            self.pos+=1
            number = int(value, 0)
            if number > 2_147_483_647 or number < -2_147_483_648:
                return self.node(LONG, value=number)
            return self.node(INT, value=number)

        if token_type == STRING_LITERAL:
            self.pos+=1
            return self.node(STRING, value=value)

        if token_type == CHAR_LITERAL:
            self.pos+=1
            return self.node(BYTE, value=value)
        
        if token_type == KEYWORDS["hear"]:
            return self.parse_input_call()

        if token_type == "BOOL_LITERAL":
            self.pos+=1
            return self.node(BOOL, value=value)

        if token_type == IDENTIFIER:
            if self.next()["type"] == PUNCTUATION["("]:
                return self.parse_function_call()

            self.pos+=1
            return self.node(VARIABLE, name=value)

        if self.is_current_token_in(PUNCTUATION["("]):
            self.pos+=1
            expression = self.parse_expression()
            self.expect("RPAREN", "')'")
            self.pos+=1
            return expression
    
    def parse_function_call(self):
        self.expect(IDENTIFIER, "function name")
        name = self.current()["value"]
        self.pos+=1
        self.expect("LPAREN", "'('")
        self.pos+=1
        args = []

        if not self.is_current_token_in(PUNCTUATION[")"]):
            args.append(self.parse_expression())
            self.pos+=1

            while self.is_current_token_in(PUNCTUATION[","]):
                args.append(self.parse_expression())
                self.pos+=1

        self.expect("RPAREN", "')'")
        self.pos+=1

        return self.node(
            FUNCTION_CALL,
            name=name,
            args=args,
        )
        
    def parse_cycle(self):
        self.expect(KEYWORDS["while"])
        self.pos+=1
        self.expect("LPAREN", "'('")
        self.pos+=1
        condition = self.parse_expression()
        self.expect("RPAREN", "')'")
        self.pos+=1
        body = self.parse_block()

        return self.node(WHILE_NODE, condition=condition, body=body)
    
    def parse_block(self):
        self.expect("LBRACE", "'{'")
        self.pos+=1
        body = []

        while not self.is_current_token_in("RBRACE", "EOF"):
            body.append(self.parse_body_term())

        self.expect("RBRACE", "'}'")
        self.pos+=1
        return body
    
    def parse_body_term(self):
        if self.is_current_token_in(COMMENT):
            return self.parse_comment()
        if self.is_current_token_in(KEYWORDS["const"]):
            return self.parse_const_declaration()
        if self.is_current_token_in(KEYWORDS["while"]):
            return self.parse_cycle()
        if self.is_current_token_in(KEYWORDS["if"]):
            return self.parse_branch()
        if self.is_current_token_in(KEYWORDS["continue"]):
            return self.parse_continue()
        if self.is_current_token_in(KEYWORDS["break"]):
            return self.parse_break()
        if self.is_current_token_in(KEYWORDS["return"]):
            return self.parse_return()
        if self.is_current_token_in(KEYWORDS["meow"]):
            return self.parse_output()
        
        if (
            self.is_current_token_in(TYPE_TOKENS["int128"])
            and self.next()["type"] == PUNCTUATION["."]
        ):
            self.pos += 1
            self.pos += 1
            return self.parse_int128_static_func()
        
        if self.is_current_token_in(*TYPE_TOKENS.values()):
            return self.parse_var_declaration()
        if self.is_current_token_in(IDENTIFIER):
            if self.next()["type"] == "LPAREN":
                return self.parse_call_statement()
            return self.parse_assignment()

        self.error(
            f"unexpected token in function body: {self.current()}"
        )
        
    def parse_branch(self):
        self.expect("IF")
        self.pos+=1
        self.expect("LPAREN", "'('")
        self.pos+=1
        condition = self.parse_expression()
        self.expect("RPAREN", "')'")
        self.pos+=1
        then_body = self.parse_block()
        else_body = None
        if self.is_current_token_in(KEYWORDS['else']):
            self.pos+=1
            else_body = self.parse_block()

        return self.node(
            IF_NODE,
            condition=condition,
            body=then_body,
            else_body=else_body,
        )
        
    def parse_return(self):
        self.expect("RETURN")
        self.pos+=1

        value = None
        if not self.is_current_token_in("SEMICOLON"):
            value = self.parse_expression()

        self.expect("SEMICOLON", "';'")
        self.pos+=1
        return self.node(RETURN_NODE, value=value)
    
    def parse_output(self):
        self.pos+=1
        self.expect("LPAREN", "'('")
        self.pos+=1

        value = self.parse_expression()

        self.expect("RPAREN", "')'")
        self.pos+=1
        self.expect(PUNCTUATION[";"], "';'")
        self.pos+=1
        return self.node(OUTPUT, value=value)

    def parse_declaration_or_function(self):
        start = self.pos
        declared_type = self.parse_type()

        if self.is_current_token_in(IDENTIFIER) and self.next()["type"] == PUNCTUATION["("]:
            self.expect(IDENTIFIER, "function name")
            name = self.current()["value"]
            return self.parse_function_after_name(declared_type, name)

        self.pos = start        
        return self.parse_var_declaration()

    def parse_function_after_name(self, return_type, name):
        self.expect("LPAREN", "'('")
        self.pos+=1
        parameters = []

        if not self.is_current_token_in("RPAREN"):
            parameters.append(self.parse_parameter())

            while self.is_current_token_in(PUNCTUATION[","]):
                self.pos+=1
                parameters.append(self.parse_parameter())

        self.expect("RPAREN", "')'")
        self.pos+=1
        self.expect("LBRACE", "'{'")
        self.pos+=1

        body = []
        while not self.is_current_token_in("RBRACE", "EOF"):
            body.append(self.parse_body_term())

        self.expect("RBRACE", "'}'")
        self.pos+=1

        return self.node(
            "function",
            return_type=return_type,
            name=name,
            params=parameters,
            body=body,
        )
        
    def parse_parameter(self):
        param_type = self.parse_type()
        self.expect(IDENTIFIER, "parameter name")
        name  = self.current()["value"]
        self.pos+=1

        return self.node(
            PARAMETER,
            param_type=param_type,
            name=name,
        )
        
    def parse_function(self):
        return_type = self.parse_type(allow_void=True)
        self.expect(IDENTIFIER, "function name")
        name  = self.current()["value"]
        self.pos+=1
        return self.parse_function_after_name(return_type, name)
    
    def parse_assignment(self):
        target = self.parse_lvalue()
        self.expect("ASSIGN", "'='")
        self.pos+=1
        value = self.parse_initializer()
        self.expect("SEMICOLON", "';'")
        self.pos+=1

        return self.node(
            ASSIGNMENT,
            target=target,
            value=value,
        )

    def parse_lvalue(self):
        self.expect(IDENTIFIER, "variable name")
        name = self.current()["value"]
        self.pos+=1
        target = self.node(VARIABLE, name=name)

        if self.is_current_token_in("LBRACKET"):
            self.pos+=1
            index = self.parse_expression()
            self.expect("RBRACKET", "']'")
            self.pos+=1
            target = self.node(INDEX, array=target, index=index)

        return target
    
    def parse_call_statement(self):
        call = self.parse_function_call()
        self.expect("SEMICOLON", "';'")
        self.pos+=1
        return self.node(CALL_STATEMENT, call=call)

    def parse_input_call(self):
        self.pos+=1
        self.expect("LPAREN", "'('")
        self.pos+=1
        self.expect("RPAREN", "')'")
        self.pos+=1

        return self.node(INPUT)
    
    def parse_int128_static_func(self):
        if self.is_current_token_in(KEYWORDS["setLength"]):
            self.pos+=1
            self.expect(PUNCTUATION["("])
            self.pos+=1
            value = self.parse_expression()
            self.expect(PUNCTUATION[")"])
            self.pos+=1
            
            self.expect(PUNCTUATION[";"])
            self.pos += 1
            
            return self.node(VECTOR_SET_LENGTH, value = value)
        
    
