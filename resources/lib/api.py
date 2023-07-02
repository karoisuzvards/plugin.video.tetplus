import json
from datetime import timedelta
from . import config
from . import constants
from . import utils
from functools import reduce
import xbmcvfs
import xbmcaddon

from .exceptions import ApiError

import requests
from requests_cache import CachedSession
from bs4 import BeautifulSoup

# on osmc 2022.11 build need to lower SSL ciphers - as manstv uses some old ones
import urllib3

requests.packages.urllib3.disable_warnings()
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
try:
    requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
except AttributeError:
    # no pyopenssl support used / needed / available
    pass

AUTH_API_URL = 'https://connect.tet.lv'

API_BASEURL = "https://api-prd.shortcut.lv"
MY_TV_BASE_URL = "https://manstv.lattelecom.tv/"

API_ENDPOINT = API_BASEURL + "/api"

API_ENDPOINTS_NOT_TO_CACHE = ["user-video-profile/time", "users/profile", "authorize" ]

def should_not_cache_request(req_url):
    return any(url in req_url for url in API_ENDPOINTS_NOT_TO_CACHE)

def skip_cache_for_following_requests(response):
    if should_not_cache_request(response.request.url):
        utils.log("Skipping cache for: "+response.request.url)
        return False
    
    utils.log("Caching HTTP req: "+response.request.url)
    return True

# lazy init and memoize - otherwise crash on startup
GLOBAL_SESSION = None

def cached_session():
    global GLOBAL_SESSION
    if GLOBAL_SESSION is None:
        GLOBAL_SESSION = CachedSession(xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))+ '/http_cache',
            cache_control=True,
            expire_after=timedelta(days=1),
            allowable_methods=['GET'],
            allowable_codes=[200],
            match_headers=False,               
            stale_if_error=False,
            filter_fn=skip_cache_for_following_requests
        )
    return GLOBAL_SESSION

def _req_headers():
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Kodi v19 (Matrix) - python3.requests',
        'Authorization': 'Bearer '+ config.get_token(),
        'Accept-Encoding': 'gzip, deflate, br',
        'X-Device-ID': '{"app":{"name":"Tet+","version":"2022_12_19-14_31_59-d62690b4"},"os":{"name":"Kodi","version":"v19.0.4"},"browser":{"name":"Firefox","version":"108.0"}}'
    }
    
def _default_url_params():
    return {
        "lang": config.get_language()
    }
    
def _handle_status_code(response, operation):
    if response.status_code == 401:
        config.logout()
    elif response.status_code not in range(200,300):
        raise ApiError(
            "Got incorrect response code during %s. Reponse code: %s; Text: %s" % (operation, response.status_code, response.text)
        )

def login(force=False):
    utils.log("User: " + config.get_username() + "; Logged in: " + str(config.is_logged_in()) + "; Token: " + config.get_token())

    if force is False and not utils.isEmpty(config.get_token()) and config.is_logged_in():
        utils.log("Already logged in")
        return

    # Step 1. Issue a get request to get magic JWT token from login form 
    
    cached_session().cache.clear()
    
    secret_key = config.get_secret_key()
        
    url_params = {
        'response_type': 'code',
        'client_id': 'shortcut',
        'state': '{"redirectUri":"https://tet.plus/login","secretKey":'+secret_key+'}',
        'redirect_uri': 'https://api-prd.shortcut.lv/api/users/connect/mtet/callback'
    }
    headers = {
        'Accept': "*/*",
    }

    response1 = cached_session().get(
        AUTH_API_URL + '/authorize',
        params={**_default_url_params(), **url_params},
        headers=headers,
    )
    # get magic token from login form
    soup = BeautifulSoup(response1.text, 'html.parser')
    login_token = soup.find(id="login__token").get("value")
    
    # Step 2. Issue a POST request with proper token and secret key

    form_data = {
        'login[username]': config.get_username(),
        'login[password]': config.get_password(),
        'login[facebook_id]': "", 
        'login[apple_id]': "", 
        'login[_token]': login_token, 
    }
    
    response = cached_session().post(
        AUTH_API_URL + '/authorize',
        params=url_params,
        data=form_data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded", 
            "Accept": "*/*",
        } 
    )

    _handle_status_code(response, "login")

    token = [param.replace("token=","") for param in response.url.split("&") if param.startswith("token")][0]
    
    config.set_logged_in(True)
    config.set_token(token)

    utils.log("Login success!")
    return True

def get_user_profile():
    response = cached_session().get(API_ENDPOINT + "/users/profile", params=_default_url_params(), headers=_req_headers())
    return response.status_code
    
