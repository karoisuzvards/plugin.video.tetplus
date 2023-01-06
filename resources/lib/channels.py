import sys

import xbmcgui
import xbmcplugin

from . import api
from . import utils
from .constants import *

def make_series_categories_list(base_url, addon_handle, params):
    """ Creates TetPlus Series category list 

    Args:
        base_url (String): same as Kodi addon sys.argv[0]
        addon_handle (int): same as Kodi addon sys.argv[1]
        params (dict): url query params
    """
    utils.log("make-category-list")

    cats = api.get_series_categories()
    for cat in cats:
        listitem = xbmcgui.ListItem(label=cat["title"])
        url = "%s?action=%s&id=%s&page=%s" % (base_url, SHOW_CATEGORY, cat['id'], 1)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=listitem, isFolder=True)
        
    xbmcplugin.endOfDirectory(handle=addon_handle)

def make_category_series_list(base_url, addon_handle, params):
    """Display a list of series having specific category

    Args:
        base_url (str): 
        addon_handle (int): 
        params (dict):
    """
    utils.log("make-category-series-list")

    series = api.get_category_series(params)
    utils.log("Series")
    utils.log(series)

    items = []
    for ser in series:
        utils.log("Series item "+ser["title"])
        listitem = xbmcgui.ListItem(label=ser["title"])
        listitem.setInfo('video', {'title': ser['title'], "plot": ser["description"]})
        listitem.setArt({"thumb": ser['image']}) 
        
        url = "%s?action=%s&id=%s" % (base_url, SHOW_SERIES_SEASONS, ser['id'])
        items.append((url, listitem, True))
        
    xbmcplugin.addDirectoryItems(handle=addon_handle, items=items, totalItems=len(items))
    xbmcplugin.endOfDirectory(handle=addon_handle)

def make_series_seasons(base_url, addon_handle, params):
    """Display a list of series seasons to be selected

    Args:
        base_url (str): 
        addon_handle (int): 
        params (dict): having id - series id to fetch episodes for
    """
    episodes_per_season = api.get_series_episodes(params["id"])
    
    items = []
    for season in episodes_per_season.keys():
        listitem = xbmcgui.ListItem(label="Season #%s" % (season))
        url = "%s?action=%s&id=%s&season_id=%s" % (base_url, SHOW_SERIES_SEASON_DETAILS, params["id"], season)
        
        items.append((url, listitem, True))
    
    xbmcplugin.addDirectoryItems(handle=addon_handle, items=items, totalItems=len(items))
    xbmcplugin.endOfDirectory(handle=addon_handle)

def make_series_episodes(base_url, addon_handle, params):
    """Display a list of episodes after selecting season 

    Args:
        base_url (str): 
        addon_handle (int): 
        params (dict): 
            id - series id to fetch episodes for
            season - int season nr (starting with 1)
    """
    episodes_per_season = api.get_series_episodes(params["id"])
    
    utils.log(episodes_per_season)
    items = []
    for e in episodes_per_season[params["season_id"]]:
        listitem = xbmcgui.ListItem(label=e["title"])
        listitem.setInfo('video', {'title': e['title'], "plot": e["description"]})
        listitem.setArt({"thumb": e['image']}) 
        listitem.setProperty('IsPlayable', "true")

        url = "%s?action=%s&data_url=%s&type=vod" % (base_url, PLAY_STREAM, e["id"])
        
        items.append((url, listitem, False))
    
    xbmcplugin.setContent(handle=addon_handle, content='episodes')
    xbmcplugin.addDirectoryItems(handle=addon_handle, items=items, totalItems=len(items))
    xbmcplugin.endOfDirectory(handle=addon_handle)

def make_channel_list():
    utils.log("url-make-channel" + sys.argv[0])

    try:
        channels = api.get_channels()

        ok = True
        for c in channels:
            listitem = xbmcgui.ListItem(label=c['name'])
            listitem.setInfo('video', {'title': c['name']})
            listitem.setArt({"thumb": c['image']}) 
            listitem.setProperty('IsPlayable', "true")

            # Build the URL for the program, including the list_info
            url = "%s?action=%s&data_url=%s&type=channel" % (sys.argv[0], PLAY_STREAM, c['id'])

            # Add the program item to the list
            ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False,
                                             totalItems=len(channels))

        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=ok)
        xbmcplugin.setContent(handle=int(sys.argv[1]), content='episodes')
    except:
        d = xbmcgui.Dialog()
        msg = utils.dialog_error("Unable to fetch listing")
        d.ok(*msg)
        utils.log_error()
  

def play_channel():
    utils.log("url play channel: " + sys.argv[0])

    try:
        handle = int(sys.argv[1])
        params_str = sys.argv[2]
        params = utils.get_url(params_str)

        data_url = params['data_url']
        stream_info = api.get_stream_url(data_url, params["type"])

        playitem = xbmcgui.ListItem(path=stream_info['stream'])
        licToken = api.get_license_token(data_url, params["type"])
        
        playitem.setMimeType('application/xml+dash')
        playitem.setContentLookup(False)
        
        playitem.setProperty('inputstream', 'inputstream.adaptive')
        playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        playitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        playitem.setProperty('inputstream.adaptive.license_key', stream_info['licUrl']+"|tpar-sc-jwt="+licToken+"|R|R")
        
        xbmcplugin.setResolvedUrl(handle, True, playitem)

    except:
        d = xbmcgui.Dialog()
        msg = utils.dialog_error("Unable to fetch listing")
        d.ok(*msg)
        utils.log_error()

