# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland, Arne Svenson
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

import sys
import traceback
import logging
from urlparse import urlsplit
import xbmc
import xbmcgui
import xbmcplugin
from xbmcgui import ListItem
from requests import HTTPError
from lib.tidalapi.models import Quality, Category, BrowsableMedia, SubscriptionType
from lib.koditidal import plugin, addon, _T, _P, log, DEBUG_LEVEL, KodiLogHandler
from lib.koditidal import TidalSession, FolderItem


# Set Log Handler for tidalapi
logger = logging.getLogger()
logger.addHandler(KodiLogHandler(modules=['lib.tidalapi']))
if DEBUG_LEVEL == xbmc.LOGSEVERE:
    logger.setLevel(logging.DEBUG)

# This is the Tidal Session
session = TidalSession()
session.load_session()


def add_items(items, content=None, end=True, withNextPage=False):
    if content:
        xbmcplugin.setContent(plugin.handle, content)
    list_items = []
    for item in items:
        if isinstance(item, Category):
            category_items = item.getListItems()
            for url, li, isFolder in category_items:
                if url and li:
                    list_items.append((url, li, isFolder))
        elif isinstance(item, BrowsableMedia):
            url, li, isFolder = item.getListItem()
            if url and li:
                list_items.append((url, li, isFolder))
    if withNextPage and len(items) > 0:
        # Add folder for next page
        try:
            totalNumberOfItems = items[0]._totalNumberOfItems
            nextOffset = items[0]._offset + session._config.pageSize
            if nextOffset < totalNumberOfItems and len(items) >= session._config.pageSize:
                path = urlsplit(sys.argv[0]).path or '/'
                path = path.split('/')[:-1]
                path.append(str(nextOffset))
                url = '/'.join(path)
                add_directory(_T(30244).format(pos1=nextOffset, pos2=min(nextOffset+session._config.pageSize, totalNumberOfItems)), plugin.url_for_path(url))
        except:
            log('Next Page for URL %s not set' % sys.argv[0], xbmc.LOGERROR)
    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    if end:
        xbmcplugin.endOfDirectory(plugin.handle)


def add_directory(title, endpoint, thumb=None, fanart=None):
    if callable(endpoint):
        endpoint = plugin.url_for(endpoint)
    item = FolderItem(title, endpoint, thumb, fanart)
    add_items([item], end=False)


@plugin.route('/')
def root():
    if session.is_logged_in:
        add_directory(_T(30201), my_music)
    add_directory(_T(30202), featured_playlists)
    categories = Category.groups()
    for item in categories:
        add_directory(_T(item), plugin.url_for(category, group=item))
    add_directory(_T(30206), search)
    if session.is_logged_in:
        add_directory(_T(30207), logout)
    else:
        add_directory(_T(30208), login)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/category/<group>')
def category(group):
    promoGroup = {'rising': 'RISING', 'discovery': 'DISCOVERY', 'featured': 'NEWS'}.get(group, None)
    items = session.get_category_items(group)
    totalCount = 0
    for item in items:
        totalCount += len(item.content_types)
    if totalCount == 1:
        # Show Single content directly (Movies and TV Shows)
        for item in items:
            content_types = item.content_types
            for content_type in content_types:
                category_content(group, item.path, content_type, offset=0)
                return
    xbmcplugin.setContent(plugin.handle, 'files')
    if promoGroup and totalCount > 10:
        # Add Promotions as Folder on the Top if more than 10 Promotions available
        add_directory(_T(30202), plugin.url_for(featured, group=promoGroup))
    # Add Category Items as Folders
    add_items(items, content=None, end=False)
    if promoGroup and totalCount <= 10:
        # Show up to 10 Promotions as single Items
        promoItems = session.get_featured(promoGroup, types=['ALBUM', 'PLAYLIST', 'VIDEO'])
        if promoItems:
            add_items(promoItems, end=False)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/category/<group>/<path>')
def category_item(group, path):
    items = session.get_category_items(group)
    path_items = []
    for item in items:
        if item.path == path:
            item._force_subfolders = True
            path_items.append(item)
    add_items(path_items, content='files')


