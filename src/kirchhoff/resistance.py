from kirchhoff.units import parse_value


class ResistanceParser:
    def __init__(self, expression: str):
        self.expression = expression
        self.tokens = self._tokenize(expression)
        self.pos = 0

    def parse(self) -> float:
        result = self._parse_series()

        if self._current() is not None:
            raise ValueError(f"Unexpected token: {self._current()!r}")

        return result

    def _parse_series(self) -> float:
        value = self._parse_parallel()

        while self._current() == "+":
            self._consume("+")
            value += self._parse_parallel()

        return value

    def _parse_parallel(self) -> float:
        values = [self._parse_factor()]

        while self._current() == "||":
            self._consume("||")
            values.append(self._parse_factor())

        if len(values) == 1:
            return values[0]

        inverse_sum = sum(1 / value for value in values)

        if inverse_sum == 0:
            raise ValueError("Invalid parallel resistance expression.")

        return 1 / inverse_sum

    def _parse_factor(self) -> float:
        token = self._current()

        if token is None:
            raise ValueError("Unexpected end of expression.")

        if token == "(":
            self._consume("(")
            value = self._parse_series()
            self._consume(")")
            return value

        self.pos += 1
        return parse_value(token, "ohm")

    def _current(self) -> str | None:
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def _consume(self, expected: str) -> None:
        token = self._current()

        if token != expected:
            raise ValueError(f"Expected {expected!r}, got {token!r}")

        self.pos += 1

    @staticmethod
    def _tokenize(expression: str) -> list[str]:
        tokens = []
        i = 0

        while i < len(expression):
            char = expression[i]

            if char.isspace():
                i += 1
                continue

            if expression.startswith("||", i):
                tokens.append("||")
                i += 2
                continue

            if char in "+()":
                tokens.append(char)
                i += 1
                continue

            start = i
            while i < len(expression):
                if expression.startswith("||", i):
                    break
                if expression[i].isspace() or expression[i] in "+()":
                    break
                i += 1

            tokens.append(expression[start:i])

        return tokens


def equivalent_resistance(expression: str) -> float:
    return ResistanceParser(expression).parse()