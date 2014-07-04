# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import json
import logging
from collections import namedtuple
import requests
from .compat import urljoin

log = logging.getLogger(__name__)

Artist = namedtuple('Artist', ['name', 'id'])
Track = namedtuple('Track', ['name', 'id'])
Album = namedtuple('Album', ['name', 'id'])


class Session(object):
    api_location = 'https://play.wimpmusic.com/v1/'
    api_token = 'rQtt0XAsYjXYIlml'

    def __init__(self, session_id='', country_code='NO'):
        self.session_id = session_id
        self.country_code = country_code

    def login(self, username, password):
        url = urljoin(self.api_location, 'login/username')
        params = {'token': self.api_token}
        payload = {
            'username': username,
            'password': password,
        }
        r = requests.post(url, data=payload, params=params)
        r.raise_for_status()
        body = r.json()
        self.session_id = body['sessionId']
        self.country_code = body['countryCode']
        return True

    def _request(self, path, **params):
        common_params = {
            'sessionId': self.session_id,
            'countryCode': self.country_code,
        }
        url = urljoin(self.api_location, path)
        r = requests.get(url, params=dict(common_params, **params))
        log.debug("request: %s" % r.request.url)
        r.raise_for_status()
        json_obj = r.json()
        log.debug("response: %s" % json.dumps(json_obj, indent=4))
        return json_obj

    def get_album(self, album_id):
        json_obj = self._request('albums/%s/tracks' % album_id)
        items = json_obj['items']
        return [Track(item['title'], item['id']) for item in items]

    def get_media_url(self, track_id):
        params = {'soundQuality': 'HIGH'}
        json_obj = self._request('tracks/%s/streamUrl' % track_id, **params)
        return json_obj['url']

    def get_albums(self, artist_id):
        params = {'filter': 'COMPILATIONS'}
        json_obj = self._request('artists/%s/albums' % artist_id, **params)
        return [Album(item['title'], item['id']) for item in json_obj['items']]

    def search(self, ret, query):
        params = {
            'query': query,
            'limit': 25,
        }
        if ret == 'artists':
            json_obj = self._request('search/artists', **params)
            return [Artist(item['name'], item['id']) for item in json_obj['items']]
        return None
