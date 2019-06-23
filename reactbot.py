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
from typing import (NewType, Optional, Callable, Pattern, Match, Union, Dict, List, Tuple, Set,
                    Type, Any)
from itertools import chain
import copy
import re

from attr import dataclass
from jinja2 import Template as JinjaTemplate

from mautrix.types import RoomID, EventType, Event
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper

from maubot import Plugin, MessageEvent
from maubot.handlers import event


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("rules")
        helper.copy("templates")
        helper.copy("default_flags")


class ConfigError(Exception):
    pass


class Key(str):
    pass


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


RMatch = Union[Match, BlankMatch]
RPattern = Union[Pattern, SimplePattern]

Index = NewType("Index", Union[str, int, Key])

variable_regex = re.compile(r"\$\${([0-9A-Za-z-_]+)}")


@dataclass
class Template:
    type: EventType
    variables: Dict[str, JinjaTemplate]
    content: Dict[str, Any]

    _variable_locations: List[Tuple[Index, ...]] = None

    def init(self) -> 'Template':
        self._variable_locations = []
        self._map_variable_locations((), self.content)
        return self

    def _map_variable_locations(self, path: Tuple[Index, ...], data: Any) -> None:
        if isinstance(data, list):
            for i, v in enumerate(data):
                self._map_variable_locations((*path, i), v)
        elif isinstance(data, dict):
            for k, v in data.items():
                if variable_regex.match(k):
                    self._variable_locations.append((*path, Key(k)))
                self._map_variable_locations((*path, k), v)
        elif isinstance(data, str):
            if variable_regex.match(data):
                self._variable_locations.append(path)

    @classmethod
    def _recurse(cls, content: Any, path: Tuple[Index, ...]) -> Any:
        if len(path) == 0:
            return content
        return cls._recurse(content[path[0]], path[1:])

    @staticmethod
    def _replace_variables(tpl: str, variables: Dict[str, Any]) -> str:
        for match in variable_regex.finditer(tpl):
            val = variables[match.group(1)]
            tpl = tpl[:match.start()] + val + tpl[match.end():]
        return tpl

    def execute(self, evt: Event, rule_vars: Dict[str, JinjaTemplate], extra_vars: Dict[str, str]
                ) -> Dict[str, Any]:
        variables = {**{name: template.render(event=evt)
                        for name, template in chain(self.variables.items(), rule_vars.items())},
                     **extra_vars}
        content = copy.deepcopy(self.content)
        for path in self._variable_locations:
            data: Dict[str, Any] = self._recurse(content, path[:-1])
            key = path[-1]
            if isinstance(key, Key):
                key = str(key)
                data[self._replace_variables(key, variables)] = data.pop(key)
            else:
                data[key] = self._replace_variables(data[key], variables)
        return content


@dataclass
class Rule:
    rooms: Set[RoomID]
    matches: List[RPattern]
    not_matches: List[RPattern]
    template: Template
    type: Optional[EventType]
    variables: Dict[str, JinjaTemplate]

    def _check_not_match(self, body: str) -> bool:
        for pattern in self.not_matches:
            if pattern.search(body):
                return True
        return False

    def match(self, evt: MessageEvent) -> Optional[Match]:
        if len(self.rooms) > 0 and evt.room_id not in self.rooms:
            return None
        for pattern in self.matches:
            match = pattern.search(evt.content.body)
            if match:
                if self._check_not_match(evt.content.body):
                    return None
                return match
        return None

    async def execute(self, evt: MessageEvent, match: Match) -> None:
        content = self.template.execute(evt=evt, rule_vars=self.variables,
                                        extra_vars={str(i): val for i, val in
                                                    enumerate(match.groups())})
        await evt.client.send_message_event(evt.room_id, self.type or self.template.type, content)


