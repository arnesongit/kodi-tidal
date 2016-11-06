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

import traceback
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
from xbmcgui import ListItem
from requests import HTTPError
from lib import tidalapi
from lib.tidalapi.models import Album, Artist, Video, Quality, SubscriptionType, Promotion
from routing import Plugin

addon = xbmcaddon.Addon()
plugin = Plugin()
plugin.name = addon.getAddonInfo('name')

_addon_id = addon.getAddonInfo('id')

_subscription_type = [SubscriptionType.hifi, SubscriptionType.premium][int('0' + addon.getSetting('subscription_type'))]
_quality = [Quality.lossless, Quality.high, Quality.low][int('0' + addon.getSetting('quality'))]

config = tidalapi.Config(quality=_quality)
session = tidalapi.Session(config=config)

is_logged_in = False
_session_id = addon.getSetting('session_id')
_client_unique_key = addon.getSetting('client_unique_key')
_country_code = addon.getSetting('country_code')
_user_id = addon.getSetting('user_id')
if _session_id and _country_code and _user_id:
    session.load_session(session_id=_session_id, country_code=_country_code, user_id=_user_id, subscription_type=_subscription_type, unique_key=_client_unique_key)
    is_logged_in = True


def log(msg):
    xbmc.log(("[%s] %s" % (_addon_id, msg)).encode('utf-8'), level=xbmc.LOGDEBUG)


def view(data_items, urls, end=True):
    list_items = []
    for item, url in zip(data_items, urls):
        info = {'title': item.name}
        if isinstance(item, Album):
            li = ListItem('%s - %s' % (item.artist.name, item.title))
            info.update({'album': item.name, 'artist': item.artist.name})
            if getattr(item, 'year', None):
                info['year'] = item.year
        elif isinstance(item, Promotion):
            li = ListItem('%s - %s' % (item.shortHeader, item.shortSubHeader))
            info.update({'album': item.shortSubHeader, 'artist': item.shortHeader})
        elif isinstance(item, Artist):
            li = ListItem(item.name)
            info.update({'artist': item.name})
        else:
            li = ListItem(item.name)
        li.setInfo('music', info)
        artwork = {}
        if getattr(item, 'image', None):
            artwork['thumb'] = item.image
        if getattr(item, 'fanart', None):
            artwork['fanart'] = item.fanart
        if artwork:
            li.setArt(artwork)
        list_items.append((url, li, True))
    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    if end:
        xbmcplugin.endOfDirectory(plugin.handle)


def track_list(tracks, content='songs', end=True):
    if content:
        xbmcplugin.setContent(plugin.handle, content)
    list_items = []
    for track in tracks:
        if not getattr(track, 'available', True):
            continue
        if isinstance(track, Video):
            label = '%s - %s' % (track.artist.name, track.name)
            if track.explicit and not 'Explicit' in label:
                label += ' (Explicit)'
            url = plugin.url_for(play_video, video_id=track.id)
            li = ListItem(label)
            li.setProperty('isplayable', 'true')
            li.setInfo('video', {
                'artist': [track.artist.name],
                'title': track.title,
                'year': track.year,
                'plotoutline': '%s - %s' % (track.artist.name, track.name)
            })
            li.addStreamInfo('video', { 'codec': 'h264', 'aspect': 1.78, 'width': 1920,
                             'height': 1080, 'duration': track.duration if session.is_logged_in else 30})
            li.addStreamInfo('audio', { 'codec': 'AAC', 'language': 'en', 'channels': 2 })
        elif isinstance(track, Promotion):
            label = '%s - %s' % (track.shortHeader, track.shortSubHeader)
            url = plugin.url_for(play_video, video_id=track.id)
            li = ListItem(label)
            li.setProperty('isplayable', 'true')
            li.setInfo('video', {
                'artist': [track.shortHeader],
                'title': track.shortSubHeader,
                'plotoutline': track.text
            })
            li.addStreamInfo('video', { 'codec': 'h264', 'aspect': 1.78, 'width': 1920,
                             'height': 1080, 'duration': track.duration if session.is_logged_in else 30})
            li.addStreamInfo('audio', { 'codec': 'AAC', 'language': 'en', 'channels': 2 })
        else:
            label = '%s - %s' % (track.artist.name, track.name)
            if track.explicit and not 'Explicit' in label:
                label += ' (Explicit)'
            url = plugin.url_for(play_track, track_id=track.id)
            li = ListItem(label)
            li.setProperty('isplayable', 'true')
            li.setInfo('music', {
                'title': track.title,
                'tracknumber': track.trackNumber,
                'discnumber': track.volumeNumber,
                'duration': track.duration if session.is_logged_in else 30,
                'artist': track.artist.name,
                'album': track.album.title,
                'year': track.year,
            })
            radio_url = plugin.url_for(track_radio, track_id=track.id)
            li.addContextMenuItems(
                [('Track Radio', 'XBMC.Container.Update(%s)' % radio_url,)])
        artwork = {}
        if getattr(track, 'image', None):
            artwork['thumb'] = track.image
        if getattr(track, 'fanart', None):
            artwork['fanart'] = track.fanart
        if artwork:
            li.setArt(artwork)
        list_items.append((url, li, False))
    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    if end:
        xbmcplugin.endOfDirectory(plugin.handle)