def get_series_categories():
    config.login_check()
    
    response = cached_session().get(
        MY_TV_BASE_URL + "api/v1.11/get/content/pages/series_web/",
        params={"include":"items", "filter[lang]": config.get_language()}, 
        headers=_req_headers()
    )
    
    _handle_status_code(response, "get series categories")
    
    categories = []
    for cat in response.json()["data"]:
        categories.append(
            {
                "id": cat["id"],
                "title": cat["attributes"]["title"]
            }
        )
    
    return categories

def get_films_categories():
    config.login_check()
    
    response = cached_session().get(
        MY_TV_BASE_URL + "api/v1.11/get/content/pages/films_web/",
        params={"include": "items", "filter[lang]": config.get_language()},
        headers=_req_headers()
    )
    
    _handle_status_code(response, "get films categories")
    
    categories = []
    for cat in response.json()["data"]:
        categories.append(
            {
                "id": cat["id"],
                "title": cat["attributes"]["title"]
            }
        )
    
    return categories

def get_category_series(params):
    utils.log("Get category series for "+str(params))
    response = cached_session().get(
        MY_TV_BASE_URL + f"api/v1.11/get/content/categories/{params['id']}",
        params={"include": "items,items.channel", "page[number]": params['page'], "filter[lang]": config.get_language()},
        headers=_req_headers()
    )
    
    _handle_status_code(response, "get category series")
    
    series = []
    for item in response.json()["included"]:
        series.append({
            "id": item["attributes"]["series-id"],
            "title": item["attributes"]["series-name"],
            "description":  item["attributes"]["description"],
            "image": "%s/images/vod/%s/poster-large?width=555" % (API_ENDPOINT, item["id"])
        })
        
    return series

def get_category_films(params):
    utils.log("Get category series for "+str(params))
    response = cached_session().get(
        MY_TV_BASE_URL + f"api/v1.11/get/content/categories/{params['id']}",
        params={"include":"items,items.channel", "page[number]": params['page'], "filter[lang]": config.get_language()},
        headers=_req_headers()
    )
    
    _handle_status_code(response, "get category series")
    
    series = []
    for item in response.json()["included"]:
        series.append({
            "id": item["id"],
            "title": item["attributes"]["title-localized"],
            "plot":  item["attributes"]["description"],
            "image": "%s/images/vod/%s/poster-large?width=555" % (API_ENDPOINT, item["id"]),
            "rating": float(item["attributes"]["imdb-rating"]) if "imdb-rating" in item["attributes"].keys() else 0.0,
            "duration": int(item["attributes"]["length"]) * 60,
            "genres": item["attributes"]["genres"],
            "year": item["attributes"]["year"],
            "director": item["attributes"]["directors"],
            "cast": item["attributes"]["actors"],
            "mediatype": "movie"
        })
        
    return series

def get_series_episodes(series_id, page_size=1000):
    response = cached_session().get(
        MY_TV_BASE_URL + f"api/v1.11/get/content/episodes/{series_id}",
        params={"page[size]": page_size, "filter[lang]": config.get_language()},
        headers=_req_headers()
    )
    
    _handle_status_code(response, "get series episodes")
        
    episodes_per_season = {}    
    for episode in response.json()["data"]:
        season_nr = episode["attributes"]["season-nr"]
        if season_nr in episodes_per_season.keys():
            episodes_per_season[season_nr].append(_add_episode(episode))
        else:
            episodes_per_season[season_nr] = []
            episodes_per_season[season_nr].append(_add_episode(episode))
        
    return episodes_per_season

def _add_episode(episode):
    episode_attrs = episode["attributes"]
    return {
        "id": episode["id"],
        "image": "%s/images/vod/%s/poster-large?width=555" % (API_ENDPOINT, episode["id"]),
        "title": "S%sE%s - %s" % (episode_attrs["season-nr"], episode_attrs["episode-nr"], episode_attrs["episode-name"]),
        "plot": episode_attrs["description"],
        "year": episode_attrs["year"],
        "genre": episode_attrs["genres"],
        "cast": episode_attrs["actors"] if "actors" in episode_attrs.keys() else [],
        "director": episode_attrs["directors"] if "directors" in episode_attrs.keys() else [],
        "rating": "(IMDB: %s)" % episode_attrs["imdb-rating"] if "imdb-rating" in episode_attrs.keys() else "",
        "season": episode_attrs["season-nr"],
        "episode": episode_attrs["episode-nr"],
        "duration": episode_attrs["content-stop-time"] if "content-stop-time" in episode_attrs.keys() else "",
        "imdbnumber": episode_attrs["imdb-link"] if "imdb-link" in episode_attrs.keys() else ""
    }

