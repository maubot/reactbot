# reactbot - A maubot plugin that reacts to messages that match predefined rules.
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
from typing import Optional, Match, Dict, List, Set, Union, Any
import json

from attr import dataclass

from mautrix.types import RoomID, EventType, Serializable

from maubot import MessageEvent

from .template import Template
from .simplepattern import SimplePattern, RegexPattern

RPattern = Union[RegexPattern, SimplePattern]


@dataclass
class Rule:
    field: List[str]
    rooms: Set[RoomID]
    not_rooms: Set[RoomID]
    matches: List[RPattern]
    not_matches: List[RPattern]

    template: Template
    type: Optional[EventType]
    room_id: Optional[RoomID]
    state_event: bool
    variables: Dict[str, Any]

    def _check_not_match(self, evt: MessageEvent, data: str) -> bool:
        for pattern in self.not_matches:
            pattern_data = self._get_value(evt, pattern.field) if pattern.field else data
            if pattern.search(pattern_data):
                return True
        return False

    @staticmethod
    def _get_value(evt: MessageEvent, field: List[str]) -> str:
        data = evt
        for part in field:
            try:
                data = evt[part]
            except KeyError:
                return ""
        if isinstance(data, (str, int)):
            return str(data)
        elif isinstance(data, Serializable):
            return json.dumps(data.serialize())
        elif isinstance(data, (dict, list)):
            return json.dumps(data)
        else:
            return str(data)

    def match(self, evt: MessageEvent) -> Optional[Match]:
        if len(self.rooms) > 0 and evt.room_id not in self.rooms:
            return None
        elif evt.room_id in self.not_rooms:
            return None
        data = self._get_value(evt, self.field)
        for pattern in self.matches:
            pattern_data = self._get_value(evt, pattern.field) if pattern.field else data
            match = pattern.search(pattern_data)
            if match:
                if self._check_not_match(evt, data):
                    return None
                return match
        return None

    async def execute(self, evt: MessageEvent, match: Match) -> None:
        extra_vars = {
            **{str(i): val for i, val in enumerate(match.groups())},
            **match.groupdict(),
        }
        room_id = self.room_id or evt.room_id
        event_type = self.type or self.template.type
        content = self.template.execute(evt=evt, rule_vars=self.variables, extra_vars=extra_vars)
        if self.state_event:
            await evt.client.send_state_event(room_id, event_type, content)
        else:
            await evt.client.send_message_event(room_id, event_type, content)
