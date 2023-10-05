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
from typing import Union, Dict, List, Tuple, Any
from itertools import chain
import json
import copy
import re

from attr import dataclass
from jinja2 import Template as JinjaStringTemplate
from jinja2.nativetypes import Template as JinjaNativeTemplate

from mautrix.types import EventType, Event


class Key(str):
    pass


variable_regex = re.compile(r"\$\${([0-9A-Za-z-_]+)}")
OmitValue = object()

global_vars = {
    "omit": OmitValue,
}

Index = Union[str, int, Key]


@dataclass
class Template:
    type: EventType
    variables: Dict[str, Any]
    content: Union[Dict[str, Any], JinjaStringTemplate]

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
                if variable_regex.search(k):
                    self._variable_locations.append((*path, Key(k)))
                self._map_variable_locations((*path, k), v)
        elif isinstance(data, str):
            if variable_regex.search(data):
                self._variable_locations.append(path)

    @classmethod
    def _recurse(cls, content: Any, path: Tuple[Index, ...]) -> Any:
        if len(path) == 0:
            return content
        return cls._recurse(content[path[0]], path[1:])

    @staticmethod
    def _replace_variables(tpl: str, variables: Dict[str, Any]) -> str:
        full_var_match = variable_regex.fullmatch(tpl)
        if full_var_match:
            # Whole field is a single variable, just return the value to allow non-string types.
            return variables[full_var_match.group(1)]
        return variable_regex.sub(lambda match: str(variables[match.group(1)]), tpl)

    def execute(self, evt: Event, rule_vars: Dict[str, Any], extra_vars: Dict[str, str]
                ) -> Dict[str, Any]:
        variables = extra_vars
        for name, template in chain(rule_vars.items(), self.variables.items()):
            if isinstance(template, JinjaNativeTemplate):
                rendered_var = template.render(event=evt, variables=variables, **global_vars)
                if not isinstance(rendered_var, (str, int, list, tuple, dict, bool)) and rendered_var is not None and rendered_var is not OmitValue:
                    rendered_var = str(rendered_var)
                variables[name] = rendered_var
            else:
                variables[name] = template
        if isinstance(self.content, JinjaStringTemplate):
            raw_json = self.content.render(event=evt, **variables)
            return json.loads(raw_json)
        content = copy.deepcopy(self.content)
        for path in self._variable_locations:
            data: Dict[str, Any] = self._recurse(content, path[:-1])
            key = path[-1]
            if isinstance(key, Key):
                key = str(key)
                data[self._replace_variables(key, variables)] = data.pop(key)
            else:
                replaced_data = self._replace_variables(data[key], variables)
                if replaced_data is OmitValue:
                    del data[key]
                else:
                    data[key] = replaced_data
        return content
