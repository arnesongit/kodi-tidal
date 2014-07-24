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
import requests
from .compat import urljoin
from .models import Artist, Album, Track, User, Playlist, SearchResult

log = logging.getLogger(__name__)


class Session(object):
    api_location = 'https://play.wimpmusic.com/v1/'
    api_token = 'rQtt0XAsYjXYIlml'

    def __init__(self, session_id='', country_code='NO', user_id=None):
        self.session_id = session_id
        self.country_code = country_code
        self.user = User(self, id=user_id) if user_id else None

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
        self.user = User(self, id=body['userId'])
        return True

    def _request(self, path, params=None):
        request_params = {
            'sessionId': self.session_id,
            'countryCode': self.country_code,
            'limit': '9999',
        }
        if params:
            request_params.update(params)
        url = urljoin(self.api_location, path)
        r = requests.get(url, params=request_params)
        log.debug("request: %s" % r.request.url)
        r.raise_for_status()
        json_obj = r.json()
        log.debug("response: %s" % json.dumps(json_obj, indent=4))
        return json_obj

    def get_user(self, user_id):
        return self._map_request('users/%s' % user_id, ret='user')

    def get_user_playlists(self, user_id):
        return self._map_request('users/%s/playlists' % user_id, ret='playlists')

    def get_favorite_artists(self, user_id):
        return self._map_request('users/%s/favorites/artists' % user_id, ret='artists')

    def get_favorite_albums(self, user_id):
        return self._map_request('users/%s/favorites/albums' % user_id, ret='albums')

    def get_favorite_tracks(self, user_id):
        json_obj = self._request('users/%s/favorites/tracks' % user_id)
        return [_parse_track(item['item']) for item in json_obj['items']]

    def get_playlist(self, playlist_id):
        return self._map_request('playlists/%s' % playlist_id, ret='playlist')

    def get_playlist_tracks(self, playlist_id):
        return self._map_request('playlists/%s/tracks' % playlist_id, ret='tracks')

    def get_album(self, album_id):
        return self._map_request('albums/%s' % album_id, ret='album')

    def get_album_tracks(self, album_id):
        return self._map_request('albums/%s/tracks' % album_id, ret='tracks')

    def get_artist(self, artist_id):
        return self._map_request('artists/%s' % artist_id, ret='artist')

    def get_artist_albums(self, artist_id):
        return self._map_request('artists/%s/albums' % artist_id, ret='albums')

    def get_artist_albums_ep_singles(self, artist_id):
        params = {'filter': 'EPSANDSINGLES'}
        return self._map_request('artists/%s/albums' % artist_id, params, ret='albums')

    def get_artist_albums_other(self, artist_id):
        params = {'filter': 'COMPILATIONS'}
        return self._map_request('artists/%s/albums' % artist_id, params, ret='albums')

    def get_artist_top_tracks(self, artist_id):
        return self._map_request('artists/%s/toptracks' % artist_id, ret='tracks')

    def get_artist_bio(self, artist_id):
        return self._request('artists/%s/bio' % artist_id)['text']

    def get_artist_similar(self, artist_id):
        return self._map_request('artists/%s/similar' % artist_id, ret='artists')

    def get_artist_radio(self, artist_id):
        return self._map_request('artists/%s/radio' % artist_id, params={'limit': 100}, ret='tracks')

    def _map_request(self, url, params=None, ret=None):
        json_obj = self._request(url, params)
        parse = None
        if ret.startswith('artist'):
            parse = _parse_artist
        elif ret.startswith('album'):
            parse = _parse_album
        elif ret.startswith('track'):
            parse = _parse_track
        elif ret.startswith('user'):
            raise NotImplementedError()
        elif ret.startswith('playlist'):
            parse = _parse_playlist

        items = json_obj.get('items')
        if items is None:
            return parse(json_obj)
        elif len(items) > 0 and 'item' in items[0]:
            return list(map(parse, [item['item'] for item in items]))
        else:
            return list(map(parse, items))

    def get_media_url(self, track_id):
        params = {'soundQuality': 'HIGH'}
        json_obj = self._request('tracks/%s/streamUrl' % track_id, params)
        return json_obj['url']

    def search(self, field, value):
        params = {
            'query': value,
            'limit': 50,
        }
        if field not in ['artist', 'album', 'playlist', 'track']:
            raise ValueError('Unknown field \'%s\'' % field)

        ret_type = field + 's'
        url = 'search/' + field + 's'
        result = self._map_request(url, params, ret=ret_type)
        return SearchResult(**{ret_type: result})


def _parse_artist(json_obj):
    return Artist(id=json_obj['id'], name=json_obj['name'])


def _parse_album(json_obj, artist=None):
    if artist is None:
        artist = _parse_artist(json_obj['artist'])
    kwargs = {
        'id': json_obj['id'],
        'name': json_obj['title'],
        'num_tracks': json_obj.get('numberOfTracks'),
        'duration': json_obj.get('duration'),
        'artist': artist,
    }
    return Album(**kwargs)


def _parse_playlist(json_obj):
    kwargs = {
        'id': json_obj['uuid'],
        'name': json_obj['title'],
        'description': json_obj['description'],
        'num_tracks': int(json_obj['numberOfTracks']),
        'duration': int(json_obj['duration']),
        'is_public': json_obj['publicPlaylist'],
        #TODO 'creator': _parse_user(json_obj['creator']),
    }
    return Playlist(**kwargs)


def _parse_track(json_obj):
    artist = _parse_artist(json_obj['artist'])
    album = _parse_album(json_obj['album'], artist)
    kwargs = {
        'id': json_obj['id'],
        'name': json_obj['title'],
        'duration': json_obj['duration'],
        'track_num': json_obj['trackNumber'],
        'popularity': json_obj['popularity'],
        'artist': artist,
        'album': album
    }
    return Track(**kwargs)
