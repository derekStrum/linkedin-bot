#!/usr/bin/env python3
# Copyright (C) 2019 nickolas360 <contact@nickolas360.com>
#
# This file is part of librecaptcha.
#
# librecaptcha is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# librecaptcha is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with librecaptcha.  If not, see <http://www.gnu.org/licenses/>.

import requests
from html.parser import HTMLParser
import re

URL = "https://techblog.willshouse.com/2012/01/03/most-common-user-agents/"
NUM_ENTRIES = 30


class Parser(HTMLParser):
    def __init__(self):
        self.desc_seen = False
        self.result = None
        super().__init__()

    def handle_data(self, data):
        if self.result is not None:
            return
        if data is None:
            return
        if not self.desc_seen:
            self.desc_seen = bool(re.search(r"\bplain-text\b", data))
            return
        if re.match(r"\s*Mozilla/", data):
            self.result = data


def get_agents(data):
    agents = []
    for agent in data.strip().splitlines()[:NUM_ENTRIES]:
        if len(agents) >= NUM_ENTRIES:
            break
        if re.match(r"\b(Chrome)\b", agent):
            continue
        agents.append(agent)
    return agents


def get_all_user_agents():
    r = requests.get(URL)
    parser = Parser()
    parser.feed(r.text)
    agents = get_agents(parser.result)
    return agents
