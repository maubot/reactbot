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
from typing import Type, Tuple, Dict
import time

from attr import dataclass

from mautrix.types import EventType, MessageType, UserID, RoomID
from mautrix.util.config import BaseProxyConfig

from maubot import Plugin, MessageEvent
from maubot.handlers import event

from .config import Config, ConfigError


@dataclass
class FloodInfo:
    max: int
    delay: int
    count: int
    last_message: int

    def bump(self) -> bool:
        now = int(time.time())
        if self.last_message + self.delay < now:
            self.count = 0
        self.count += 1
        if self.count > self.max:
            return True
        self.last_message = now
        return False


class ReactBot(Plugin):
    allowed_msgtypes: Tuple[MessageType, ...] = (MessageType.TEXT, MessageType.EMOTE)
    user_flood: Dict[UserID, FloodInfo]
    room_flood: Dict[RoomID, FloodInfo]

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        await super().start()
        self.user_flood = {}
        self.room_flood = {}
        self.on_external_config_update()

    def on_external_config_update(self) -> None:
        self.config.load_and_update()
        try:
            self.config.parse_data()
        except ConfigError:
            self.log.exception("Failed to load config")
        for fi in self.user_flood.values():
            fi.max = self.config["antispam.user.max"]
            fi.delay = self.config["antispam.user.delay"]
        for fi in self.room_flood.values():
            fi.max = self.config["antispam.room.max"]
            fi.delay = self.config["antispam.room.delay"]

    def _make_flood_info(self, for_type: str) -> 'FloodInfo':
        return FloodInfo(max=self.config[f"antispam.{for_type}.max"],
                         delay=self.config[f"antispam.{for_type}.delay"],
                         count=0, last_message=0)

    def _get_flood_info(self, flood_map: dict, key: str, for_type: str) -> 'FloodInfo':
        try:
            return flood_map[key]
        except KeyError:
            fi = flood_map[key] = self._make_flood_info(for_type)
            return fi

    def is_flood(self, evt: MessageEvent) -> bool:
        return (self._get_flood_info(self.user_flood, evt.sender, "user").bump()
                or self._get_flood_info(self.room_flood, evt.room_id, "room").bump())

    @event.on(EventType.ROOM_MESSAGE)
    async def event_handler(self, evt: MessageEvent) -> None:
        if evt.sender == self.client.mxid or evt.content.msgtype not in self.allowed_msgtypes:
            return
        for name, rule in self.config.rules.items():
            match = rule.match(evt)
            if match is not None:
                if self.is_flood(evt):
                    return
                try:
                    await rule.execute(evt, match)
                except Exception:
                    self.log.exception(f"Failed to execute {name}")
                return
