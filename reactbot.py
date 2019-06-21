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
from typing import Pattern, List, Set, Type
from attr import dataclass
import re

from mautrix.types import RoomID, EventType, ReactionEventContent, RelationType
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper

from maubot import Plugin, MessageEvent
from maubot.handlers import event


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("rules")


@dataclass
class Rule:
    rooms: Set[RoomID]
    matches: List[Pattern]
    reaction: str
    react_to_reply: bool

    def is_match(self, evt: MessageEvent) -> bool:
        if evt.room_id not in self.rooms:
            return False
        for match in self.matches:
            if match.match(evt.content.body):
                return True
        return False


class ReactBot(Plugin):
    rules: List[Rule]

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        await super().start()
        self.rules = []
        self.on_external_config_update()

    def on_external_config_update(self) -> None:
        self.config.load_and_update()
        self.rules = [Rule(rooms=set(rule.get("rooms", [])),
                           matches=[re.compile(match) for match in rule.get("matches")],
                           reaction=rule.get("reaction", "\U0001F44D"),
                           react_to_reply=rule.get("react_to_reply", False))
                      for rule in self.config["rules"]]

    @event.on(EventType.ROOM_MESSAGE)
    async def echo_handler(self, evt: MessageEvent) -> None:
        for rule in self.rules:
            if rule.is_match(evt):
                if rule.react_to_reply and evt.content.get_reply_to():
                    await self.client.react(evt.room_id, evt.content.get_reply_to(), rule.reaction)
                else:
                    await evt.react(rule.reaction)
