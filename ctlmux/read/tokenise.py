class CTLMUX_TokeniseError(Exception):
    pass


class Tokenise:
    def __init__(self, buffer: str):
        self.buffer: str = buffer
        self.cursor: int = 0

    def consume_until(self, char: str) -> tuple[str, bool]:
        """
        Consumes until, but not including, a given `char`.
        Will need to `advance` to consume the `char`

        Returns read buffer, and if eof reached
        """
        if len(char) != 1:
            raise CTLMUX_TokeniseError(f"bad input: {char}. Must be 1 char.")

        sub_buffer = ""
        while not self.eof():
            c = self.buffer[self.cursor]
            if c == char:
                break

            self.cursor += 1
            sub_buffer += c

        return sub_buffer, self.eof()

    def eof(self) -> bool:
        return self.cursor >= len(self.buffer)

    def peek(self) -> str:
        """
        Emit the next character without moving the cursor
        """
        return self.buffer[self.cursor+1]

    def advance(self) -> str:
        """
        Advance the cursor by 1 and emit the character
        """
        c = self.peek()
        self.cursor += 1
        return c

    def find_next(self, char: str) -> int | None:
        """
        Find the next instance of char in buffer, without advancing the real
        cursor

        Return int if found, or None if not
        """
        if len(char) != 1:
            raise CTLMUX_TokeniseError(f"bad input: {char}. Must be 1 char.")

        cpy_cursor = self.cursor

        while not cpy_cursor >= len(self.buffer):
            c = self.buffer[cpy_cursor]

            if c == char:
                return cpy_cursor

            cpy_cursor += 1

        return None

    def peek_count(self, count: int) -> tuple[str, bool]:
        """
        Get the buffer from the current cursor -> count or eof,
        without advancing the cursor

        Return the substring and if eof was reached
        """
        if count <= 0:
            raise CTLMUX_TokeniseError(
                f"bad input: {count}. Must be greater than 0/zero"
            )

        cpy_cursor = self.cursor
        until_pos = cpy_cursor + count
        eof = False

        if until_pos >= len(self.buffer):
            until_pos = len(self.buffer)-1
            eof = True

        return self.buffer[cpy_cursor:until_pos], eof

