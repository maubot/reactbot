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
from typing import Any, Dict, List, Match, Optional, Pattern, Set, Union

from attr import dataclass

from maubot import MessageEvent
from mautrix.types import EventType, RoomID, UserID,RelationType,MessageType

from .simplepattern import SimplePattern
from .template import OmitValue, Template

RPattern = Union[Pattern, SimplePattern]


@dataclass
class Rule:
    rooms: Set[RoomID]
    not_rooms: Set[RoomID]
    users: Set[UserID]
    not_users: Set[UserID]
    not_thread: bool
    only_text: bool
    is_reedit: bool
    matches: List[RPattern]
    not_matches: List[RPattern]
    template: Template
    type: Optional[EventType]
    variables: Dict[str, Any]

    def _check_not_match(self, body: str) -> bool:
        for pattern in self.not_matches:
            if pattern.search(body):
                return True
        return False

    def match(self, evt: MessageEvent) -> Optional[Match]:
        if len(self.rooms) > 0 and evt.room_id not in self.rooms:
            return None
        elif evt.room_id in self.not_rooms:
            return None
        if len(self.users) > 0 and evt.sender not in self.users:
            return None
        elif evt.sender in self.not_users:
            return None
        if self.not_thread and  evt.content.relates_to and evt.content.relates_to.rel_type == RelationType.THREAD:
            return None
        if self.only_text and (evt.content.msgtype != MessageType.TEXT and evt.content.msgtype != MessageType.NOTICE):
            return None
        if self.is_reedit == False and (evt.content.relates_to and evt.content.relates_to.rel_type == RelationType.REPLACE):
            return None
        for pattern in self.matches:
            match = pattern.search(evt.content.body)
            if match:
                if self._check_not_match(evt.content.body):
                    return None
                return match
        return None

    async def execute(self, evt: MessageEvent, match: Match) -> None:
        extra_vars = {
            "0": match.group(0),
            **{str(i + 1): val for i, val in enumerate(match.groups())},
            **match.groupdict(),
        }
        content = self.template.execute(evt=evt, rule_vars=self.variables, extra_vars=extra_vars)
        await evt.client.send_message_event(evt.room_id, self.type or self.template.type, content)
