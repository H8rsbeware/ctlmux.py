class CTLMUX_TokeniseError(Exception):
    pass


class Tokenise:
    def __init__(self, buffer: str):
        self.buffer: str = buffer
        self.cursor: int = 0
        self._debug: bool = False
    
    def _dprint(self, s: str):
        if self._debug:
            print(s)
    
    def consume_until(self, char: str) -> tuple[str, bool]:
        """
        Consumes until, but not including, a given `char`.
        Will need to `advance` to consume the `char`

        Returns read buffer, and if eof reached
        """
        if len(char) != 1:
            self._dprint(f"bad input: {char}")
            raise CTLMUX_TokeniseError(f"bad input: {char}. Must be 1 char.")

        _start_cursor = self.cursor
        sub_buffer = ""
        while not self.eof():
            c = self.buffer[self.cursor]
            if c == char:
                break

            self.cursor += 1
            sub_buffer += c

        self._dprint(f"{sub_buffer} [{_start_cursor}->{self.cursor}] (searching for: {char})")
        return sub_buffer, self.eof()

    def eof(self) -> bool:
        eof_v = self.cursor >= len(self.buffer)
        # self._dprint(f"eof = {eof_v}")
        return eof_v 

    def peek(self) -> tuple[str, bool]:
        """
        Emit the next character without moving the cursor
        """
        if self.eof():
            return '', True

        peek_v = self.buffer[self.cursor]
        self._dprint(f"peeked: {peek_v}")
        return peek_v, False

    def peek_rel(self, offset: int) -> str:
        peek_v = self.buffer[self.cursor+offset]
        self._dprint(f"rel peeked {offset}, saw {peek_v}")
        return peek_v

    def advance(self) -> tuple[str, bool]:
        """
        Advance the cursor by 1 and emit the character
        """
        c, eof = self.peek()
        self.cursor += 1
        self._dprint(f"advanced over {c}, to {self.cursor}")
        return c, eof

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
                self._dprint(f"found {char}, at {cpy_cursor} from {self.cursor}")
                return cpy_cursor

            cpy_cursor += 1

        self._dprint(f"didnt find {char} in {self.buffer[self.cursor:]} -> {cpy_cursor}")
        return None

    def peek_count(self, count: int) -> tuple[str, bool]:
        """
        Get the buffer from the current cursor -> count or eof,
        without advancing the cursor

        Return the substring and if eof was reached
        """
        if count <= 0:
            self._dprint(f"bad input: {count}")
            raise CTLMUX_TokeniseError(
                f"bad input: {count}. Must be greater than 0/zero"
            )
        
        cpy_cursor = self.cursor
        until_pos = cpy_cursor + count
        eof = False

        if until_pos >= len(self.buffer):
            until_pos = len(self.buffer)-1
            eof = True
        
        self._dprint(f"peeked {count} ahead, found {self.buffer[cpy_cursor:until_pos]}, eof = {eof}")
        return self.buffer[cpy_cursor:until_pos], eof

