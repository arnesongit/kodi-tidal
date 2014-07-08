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

class Immutable(object):
    id = None
    name = None

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            self.__dict__[name] = value

    def __setattr__(self, name, value):
        raise AttributeError('immutable')


class Album(Immutable):
    artist = None
    num_tracks = -1
    duration = -1


class Artist(Immutable):
    pass


class Playlist(Immutable):
    description = None
    creator = None
    type = None
    is_public = None
    created = None
    last_updated = None
    num_tracks = -1
    duration = -1


class Track(Immutable):
    duration = -1
    track_num = -1
    popularity = -1
    artist = None
    album = None

    # @staticmethod
    # def from_response(json_obj):
    #     artist = Artist.from_response(json_obj['artist'])
    #     album = Album.from_response(json_obj['album'], artist)
    #     kwargs = {
    #         'id': json_obj['id'],
    #         'name': json_obj['title'],
    #         'duration': json_obj['duration'],
    #         'track_num': json_obj['trackNumber'],
    #         'popularity': json_obj['popularity'],
    #         'artist': artist,
    #         'album': album
    #     }
    #     return Track(**kwargs)


class User(object):

    def __init__(self, session, id):
        """
        :type session: :class:`wimpy.Session`
        :param id: The user ID
        """
        self._session = session
        self.id = id

    @property
    def playlists(self):
        return self._session.get_user_playlists(self.id)

    @property
    def favourite_artist(self):
        return self._session.get_favorite_artists(self.id)

    @property
    def favourite_albums(self):
        return self._session.get_favorite_albums(self.id)

    @property
    def favourite_tracks(self):
        return self._session.get_favorite_tracks(self.id)
