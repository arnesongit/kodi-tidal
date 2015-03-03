# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2015 Thomas Amland
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

import re
import sys
import xbmc
import xbmcaddon
import urlparse
from urllib import urlencode

_addon_id = xbmcaddon.Addon().getAddonInfo('id')

_log_tag = "[%s][routing] " % _addon_id
log = lambda msg: xbmc.log(_log_tag + msg, level=xbmc.LOGDEBUG)


class RoutingError(Exception):
    pass


class Plugin(object):

    def __init__(self):
        self._rules = {}  # function to list of rules
        self.handle = int(sys.argv[1])
        self.addon_id = _addon_id
        self.args = None

    def route_for(self, path):
        """ Returns the view function for path. """
        uri_self = 'plugin://%s' % self.addon_id
        if path.startswith(uri_self):
            path = path.split(uri_self, 1)[1]

        for view_fun, rules in self._rules.iteritems():
            for rule in rules:
                if rule.match(path) is not None:
                    return view_fun
        raise RoutingError("No route for path '%s'" % path)

    def url_for(self, func, *args, **kwargs):
        """
        Construct and returns an URL for view function with give arguments.
        """
        if func in self._rules:
            for rule in self._rules[func]:
                path = rule.make_path(*args, **kwargs)
                if path is not None:
                    return self.url_for_path(path)
        raise RoutingError("No known paths to '{0}' with args {1} and kwargs {2}"
                        .format(func.__name__, args, kwargs))

    def url_for_path(self, path):
        """ Returns the complete URL for a path. """
        path = path if path.startswith('/') else '/' + path
        res = 'plugin://%s%s' % (self.addon_id, path)
        return res

    def route(self, pattern):
        """ Register a route. """
        def decorator(func):
            rule = UrlRule(pattern)
            if func not in self._rules:
                self._rules[func] = []
            self._rules[func].append(rule)
            return func
        return decorator

    def run(self):
        self.args = urlparse.parse_qs(sys.argv[2].lstrip('?'))
        path = sys.argv[0].split('plugin://%s' % self.addon_id)[1] or '/'
        self._dispatch(path)

    def redirect(self, path):
        self._dispatch(path)

    def _dispatch(self, path):
        for view_func, rules in self._rules.iteritems():
            for rule in rules:
                kwargs = rule.match(path)
                if kwargs is not None:
                    log("Dispatching to '%s', args: %s" % (view_func.__name__, kwargs))
                    view_func(**kwargs)
                    return
        raise RoutingError('No route to path "%s"' % path)


class UrlRule(object):

    def __init__(self, pattern):
        kw_pattern = r'<(?:[^:]+:)?([A-z]+)>'
        self._pattern = re.sub(kw_pattern, '{\\1}', pattern)
        self._keywords = re.findall(kw_pattern, pattern)

        p = re.sub('<([A-z]+)>', '<string:\\1>', pattern)
        p = re.sub('<string:([A-z]+)>', '(?P<\\1>[^/]+?)', p)
        p = re.sub('<path:([A-z]+)>', '(?P<\\1>.*)', p)
        self._compiled_pattern = p
        self._regex = re.compile('^' + p + '$')

    def match(self, path):
        """
        Check if path matches this rule. Returns a tuple of the view function
        and a dictionary of the extracted arguments, otherwise None.
        """
        path = urlparse.urlsplit(path).path
        match = self._regex.search(path)
        if match:
            return match.groupdict()
        return None

    def make_path(self, *args, **kwargs):
        """Construct a path from arguments."""
        if args and kwargs:
            return None  # can't use both args and kwargs
        if args:
            # Replace the named groups %s and format
            try:
                return re.sub(r'{[A-z]+}', r'%s', self._pattern) % args
            except TypeError:
                return None

        # We need to find the keys from kwargs that occur in our pattern.
        # Unknown keys are pushed to the query string.
        url_kwargs = dict(((k, v) for k, v in kwargs.items() if k in self._keywords))
        qs_kwargs = dict(((k, v) for k, v in kwargs.items() if k not in self._keywords))

        query = '?' + urlencode(qs_kwargs) if qs_kwargs else ''
        try:
            return self._pattern.format(**url_kwargs) + query
        except KeyError:
            return None

    def __str__(self):
        return b"Rule(pattern=%s, keywords=%s)" % (self._pattern, self._keywords)
