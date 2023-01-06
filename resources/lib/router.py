from resources.lib.constants import SHOW_SERIES,SHOW_LIVE_CHANNELS,PLAY_STREAM,REBUILD_EPG,REFRESH_TOKEN,CONFIGURE_EPG
from resources.lib.channels import make_channel_list, make_series_list, play_channel
import xbmcgui
import xbmcplugin
from . import config 
from . import epg 

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
            # Play a video from a provided URL.
            make_series_list()
        elif params['action'] == PLAY_STREAM:
            play_channel()
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        make_main_menu(base_url, addon_handle)

def make_main_menu(base_url, addon_handle):
    movies = xbmcgui.ListItem(label="Live TV")
    movies_url = "%s?action=%s" % (base_url, SHOW_LIVE_CHANNELS)
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=movies_url, listitem=movies, isFolder=True)
    
    series = xbmcgui.ListItem(label="Series")
    series_url = "%s?action=%s" % (base_url, SHOW_SERIES)
    xbmcplugin.addDirectoryItem(handle=int(addon_handle), url=series_url, listitem=series, isFolder=True)
    
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