class ReactBot(Plugin):
    rules: Dict[str, Rule]
    templates: Dict[str, Template]
    default_flags: re.RegexFlag

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        await super().start()
        self.rules = {}
        self.templates = {}
        self.on_external_config_update()

    @staticmethod
    def _parse_variables(data: Dict[str, Any]) -> Dict[str, JinjaTemplate]:
        return {name: JinjaTemplate(var_tpl) for name, var_tpl
                in data.get("variables", {}).items()}

    def _make_template(self, name: str, tpl: Dict[str, Any]) -> Template:
        try:
            return Template(type=EventType.find(tpl.get("type", "m.room.message")),
                            variables=self._parse_variables(tpl),
                            content=tpl.get("content", {})).init()
        except Exception as e:
            raise ConfigError(f"Failed to load {name}") from e

    def _get_flags(self, flags: str) -> re.RegexFlag:
        output = self.default_flags
        for flag in flags:
            flag = flag.lower()
            if flag == "i" or flag == "ignorecase":
                output |= re.IGNORECASE
            elif flag == "s" or flag == "dotall":
                output |= re.DOTALL
            elif flag == "x" or flag == "verbose":
                output |= re.VERBOSE
            elif flag == "m" or flag == "multiline":
                output |= re.MULTILINE
            elif flag == "l" or flag == "locale":
                output |= re.LOCALE
            elif flag == "u" or flag == "unicode":
                output |= re.UNICODE
            elif flag == "a" or flag == "ascii":
                output |= re.ASCII
        return output

    def _compile(self, pattern: str) -> RPattern:
        flags = self.default_flags
        raw = False
        if isinstance(pattern, dict):
            flags = self._get_flags(pattern.get("flags", ""))
            pattern = pattern["pattern"]
            raw = pattern.get("raw", False)
        if not flags or flags == re.IGNORECASE:
            ignorecase = flags == re.IGNORECASE
            s_pattern = pattern.lower() if ignorecase else pattern
            esc = ""
            if not raw:
                esc = re.escape(pattern)
            first, last = pattern[0], pattern[-1]
            if first == '^' and last == '$' and (raw or esc == f"\\^{pattern[1:-1]}\\$"):
                s_pattern = s_pattern[1:-1]
                return SimplePattern(lambda val: val == s_pattern, ignorecase=ignorecase)
            elif first == '^' and (raw or esc == f"\\^{pattern[1:]}"):
                s_pattern = s_pattern[1:]
                return SimplePattern(lambda val: val.startswith(s_pattern), ignorecase=ignorecase)
            elif last == '$' and (raw or esc == f"{pattern[:-1]}\\$"):
                s_pattern = s_pattern[:-1]
                return SimplePattern(lambda val: val.endswith(s_pattern), ignorecase=ignorecase)
            elif raw or esc == pattern:
                return SimplePattern(lambda val: s_pattern in val, ignorecase=ignorecase)
        return re.compile(pattern, flags=flags)

    def _compile_all(self, patterns: List[str]) -> List[RPattern]:
        return [self._compile(pattern) for pattern in patterns]

    def _make_rule(self, name: str, rule: Dict[str, Any]) -> Rule:
        try:
            return Rule(rooms=set(rule.get("rooms", [])),
                        matches=self._compile_all(rule["matches"]),
                        not_matches=self._compile_all(rule.get("not_matches", [])),
                        type=EventType.find(rule["type"]) if "type" in rule else None,
                        template=self.templates[rule["template"]],
                        variables=self._parse_variables(rule))
        except Exception as e:
            raise ConfigError(f"Failed to load {name}") from e

    def on_external_config_update(self) -> None:
        self.config.load_and_update()
        try:
            self.default_flags = re.RegexFlag(0)
            self.default_flags = self._get_flags(self.config["default_flags"])
            self.templates = {name: self._make_template(name, tpl)
                              for name, tpl in self.config["templates"].items()}
            self.rules = {name: self._make_rule(name, rule)
                          for name, rule in self.config["rules"].items()}
        except ConfigError:
            self.log.exception("Failed to load config")

    @event.on(EventType.ROOM_MESSAGE)
    async def event_handler(self, evt: MessageEvent) -> None:
        if evt.sender == self.client.mxid:
            return
        for name, rule in self.rules.items():
            match = rule.match(evt)
            if match is not None:
                try:
                    await rule.execute(evt, match)
                except Exception:
                    self.log.exception(f"Failed to execute {name}")
                return