def add_directory(title, endpoint):
    if callable(endpoint):
        endpoint = plugin.url_for(endpoint)
    xbmcplugin.addDirectoryItem(plugin.handle, endpoint, ListItem(title), True)


def urls_from_id(view_func, items):
    return [plugin.url_for(view_func, item.id) for item in items]


@plugin.route('/')
def root():
    if is_logged_in:
        add_directory('My Music', my_music)
    add_directory('Featured Playlists', featured_playlists)
    add_directory('Featured Videos', featured_videos)
    add_directory("What's New", whats_new)
    add_directory('Movies', movies)
    add_directory('Shows', shows)
    add_directory('Genres', genres)
    add_directory('Moods', moods)
    add_directory('Search', search)
    if is_logged_in:
        add_directory('Logout', logout)
    else:
        add_directory('Login (Trial Mode active !)', login)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/track_radio/<track_id>')
def track_radio(track_id):
    track_list(session.get_track_radio(track_id))


@plugin.route('/movies')
def movies():
    items = session.get_movies()
    track_list(items, content='musicvideos')


@plugin.route('/shows')
def shows():
    items = session.get_shows()
    view(items, urls_from_id(playlist_view, items))


@plugin.route('/moods')
def moods():
    items = session.get_moods()
    view(items, urls_from_id(moods_playlists, items))


@plugin.route('/moods/<mood>')
def moods_playlists(mood):
    items = session.get_mood_playlists(mood)
    view(items, urls_from_id(playlist_view, items))


@plugin.route('/genres')
def genres():
    items = session.get_genres()
    view(items, urls_from_id(genre_view, items))


@plugin.route('/genre/<genre_id>')
def genre_view(genre_id):
    add_directory('Playlists', plugin.url_for(genre_playlists, genre_id=genre_id))
    add_directory('Albums', plugin.url_for(genre_albums, genre_id=genre_id))
    add_directory('Tracks', plugin.url_for(genre_tracks, genre_id=genre_id))
    add_directory('Videos', plugin.url_for(genre_videos, genre_id=genre_id))
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/genre/<genre_id>/playlists')
def genre_playlists(genre_id):
    items = session.get_genre_items(genre_id, 'playlists')
    view(items, urls_from_id(playlist_view, items))


@plugin.route('/genre/<genre_id>/albums')
def genre_albums(genre_id):
    xbmcplugin.setContent(plugin.handle, 'albums')
    items = session.get_genre_items(genre_id, 'albums')
    view(items, urls_from_id(album_view, items))


@plugin.route('/genre/<genre_id>/tracks')
def genre_tracks(genre_id):
    items = session.get_genre_items(genre_id, 'tracks')
    track_list(items)


@plugin.route('/genre/<genre_id>/videos')
def genre_videos(genre_id):
    items = session.get_genre_items(genre_id, 'videos')
    track_list(items, content='musicvideos')


@plugin.route('/featured_playlists')
def featured_playlists():
    items = session.get_featured(group='NEWS', types=['ALBUM', 'PLAYLIST'])
    playlists = [item for item in items if item.type == 'PLAYLIST']
    albums = [item for item in items if item.type == 'ALBUM']
    view(playlists, urls_from_id(playlist_view, playlists), end=False)
    view(albums, urls_from_id(album_view, albums), end=True)


@plugin.route('/featured_videos')
def featured_videos():
    items = session.get_featured(group='NEWS', types=['VIDEO'])
    track_list(items, content='musicvideos', end=True)