def get_channels():
    config.login_check()

    url = API_ENDPOINT + '/packaging/services?flattenBundles=true'
    response = cached_session().get(url, headers=_req_headers(), params=_default_url_params())

    _handle_status_code(response, "get channels")

    channels = []
    for item in response.json():
        if item["type"] != "tv-channel":
            continue

        channels.append({
            'id': item["id"],
            'name': item["title"],
            'image': API_ENDPOINT + "/images/channel/"+str(item['id'])+"/logo/dark?height=200",
            "group": (item["group"] if "group" in item else "No Group") 
        })

    return channels

def get_continue_watching(page):
    config.login_check()

    url = API_ENDPOINT + '/user-video-profile/time'
    url_params = { "contentType": "vod", "pageIndex": page, "pageSize":"20"}
    response = cached_session().get(url, headers=_req_headers(), params=url_params)
    
    _handle_status_code(response, "get continue watching")
    
    return list(map(lambda cont: cont["id"], response.json()))
       
def get_vod_bulk(list_of_ids):
    ids_url_params = reduce(lambda acc,id: acc+"id="+str(id)+"&", list_of_ids, "")
    url = API_ENDPOINT + '/vod/bulk?' + ids_url_params + f"lang={config.get_language()}"
    response = cached_session().get(url, headers=_req_headers())
    
    _handle_status_code(response, "get vod bulk: "+ids_url_params)
    
    vods = []
    for vod in response.json():
        if vod["type"] == "series" or vod["type"] == "tv show":
            vods.append({
                "type": "series",
                "id": vod["series"]["id"],
                "title": vod["title"],
                "plot": vod["description"] if "description" in vod.keys() else "",
                "image": "%s/images/vod/%s/poster-large?width=555" % (API_ENDPOINT, vod["id"]),
                "year": vod["year"],
                "genre": vod["genres"],
                "cast": vod["actors"] if "actors" in vod.keys() else [],
                "director": vod["directors"] if "directors" in vod.keys() else [],
                "rating": vod["imdbRating"] if "imdbRating" in vod.keys() else 0.0,
                "season": vod["episode"]["seasonNr"],
                "episode": vod["episode"]["episodeNr"],
                "duration": vod["duration"] * 60,
                "imdbnumber": vod["imdbLink"] if "imdbLink" in vod.keys() else ""
            })
        elif vod["type"] == "movie":
            vods.append({
                "type": "movie",
                "id": vod["id"],
                "title": vod["title"],
                "plot": vod["description"] if "description" in vod.keys() else "",
                "image": "%s/images/vod/%s/poster-large?width=555" % (API_ENDPOINT, vod["id"]),
                "year": vod["year"],
                "genre": vod["genres"],
                "cast": vod["actors"] if "actors" in vod.keys() else [],
                "director": vod["directors"] if "directors" in vod.keys() else [],
                "rating": vod["imdbRating"] if "imdbRating" in vod.keys() else 0.0,
                "imdbnumber": vod["imdbLink"] if "imdbLink" in vod.keys() else "",
                "duration": vod["duration"]
            })
            
    return vods

def mark_vod_in_progress(id):
    url = API_ENDPOINT + "/user-video-profile/time/vod/%s" % (id)
    payload = { "position": 189 } # TODO: check if vod watch status update be properly implemented
    response = cached_session().put(url, headers=_req_headers(), data=json.dumps(payload))
    
    _handle_status_code(response, "mark vod in progress")

def get_stream_url(data_url, channel_or_vod):
    utils.log("Getting URL for channel: " + data_url)
    config.login_check()

    url = API_ENDPOINT + "/stream/v2/%s/%s" % (channel_or_vod, data_url)
    
    response = cached_session().get(url, headers=_req_headers(), params=_default_url_params())

    _handle_status_code(response, "get stream url")

    json_object = response.json()
    
    return { 'stream': json_object["streams"]["dash"], 'licUrl': json_object["drm"]["com.widevine.alpha"] }

def get_license_token(data_url, channel_or_vod):
    utils.log("Getting Licence token for channel: " + data_url)
    config.login_check()
    
    # because API
    if channel_or_vod == "vod":
        channel_or_vod = "svod"

    url = API_ENDPOINT + "/access-rights/resource-auth/%s/%s" % (channel_or_vod, data_url)
    response = cached_session().get(url, headers=_req_headers())

    _handle_status_code(response, "get license token")

    return response.json()["token"]


def get_epg(timestampFrom,timestampTo ):
    utils.log("Getting EPG for date: %s - %s" % (timestampFrom,timestampTo))
    
    url_params = {
        "from": timestampFrom,
        "to": timestampTo
    }

    url = API_ENDPOINT + "/epg/lv"
    response = cached_session().get(url, params={**_default_url_params(), **url_params}, headers=_req_headers())

    _handle_status_code(response, "get epg")

    return response.json()