@plugin.route('/category/<group>/<path>/<content_type>/<offset>')
def category_content(group, path, content_type, offset):
    items = session.get_category_content(group, path, content_type, offset=int('0%s' % offset), limit=session._config.pageSize)
    add_items(items, content='musicvideos' if content_type == 'videos' else 'songs', withNextPage=True)


@plugin.route('/track_radio/<track_id>')
def track_radio(track_id):
    add_items(session.get_track_radio(track_id), content='songs')


@plugin.route('/recommended/tracks/<track_id>')
def recommended_tracks(track_id):
    add_items(session.get_recommended_items('tracks', track_id), content='songs')


@plugin.route('/recommended/videos/<video_id>')
def recommended_videos(video_id):
    add_items(session.get_recommended_items('videos', video_id), content='musicvideos')


@plugin.route('/featured/<group>')
def featured(group):
    items = session.get_featured(group, types=['ALBUM', 'PLAYLIST', 'VIDEO'])
    add_items(items, content='files')


@plugin.route('/featured_playlists')
def featured_playlists():
    items = session.get_featured()
    add_items(items, content='files')


@plugin.route('/my_music')
def my_music():
    add_directory(_T(30213), user_playlists)
    add_directory(_T(30214), plugin.url_for(favorites, content_type='artists'))
    add_directory(_T(30215), plugin.url_for(favorites, content_type='albums'))
    add_directory(_T(30216), plugin.url_for(favorites, content_type='playlists'))
    add_directory(_T(30217), plugin.url_for(favorites, content_type='tracks'))
    add_directory(_T(30218), plugin.url_for(favorites, content_type='videos'))
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/album/<album_id>')
def album_view(album_id):
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    add_items(session.get_album_tracks(album_id), content='albums')


@plugin.route('/artist/<artist_id>')
def artist_view(artist_id):
    if session.is_logged_in:
        session.user.favorites.load_all()
    artist = session.get_artist(artist_id)
    xbmcplugin.setContent(plugin.handle, 'albums')
    add_directory(_T(30225), plugin.url_for(artist_bio, artist_id), thumb=artist.image, fanart=artist.fanart)
    add_directory(_T(30226), plugin.url_for(top_tracks, artist_id), thumb=artist.image, fanart=artist.fanart)
    add_directory(_P('videos'), plugin.url_for(artist_videos, artist_id), thumb=artist.image, fanart=artist.fanart)
    add_directory(_T(30227), plugin.url_for(artist_radio, artist_id), thumb=artist.image, fanart=artist.fanart)
    add_directory(_T(30228), plugin.url_for(artist_playlists, artist_id), thumb=artist.image, fanart=artist.fanart)
    add_directory(_T(30229), plugin.url_for(similar_artists, artist_id), thumb=artist.image, fanart=artist.fanart)
    if session.is_logged_in:
        if session.user.favorites.isFavoriteArtist(artist_id):
            add_directory(_T(30220), plugin.url_for(favorites_remove, content_type='artists', item_id=artist_id), thumb=artist.image, fanart=artist.fanart)
        else:
            add_directory(_T(30219), plugin.url_for(favorites_add, content_type='artists', item_id=artist_id), thumb=artist.image, fanart=artist.fanart)
    albums = session.get_artist_albums(artist_id) + \
             session.get_artist_albums_ep_singles(artist_id) + \
             session.get_artist_albums_other(artist_id)
    add_items(albums, content=None)


@plugin.route('/artist/<artist_id>/bio')
def artist_bio(artist_id):
    artist = session.get_artist(artist_id)
    info = session.get_artist_info(artist_id)
    text = ''
    if info.get('summary', None):
        text += '%s:\n\n' % _T(30230) + info.get('summary') + '\n\n'
    if info.get('text', None):
        text += '%s:\n\n' % _T(30225) + info.get('text')
    if text:
        xbmcgui.Dialog().textviewer(artist.name, text)


@plugin.route('/artist/<artist_id>/top')
def top_tracks(artist_id):
    add_items(session.get_artist_top_tracks(artist_id), content='songs')


@plugin.route('/artist/<artist_id>/radio')
def artist_radio(artist_id):
    add_items(session.get_artist_radio(artist_id), content='songs')


@plugin.route('/artist/<artist_id>/videos')
def artist_videos(artist_id):
    add_items(session.get_artist_videos(artist_id), content='musicvideos')


