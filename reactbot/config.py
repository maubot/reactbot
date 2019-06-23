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
from typing import List, Union, Dict, Any
import re

from jinja2 import Template as JinjaTemplate

from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from mautrix.types import EventType

from .simplepattern import SimplePattern
from .template import Template
from .rule import Rule, RPattern

InputPattern = Union[str, Dict[str, str]]


class Config(BaseProxyConfig):
    rules: Dict[str, Rule]
    templates: Dict[str, Template]
    default_flags: re.RegexFlag

    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("rules")
        helper.copy("templates")
        helper.copy("default_flags")
        helper.copy("antispam.max")
        helper.copy("antispam.delay")

    def parse_data(self) -> None:
        self.default_flags = re.RegexFlag(0)
        self.default_flags = self._get_flags(self["default_flags"])
        self.templates = {name: self._make_template(name, tpl)
                          for name, tpl in self["templates"].items()}
        self.rules = {name: self._make_rule(name, rule)
                      for name, rule in self["rules"].items()}

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

    def _make_template(self, name: str, tpl: Dict[str, Any]) -> Template:
        try:
            return Template(type=EventType.find(tpl.get("type", "m.room.message")),
                            variables=self._parse_variables(tpl),
                            content=self._parse_content(tpl.get("content", None))).init()
        except Exception as e:
            raise ConfigError(f"Failed to load {name}") from e

    def _compile_all(self, patterns: Union[InputPattern, List[InputPattern]]) -> List[RPattern]:
        if isinstance(patterns, list):
            return [self._compile(pattern) for pattern in patterns]
        else:
            return [self._compile(patterns)]

    def _compile(self, pattern: InputPattern) -> RPattern:
        flags = self.default_flags
        raw = None
        if isinstance(pattern, dict):
            flags = self._get_flags(pattern["flags"]) if "flags" in pattern else flags
            raw = pattern.get("raw", False)
            pattern = pattern["pattern"]
        if raw is not False and (not flags & re.MULTILINE or raw is True):
            return SimplePattern.compile(pattern, flags, raw) or re.compile(pattern, flags=flags)
        return re.compile(pattern, flags=flags)

    @staticmethod
    def _parse_variables(data: Dict[str, Any]) -> Dict[str, JinjaTemplate]:
        return {name: JinjaTemplate(var_tpl) for name, var_tpl
                in data.get("variables", {}).items()}

    @staticmethod
    def _parse_content(content: Union[Dict[str, Any], str]) -> Union[Dict[str, Any], JinjaTemplate]:
        if not content:
            return {}
        elif isinstance(content, str):
            return JinjaTemplate(content)
        return content

    @staticmethod
    def _get_flags(flags: Union[str, List[str]]) -> re.RegexFlag:
        output = re.RegexFlag(0)
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


class ConfigError(Exception):
    pass