@plugin.route('/whats_new')
def whats_new():
    add_directory('Recommended Playlists', plugin.url_for(featured, group='recommended', content_type='playlists'))
    add_directory('Recommended Albums', plugin.url_for(featured, group='recommended', content_type='albums'))
    add_directory('Recommended Tracks', plugin.url_for(featured, group='recommended', content_type='tracks'))
    add_directory('Recommended Videos', plugin.url_for(featured, group='recommended', content_type='videos'))
    add_directory('New Playlists', plugin.url_for(featured, group='new', content_type='playlists'))
    add_directory('New Albums', plugin.url_for(featured, group='new', content_type='albums'))
    add_directory('New Tracks', plugin.url_for(featured, group='new', content_type='tracks'))
    add_directory('New Videos', plugin.url_for(featured, group='new', content_type='videos'))
    add_directory('Top Albums', plugin.url_for(featured, group='top', content_type='albums'))
    add_directory('Top Tracks', plugin.url_for(featured, group='top', content_type='tracks'))
    add_directory('Top Videos', plugin.url_for(featured, group='top', content_type='videos'))
    add_directory('Exclusive Playlists', plugin.url_for(featured, group='exclusive', content_type='playlists'))
    add_directory('Exclusive Videos', plugin.url_for(featured, group='exclusive', content_type='videos'))
    if session.country_code != 'US':
        add_directory('Local Playlists', plugin.url_for(featured, group='local', content_type='playlists'))
        add_directory('Local Albums', plugin.url_for(featured, group='local', content_type='albums'))
        add_directory('Local Tracks', plugin.url_for(featured, group='local', content_type='tracks'))
        add_directory('Local Videos', plugin.url_for(featured, group='local', content_type='videos'))
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/featured/<group>/<content_type>')
def featured(group=None, content_type=None):
    items = session.get_featured_items(content_type, group)
    if content_type == 'tracks':
        track_list(items)
    elif content_type == 'videos':
        track_list(items, content='musicvideos')
    elif content_type == 'albums':
        xbmcplugin.setContent(plugin.handle, 'albums')
        view(items, urls_from_id(album_view, items))
    elif content_type == 'playlists':
        view(items, urls_from_id(playlist_view, items))


@plugin.route('/my_music')
def my_music():
    add_directory('My Playlists', my_playlists)
    add_directory('Favourite Playlists', favourite_playlists)
    add_directory('Favourite Artists', favourite_artists)
    add_directory('Favourite Albums', favourite_albums)
    add_directory('Favourite Tracks', favourite_tracks)
    add_directory('Favourite Videos', favourite_videos)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/album/<album_id>')
def album_view(album_id):
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    album = session.get_album(album_id)
    if album and album.numberOfVideos > 0:
        add_directory('Videos', plugin.url_for(album_videos, album_id=album_id))
    track_list(session.get_album_tracks(album_id))


@plugin.route('/album_videos/<album_id>')
def album_videos(album_id):
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    track_list(session.get_album_items(album_id, ret='videos'))


@plugin.route('/artist/<artist_id>')
def artist_view(artist_id):
    xbmcplugin.setContent(plugin.handle, 'albums')
    xbmcplugin.addDirectoryItem(
        plugin.handle, plugin.url_for(top_tracks, artist_id),
        ListItem('Top Tracks'), True
    )
    xbmcplugin.addDirectoryItem(
        plugin.handle, plugin.url_for(artist_videos, artist_id),
        ListItem('Artist Videos'), True
    )
    xbmcplugin.addDirectoryItem(
        plugin.handle, plugin.url_for(artist_radio, artist_id),
        ListItem('Artist Radio'), True
    )
    xbmcplugin.addDirectoryItem(
        plugin.handle, plugin.url_for(similar_artists, artist_id),
        ListItem('Similar Artists'), True
    )
    albums = session.get_artist_albums(artist_id) + \
             session.get_artist_albums_ep_singles(artist_id) + \
             session.get_artist_albums_other(artist_id)
    view(albums, urls_from_id(album_view, albums))


@plugin.route('/artist/<artist_id>/radio')
def artist_radio(artist_id):
    track_list(session.get_artist_radio(artist_id))


@plugin.route('/artist/<artist_id>/top')
def top_tracks(artist_id):
    track_list(session.get_artist_top_tracks(artist_id))


@plugin.route('/artist/<artist_id>/videos')
def artist_videos(artist_id):
    track_list(session.get_artist_videos(artist_id))


@plugin.route('/artist/<artist_id>/similar')
def similar_artists(artist_id):
    xbmcplugin.setContent(plugin.handle, 'artists')
    artists = session.get_artist_similar(artist_id)
    view(artists, urls_from_id(artist_view, artists))


@plugin.route('/playlist/<playlist_id>')
def playlist_view(playlist_id):
    track_list(session.get_playlist_items(playlist_id))


@plugin.route('/user_playlists')
def my_playlists():
    items = session.user.playlists()
    view(items, urls_from_id(playlist_view, items))


@plugin.route('/favourite_playlists')
def favourite_playlists():
    items = session.user.favorites.playlists()
    view(items, urls_from_id(playlist_view, items))


