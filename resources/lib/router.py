from resources.lib.constants import *
from resources.lib.channels import *
import xbmcgui
import xbmcplugin
from . import config 
from . import epg 
from . import utils


def router(base_url, addon_handle, params):
    """
    Router function that calls other functions
    depending on the provided paramdict
    :param base_url string
    :param addon_handle string
    :param params dict
    :return:
    """
    _handle_addon_handles(addon_handle)
    # Check the parameters passed to the plugin
    xbmcplugin.setContent(handle=addon_handle, content='videos')
    if params:
        if params['action'] == SHOW_LIVE_CHANNELS:
            # Display the list of videos in a provided category.
            make_channel_list()
        elif params['action'] == SHOW_SERIES:
            make_series_categories_list(base_url, addon_handle, params)
        elif params['action'] == SHOW_FILMS:
            make_films_categories_list(base_url, addon_handle, params)
        elif params['action'] == PLAY_STREAM:
            play_channel(base_url, addon_handle, params)
        elif params['action'] == SHOW_SERIES_CATEGORY:
            make_category_series_list(base_url, addon_handle, params)
        elif params['action'] == SHOW_FILMS_CATEGORY:
            make_category_films_list(base_url, addon_handle, params)
        elif params['action'] == SHOW_SERIES_SEASONS:
            make_series_seasons(base_url, addon_handle, params)
        elif params["action"] == SHOW_SERIES_SEASON_DETAILS:
            make_series_episodes(base_url, addon_handle, params)
        elif params["action"] == SHOW_CONTINUE_WATCHING:
            make_continue_watching(base_url, addon_handle, params)
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        make_main_menu(base_url, addon_handle)

def make_main_menu(base_url, addon_handle):
    continue_watch = xbmcgui.ListItem(label="Continue Watching")
    continue_watch_url = "%s?action=%s&page=0&id=0" % (base_url, SHOW_CONTINUE_WATCHING)
    xbmcplugin.addDirectoryItem(handle=int(addon_handle), url=continue_watch_url, listitem=continue_watch, isFolder=True)
    
    movies = xbmcgui.ListItem(label="Live TV")
    movies_url = "%s?action=%s" % (base_url, SHOW_LIVE_CHANNELS)
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=movies_url, listitem=movies, isFolder=True)
    
    series = xbmcgui.ListItem(label="Series")
    series_url = "%s?action=%s" % (base_url, SHOW_SERIES)
    xbmcplugin.addDirectoryItem(handle=int(addon_handle), url=series_url, listitem=series, isFolder=True)
    
    films = xbmcgui.ListItem(label="Films")
    films_url = "%s?action=%s" % (base_url, SHOW_FILMS)
    xbmcplugin.addDirectoryItem(handle=int(addon_handle), url=films_url, listitem=films, isFolder=True)
    
    xbmcplugin.endOfDirectory(handle=int(addon_handle))

def _handle_addon_handles(addon_handle):
    if addon_handle == REFRESH_TOKEN:
        config.logout()
        exit(0)
    elif addon_handle == REBUILD_EPG:
        epg.build_epg()
        exit(0)
    elif addon_handle == CONFIGURE_EPG:
        epg.configure_epg()
        exit(0)