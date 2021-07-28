# reminder - A maubot plugin that reacts to messages that match predefined rules.
# Copyright (C) 2021 Tulir Asokan
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
from typing import Callable, List, Dict, Optional, NamedTuple
import re


class SimpleMatch(NamedTuple):
    value: str

    def groups(self) -> List[str]:
        return [self.value]

    def group(self, group: int) -> Optional[str]:
        if group == 0:
            return self.value
        return None

    def groupdict(self) -> Dict[str, str]:
        return {}


def matcher_equals(val: str, pattern: str) -> bool:
    return val == pattern


def matcher_startswith(val: str, pattern: str) -> bool:
    return val.startswith(pattern)


def matcher_endswith(val: str, pattern: str) -> bool:
    return val.endswith(pattern)


def matcher_contains(val: str, pattern: str) -> bool:
    return pattern in val


SimpleMatcherFunc = Callable[[str, str], bool]


class SimplePattern:
    matcher: SimpleMatcherFunc
    pattern: str
    ignorecase: bool

    def __init__(self, matcher: SimpleMatcherFunc, pattern: str, ignorecase: bool) -> None:
        self.matcher = matcher
        self.pattern = pattern
        self.ignorecase = ignorecase

    def search(self, val: str) -> SimpleMatch:
        if self.ignorecase:
            val = val.lower()
        if self.matcher(val, self.pattern):
            return SimpleMatch(self.pattern)

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
            func = matcher_equals
        elif first == '^' and (force_raw or esc == f"\\^{pattern[1:]}"):
            s_pattern = s_pattern[1:]
            func = matcher_startswith
        elif last == '$' and (force_raw or esc == f"{pattern[:-1]}\\$"):
            s_pattern = s_pattern[:-1]
            func = matcher_endswith
        elif force_raw or esc == pattern:
            func = matcher_contains
        else:
            # Not a simple pattern
            return None
        return SimplePattern(matcher=func, pattern=s_pattern, ignorecase=ignorecase)
