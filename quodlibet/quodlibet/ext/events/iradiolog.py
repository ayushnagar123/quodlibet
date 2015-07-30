# -*- coding: utf-8 -*-
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import app
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons


class IRadioLog(EventPlugin):
    PLUGIN_ID = "Internet Radio Log"
    PLUGIN_NAME = _("Internet Radio Log")
    PLUGIN_DESC = _("Records the last 10 songs played on radio stations, "
                    "and lists them in the seek context menu.")
    PLUGIN_ICON = Icons.EDIT

    def plugin_on_song_started(self, song):
        if song is None:
            return

        player = app.player

        if player.song.multisong and not song.multisong:
            time = player.get_position()
            title = song("title")
            bookmarks = player.song.bookmarks
            bookmarks.append([time // 1000, title])
            try:
                bookmarks.pop(-10)
            except IndexError:
                pass
            player.song.bookmarks = bookmarks
        elif song.multisong:
            song.bookmarks = []
