'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import re
import sys
import xbmc, xbmcaddon

class Plugin(object):
  def __init__(self):
    self._routes = []
    self._addon = xbmcaddon.Addon()
    self.handle = int(sys.argv[1])
    self.addon_id = self._addon.getAddonInfo('id')
    self.path = self._addon.getAddonInfo('path')
  
  def get_setting(self, key):
    return self._addon.getSetting(id=key)

  def set_setting(self, key, val):
      self._addon.getSetting
  
  def build_url(self, path):
    return 'plugin://%s%s' % (self.addon_id, path)
  
  def route_for(self, path):
    uri_self = 'plugin://%s' % self.addon_id
    if path.startswith(uri_self):
      path = path.split(uri_self, 1)[1]
    for rule in self._routes:
      view_func, items = rule.match(path)
      if view_func:
        return view_func
    raise Exception('route_for: no route for path <%s>' % path)

  def url_for(self, func, **kwargs):
    for rule in self._routes:
      if rule._view_func is func:
        path = rule.make_path(**kwargs)
        url = self.build_url(path)
        return url
    return None

  def route(self, url_rule):
    def decorator(f):
      rule = UrlRule(url_rule, f)
      self._routes.append(rule)
      return f
    return decorator
  
  def run(self):
    path = sys.argv[0].split('plugin://%s' % self.addon_id)[1] or '/'
    self._dispatch(path)
  
  def redirect(self, path):
    self._dispatch(path)
  
  def _dispatch(self, path):
    for rule in self._routes:
      view_func, kwargs = rule.match(path)
      if view_func:
        view_func(**kwargs)
        return
    raise Exception('no route for path')

class UrlRule(object):
  def __init__(self, url_rule, view_func):
    self._view_func = view_func
    self._url_format = re.sub('<(?:[^:]+:)?([A-z]+)>', '{\\1}', url_rule)

    p = re.sub('<([A-z]+)>', '<string:\\1>', url_rule)
    p = re.sub('<string:([A-z]+)>', '(?P<\\1>[^/]+?)', p)
    p = re.sub('<path:([A-z]+)>', '(?P<\\1>.*)', p)
    self._pattern = p
    self._regex = re.compile('^' + p + '$')
  
  def match(self, path):
    m = self._regex.search(path)
    if not m:
      return False, None
    return self._view_func, m.groupdict()

  def make_path(self, **kwargs):
    return self._url_format.format(**kwargs)