@plugin.route('/favourite_artists')
def favourite_artists():
    xbmcplugin.setContent(plugin.handle, 'artists')
    items = session.user.favorites.artists()
    view(items, urls_from_id(artist_view, items))


@plugin.route('/favourite_albums')
def favourite_albums():
    xbmcplugin.setContent(plugin.handle, 'albums')
    items = session.user.favorites.albums()
    view(items, urls_from_id(album_view, items))


@plugin.route('/favourite_tracks')
def favourite_tracks():
    track_list(session.user.favorites.tracks())


@plugin.route('/favourite_videos')
def favourite_videos():
    track_list(session.user.favorites.videos(), content='musicvideos')


@plugin.route('/search')
def search():
    add_directory('Artist', plugin.url_for(search_type, field='artist'))
    add_directory('Album', plugin.url_for(search_type, field='album'))
    add_directory('Playlist', plugin.url_for(search_type, field='playlist'))
    add_directory('Track', plugin.url_for(search_type, field='track'))
    add_directory('Videos', plugin.url_for(search_type, field='video'))
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/search_type/<field>')
def search_type(field):
    keyboard = xbmc.Keyboard('', 'Search')
    keyboard.doModal()
    if keyboard.isConfirmed():
        keyboardinput = keyboard.getText()
        if keyboardinput:
            searchresults = session.search(field, keyboardinput)
            view(searchresults.artists, urls_from_id(artist_view, searchresults.artists), end=False)
            view(searchresults.albums, urls_from_id(album_view, searchresults.albums), end=False)
            view(searchresults.playlists, urls_from_id(playlist_view, searchresults.playlists), end=False)
            track_list(searchresults.tracks, end=False)
            track_list(searchresults.videos, content=None, end=True)


@plugin.route('/login')
def login():
    username = addon.getSetting('username')
    password = addon.getSetting('password')
    subscription_type = _subscription_type
    session.client_unique_key = _client_unique_key

    if not username or not password:
        # Ask for username/password
        dialog = xbmcgui.Dialog()
        username = dialog.input('Username')
        if not username:
            return
        password = dialog.input('Password', option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if not password:
            return
        selected = dialog.select('Subscription Type', [SubscriptionType.hifi, SubscriptionType.premium])
        if selected < 0:
            return
        subscription_type = [SubscriptionType.hifi, SubscriptionType.premium][selected]

    if session.login(username, password, subscription_type=subscription_type):
        addon.setSetting('session_id', session.session_id)
        addon.setSetting('client_unique_key', session.client_unique_key)
        addon.setSetting('country_code', session.country_code)
        addon.setSetting('user_id', unicode(session.user.id))
        addon.setSetting('subscription_type', '0' if session.user.subscription.type == SubscriptionType.hifi else '1')

        if not addon.getSetting('username') or not addon.getSetting('password'):
            # Ask about remembering username/password
            dialog = xbmcgui.Dialog()
            if dialog.yesno(plugin.name, 'Remember login details?'):
                addon.setSetting('username', username)
                addon.setSetting('password', password)
    xbmc.executebuiltin('XBMC.Container.Refresh()')


@plugin.route('/logout')
def logout():
    addon.setSetting('session_id', '')
    addon.setSetting('user_id', '')
    xbmc.executebuiltin('XBMC.Container.Refresh()')


@plugin.route('/play_track/<track_id>')
def play_track(track_id):
    media_url = session.get_media_url(track_id)
    if not media_url.startswith('http://') and not media_url.startswith('https://'):
        log("media url: %s" % media_url)
        host, tail = media_url.split('/', 1)
        app, playpath = tail.split('/mp4:', 1)
        media_url = 'rtmp://%s app=%s playpath=mp4:%s' % (host, app, playpath)
    li = ListItem(path=media_url)
    mimetype = 'audio/flac' if config.quality == Quality.lossless else 'audio/mpeg'
    li.setProperty('mimetype', mimetype)
    xbmcplugin.setResolvedUrl(plugin.handle, True, li)


@plugin.route('/play_video/<video_id>')
def play_video(video_id):
    media_url = session.get_video_url(video_id)
    li = ListItem(path=media_url)
    li.setProperty('mimetype', 'video/mp4')
    xbmcplugin.setResolvedUrl(plugin.handle, True, li)


if __name__ == '__main__':
    try:
        plugin.run()
    except HTTPError as e:
        if e.response.status_code in [401, 403]:
            dialog = xbmcgui.Dialog()
            dialog.notification(plugin.name, "Authorization problem", xbmcgui.NOTIFICATION_ERROR)
        traceback.print_exc()