@plugin.route('/artist/<artist_id>/playlists')
def artist_playlists(artist_id):
    add_items(session.get_artist_playlists(artist_id), content='songs')


@plugin.route('/artist/<artist_id>/similar')
def similar_artists(artist_id):
    add_items(session.get_artist_similar(artist_id), content='artists')


@plugin.route('/playlist/<playlist_id>')
def playlist_view(playlist_id):
    add_items(session.get_playlist_items(playlist_id), content='songs')


@plugin.route('/user_playlists')
def user_playlists():
    add_items(session.user.playlists(), content='songs')


@plugin.route('/user_playlist/delete/<playlist_id>')
def user_playlist_delete(playlist_id):
    dialog = xbmcgui.Dialog()
    playlist = session.get_playlist(playlist_id)
    ok = dialog.yesno(_T(30235), _T(30236).format(name=playlist.title, count=playlist.numberOfItems))
    if ok:
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        try:
            session.user.delete_playlist(playlist_id)
        except Exception, e:
            log(str(e), level=xbmc.LOGERROR)
            traceback.print_exc()
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        xbmc.executebuiltin('Container.Refresh()')


@plugin.route('/user_playlist/add/<item_type>/<item_id>')
def user_playlist_add_item(item_type, item_id):
    if item_type == 'playlist':
        items = session.get_playlist_items(item_id)
        # Sort Items by Artist, Title
        items.sort(key=lambda line: (line.artist.name, line.title) , reverse=False)
        items = [item.id for item in items]
    else:
        items = [item_id]
    playlist = session.selectPlaylistDialog(allowNew=True, item_type=item_type)
    if playlist:
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        try:
            session.user.add_playlist_entries(playlist=playlist, item_ids=items)
        except Exception, e:
            log(str(e), level=xbmc.LOGERROR)
            traceback.print_exc()
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        xbmc.executebuiltin('Container.Refresh()')


@plugin.route('/user_playlist/remove/<playlist_id>/<entry_no>')
def user_playlist_remove_item(playlist_id, entry_no):
    dialog = xbmcgui.Dialog()
    item_no = int('0%s' % entry_no) + 1
    ok = dialog.yesno(_T(30240), _T(30241) % item_no )
    if ok:
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        try:
            session.user.remove_playlist_entry(playlist_id, entry_no=entry_no)
        except Exception, e:
            log(str(e), level=xbmc.LOGERROR)
            traceback.print_exc()
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        xbmc.executebuiltin('Container.Refresh()')


@plugin.route('/favorites/<content_type>')
def favorites(content_type):
    CONTENT_FOR_TYPE = {'artists': 'artists', 'albums': 'albums', 'playlists': 'albums', 'tracks': 'songs', 'videos': 'musicvideos'}
    items = session.user.favorites.get(content_type, limit=100 if content_type == 'videos' else 9999)
    if content_type in ['playlists', 'artists']:
        items.sort(key=lambda line: line.name, reverse=False)
    else:
        items.sort(key=lambda line: '%s - %s' % (line.artist.name, line.title), reverse=False)
    add_items(items, content=CONTENT_FOR_TYPE.get(content_type, 'songs'))


@plugin.route('/favorites/add/<content_type>/<item_id>')
def favorites_add(content_type, item_id):
    ok = session.user.favorites.add(content_type, item_id)
    if ok:
        xbmcgui.Dialog().notification(heading=plugin.name, message=_T(30231).format(what=_T(content_type)), icon=xbmcgui.NOTIFICATION_INFO)
    #if content_type == 'artists':
        # Refresh the Artist View page
    xbmc.executebuiltin('Container.Refresh()')


@plugin.route('/favorites/remove/<content_type>/<item_id>')
def favorites_remove(content_type, item_id):
    ok = session.user.favorites.remove(content_type, item_id)
    if ok:
        xbmcgui.Dialog().notification(heading=plugin.name, message=_T(30232).format(what=_T(content_type)), icon=xbmcgui.NOTIFICATION_INFO)
    xbmc.executebuiltin('Container.Refresh()')


