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
    utils.log("make-series-categories-list")

    cats = api.get_series_categories()
    for cat in cats:
        listitem = xbmcgui.ListItem(label=cat["title"])
        url = "%s?action=%s&id=%s&page=%s" % (base_url, SHOW_SERIES_CATEGORY, cat['id'], 1)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=listitem, isFolder=True)
        
    xbmcplugin.endOfDirectory(handle=addon_handle)

def make_films_categories_list(base_url, addon_handle, params):
    """ Creates TetPlus Films category list 
    """
    utils.log("make-films-categories-list")

    cats = api.get_films_categories()
    for cat in cats:
        listitem = xbmcgui.ListItem(label=cat["title"])
        url = "%s?action=%s&id=%s&page=%s" % (base_url, SHOW_FILMS_CATEGORY, cat['id'], 1)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=listitem, isFolder=True)
        
    xbmcplugin.endOfDirectory(handle=addon_handle)

def _add_pagination_folder(base_url, params, items, action):
    """Adds pagination folder as last item in list

    Args:
        base_url (str): 
        params (dict): id - id of series or films category
        items (list): existing item list 
        action (str): where to navigate?
    """
    if len(items) >= ITEMS_PER_PAGE:
        listitem = xbmcgui.ListItem(label="NEXT PAGE")
        url = "%s?action=%s&id=%s&page=%s" % (base_url, action, params["id"], str(int(params["page"])+1))
        items.append((url, listitem, True))

def make_category_series_list(base_url, addon_handle, params):
    """Display a list of series having specific category

    Args:
        base_url (str): 
        addon_handle (int): 
        params (dict):
    """
    utils.log("make_category_series_list")
    series = api.get_category_series(params)

    items = []
    for ser in series:
        listitem = xbmcgui.ListItem(label=ser["title"])
        listitem.setInfo('video', {'title': ser['title'], "plot": ser["description"]})
        listitem.setArt({"thumb": ser['image']}) 
        
        url = "%s?action=%s&id=%s" % (base_url, SHOW_SERIES_SEASONS, ser['id'])
        items.append((url, listitem, True))
 
    _add_pagination_folder(base_url, params, items, SHOW_SERIES_CATEGORY)
    
    xbmcplugin.addDirectoryItems(handle=addon_handle, items=items, totalItems=len(items))
    xbmcplugin.endOfDirectory(handle=addon_handle)

def make_category_films_list(base_url, addon_handle, params):
    """Display a list of films having specific category
    """
    utils.log("make_category_films_list")
    films = api.get_category_films(params)

    items = []
    for film in films:
        listitem = xbmcgui.ListItem(label=film["title"])
        listitem.setInfo('video', {'title': film['title'], "plot": film["description"]})
        listitem.setArt({"thumb": film['image']})
        listitem.setProperty('IsPlayable', "true")
        
        url = "%s?action=%s&data_url=%s&type=vod" % (base_url, PLAY_STREAM, film['id'])
        items.append((url, listitem, False))
    
    _add_pagination_folder(base_url, params, items, SHOW_FILMS_CATEGORY)
        
    xbmcplugin.setContent(handle=addon_handle, content='videos')
    xbmcplugin.addDirectoryItems(handle=addon_handle, items=items, totalItems=len(items))
    xbmcplugin.endOfDirectory(handle=addon_handle)

def make_series_seasons(base_url, addon_handle, params):
    """Display a list of series seasons to be selected

    Args:
        base_url (str): 
        addon_handle (int): 
        params (dict): id - series id to fetch episodes for
    """
    episodes_per_season = api.get_series_episodes(params["id"])
    
    items = []
    for season in episodes_per_season.keys():
        listitem = xbmcgui.ListItem(label="Season %s" % (season))
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
    
    items = []
    for e in episodes_per_season[params["season_id"]]:
        listitem = xbmcgui.ListItem(label=e["title"])
        listitem.setInfo('video', {'title': e['title'], "plot": e["description"]})
        listitem.setArt({"thumb": e['image']}) 
        listitem.setProperty('IsPlayable', "true")

        url = "%s?action=%s&data_url=%s&type=vod" % (base_url, PLAY_STREAM, e["id"])
        
        items.append((url, listitem, False))
    
    xbmcplugin.setContent(handle=addon_handle, content='videos')
    xbmcplugin.addDirectoryItems(handle=addon_handle, items=items, totalItems=len(items))
    xbmcplugin.endOfDirectory(handle=addon_handle)

# Ruby has Hash#except, another example that Ruby is superior 
def _without_keys(d, exclude_keys):
    return {k: d[k] for k in set(list(d.keys())) - set(exclude_keys)}

def make_continue_watching(base_url, addon_handle, params):
    utils.log(params["page"])
    cont_ids = api.get_continue_watching(params["page"])
    continues = api.get_vod_bulk(cont_ids)
    items = []
    for c in continues:
        if c["type"] == "series":
            listitem = xbmcgui.ListItem(label=c["title"])
            listitem.setInfo('video', _without_keys(c,["id","image","type"]))
            listitem.setArt({"thumb": c['image']}) 
            url = "%s?action=%s&id=%s&type=vod" % (base_url, SHOW_SERIES_SEASONS, c["id"])
            items.append((url, listitem, True))
        elif c["type"] == "movie":
            listitem = xbmcgui.ListItem(label=c["title"])
            listitem.setInfo('video', _without_keys(c,["id","image","type"]))
            listitem.setArt({"thumb": c['image']}) 
            listitem.setProperty('IsPlayable', "true")
            url = "%s?action=%s&data_url=%s&type=vod" % (base_url, PLAY_STREAM, c["id"])
            items.append((url, listitem, False))
    
    _add_pagination_folder(base_url, params, items, SHOW_CONTINUE_WATCHING)

    xbmcplugin.setContent(handle=addon_handle, content='videos')
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
  

def play_channel(base_url, addon_handle, params):
    utils.log("url play channel: " + base_url)

    try:
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
        if params["type"] == "vod":
            api.mark_vod_in_progress(params["data_url"])
            
        xbmcplugin.setResolvedUrl(addon_handle, True, playitem)

    except:
        d = xbmcgui.Dialog()
        msg = utils.dialog_error("Unable to fetch listing")
        d.ok(*msg)
        utils.log_error()

