# reminder - A maubot plugin that reacts to messages that match predefined rules.
# Copyright (C) 2019 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from typing import Callable, List, Optional
import re


class BlankMatch:
    @staticmethod
    def groups() -> List[str]:
        return []


class SimplePattern:
    _ptm = BlankMatch()

    matcher: Callable[[str], bool]
    ignorecase: bool

    def __init__(self, matcher: Callable[[str], bool], ignorecase: bool) -> None:
        self.matcher = matcher
        self.ignorecase = ignorecase

    def search(self, val: str) -> BlankMatch:
        if self.ignorecase:
            val = val.lower()
        if self.matcher(val):
            return self._ptm

    @staticmethod
    def compile(pattern: str, flags: re.RegexFlag = re.RegexFlag(0), force_raw: bool = False
                ) -> Optional['SimplePattern']:
        ignorecase = flags == re.IGNORECASE
        s_pattern = pattern.lower() if ignorecase else pattern
        esc = ""
        if not force_raw:
            esc = re.escape(pattern)
        first, last = pattern[0], pattern[-1]
        if first == '^' and last == '$' and (force_raw or esc == f"\\^{pattern[1:-1]}\\$"):
            s_pattern = s_pattern[1:-1]
            return SimplePattern(lambda val: val == s_pattern, ignorecase=ignorecase)
        elif first == '^' and (force_raw or esc == f"\\^{pattern[1:]}"):
            s_pattern = s_pattern[1:]
            return SimplePattern(lambda val: val.startswith(s_pattern), ignorecase=ignorecase)
        elif last == '$' and (force_raw or esc == f"{pattern[:-1]}\\$"):
            s_pattern = s_pattern[:-1]
            return SimplePattern(lambda val: val.endswith(s_pattern), ignorecase=ignorecase)
        elif force_raw or esc == pattern:
            return SimplePattern(lambda val: s_pattern in val, ignorecase=ignorecase)
        return None