@plugin.route('/search')
def search():
    add_directory(_T(30106), plugin.url_for(search_type, field='artist'))
    add_directory(_T(30107), plugin.url_for(search_type, field='album'))
    add_directory(_T(30108), plugin.url_for(search_type, field='playlist'))
    add_directory(_T(30109), plugin.url_for(search_type, field='track'))
    add_directory(_T(30110), plugin.url_for(search_type, field='video'))
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/search_type/<field>')
def search_type(field):
    keyboard = xbmc.Keyboard('', _T(30206))
    keyboard.doModal()
    if keyboard.isConfirmed():
        keyboardinput = keyboard.getText()
        if keyboardinput:
            searchresults = session.search(field, keyboardinput)
            add_items(searchresults.artists, content='files', end=False)
            add_items(searchresults.albums, end=False)
            add_items(searchresults.playlists, end=False)
            add_items(searchresults.tracks, end=False)
            add_items(searchresults.videos, end=True)


@plugin.route('/login')
def login():
    username = addon.getSetting('username')
    password = addon.getSetting('password')
    subscription_type = [SubscriptionType.hifi, SubscriptionType.premium][int('0' + addon.getSetting('subscription_type'))]

    if not username or not password:
        # Ask for username/password
        dialog = xbmcgui.Dialog()
        username = dialog.input(_T(30008))
        if not username:
            return
        password = dialog.input(_T(30009), option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if not password:
            return
        subscription_type = dialog.select(_T(30010), [SubscriptionType.hifi, SubscriptionType.premium])
        if not subscription_type:
            return

    if session.login(username, password, subscription_type):
        addon.setSetting('session_id', session.session_id)
        addon.setSetting('api_session_id', session.api_session_id)
        addon.setSetting('country_code', session.country_code)
        addon.setSetting('user_id', unicode(session.user.id))
        addon.setSetting('subscription_type', '0' if session.user.subscription.type == SubscriptionType.hifi else '1')

        if not addon.getSetting('username') or not addon.getSetting('password'):
            # Ask about remembering username/password
            dialog = xbmcgui.Dialog()
            if dialog.yesno(plugin.name, _T(30209)):
                addon.setSetting('username', username)
                addon.setSetting('password', password)
    xbmc.executebuiltin('Container.Refresh()')


@plugin.route('/logout')
def logout():
    addon.setSetting('session_id', '')
    addon.setSetting('api_session_id', '')
    # Keep Country Code
    #addon.setSetting('country_code', '')
    addon.setSetting('user_id', '')
    # Keep Subscription Type
    #addon.setSetting('subscription_type', '')
    xbmc.executebuiltin('Container.Refresh()')


@plugin.route('/play_track/<track_id>')
def play_track(track_id):
    media_url = session.get_media_url(track_id)
    if not media_url.startswith('http://') and not media_url.startswith('https://'):
        log("media url: %s" % media_url)
        host, tail = media_url.split('/', 1)
        app, playpath = tail.split('/mp4:', 1)
        media_url = 'rtmp://%s app=%s playpath=mp4:%s' % (host, app, playpath)
    li = ListItem(path=media_url)
    mimetype = 'audio/flac' if session._config.quality == Quality.lossless and session.is_logged_in else 'audio/mpeg'
    li.setProperty('mimetype', mimetype)
    xbmcplugin.setResolvedUrl(plugin.handle, True, li)


@plugin.route('/play_video/<video_id>')
def play_video(video_id):
    media_url = session.get_video_url(video_id)
    li = ListItem(path=media_url)
    li.setProperty('mimetype', 'video/mp4')
    xbmcplugin.setResolvedUrl(plugin.handle, True, li)


@plugin.route('/stream_locked')
def stream_locked():
    xbmcgui.Dialog().notification(heading=plugin.name, message=_T(30242), icon=xbmcgui.NOTIFICATION_INFO)


if __name__ == '__main__':
    try:
        plugin.run()
    except HTTPError as e:
        r = e.response
        if r.status_code in [401, 403]:
            xbmcgui.Dialog().notification(plugin.name, _T(30210), xbmcgui.NOTIFICATION_ERROR)
        else:
            try:
                msg = r.json().get('userMessage')
            except:
                msg = r.reason
            xbmcgui.Dialog().notification('%s Error %s' % (plugin.name, r.status_code), msg, xbmcgui.NOTIFICATION_ERROR)
        traceback.print_exc()
