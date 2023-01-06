import json
from . import config
from . import utils
from . import constants

from .exceptions import ApiError

import requests
from bs4 import BeautifulSoup


AUTH_API_URL = 'https://connect.tet.lv'

API_BASEURL = "https://api-prd.shortcut.lv"
MY_TV_BASE_URL = "https://manstv.lattelecom.tv/"

API_ENDPOINT = API_BASEURL + "/api"

S = requests.Session()


def req_headers():
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Kodi v19 (Matrix) - python3.requests',
        'Authorization': 'Bearer '+ config.get_token(),
        'Accept-Encoding': 'gzip, deflate, br',
        'X-Device-ID': '{"app":{"name":"Tet+","version":"2022_12_19-14_31_59-d62690b4"},"os":{"name":"Kodi","version":"v19.0.4"},"browser":{"name":"Firefox","version":"108.0"}}'
    }
    

def login(force=False):
    utils.log("User: " + config.get_username() + "; Logged in: " + str(config.is_logged_in()) + "; Token: " + config.get_token())

    if force is False and not utils.isEmpty(config.get_token()) and config.is_logged_in():
        utils.log("Already logged in")
        return

    # Step 1. Issue a get request to get magic JWT token from login form 
    
    secret_key = config.get_secret_key()
        
    url_params = {
        'lang': 'lv',
        'response_type': 'code',
        'client_id': 'shortcut',
        'state': '{"redirectUri":"https://tet.plus/login","secretKey":"'+secret_key+'"}',
        'redirect_uri': 'https://api-prd.shortcut.lv/api/users/connect/mtet/callback'
    }
    headers = {
        'Accept': "*/*",
    }

    response1 = S.get(
        AUTH_API_URL + '/authorize',
        params=url_params,
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
    
    response = S.post(
        AUTH_API_URL + '/authorize',
        params=url_params,
        data=form_data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded", 
            "Accept": "*/*",
        }
    )
    
    if response.status_code != 200:
        raise ApiError(
            "Got incorrect response code during login. Reponse code: " + response.status_code + "; Text: " +  response.text)

    token = [param.replace("token=","") for param in response.url.split("&") if param.startswith("token")][0]
    
    config.set_logged_in(True)
    config.set_token(token)

    utils.log("Login success!")
    return True

def get_series_categories():
    config.login_check()
    
    response = S.get(MY_TV_BASE_URL + "api/v1.11/get/content/pages/series_web/?include=items&filter%5Blang%5D=en", headers=req_headers())
    
    # TODO: try out decorator
    if response.status_code != 200:
        raise ApiError(
            "Got incorrect response code while requesting categories of series. Response code: %s ;\nText: %s" % (response.status_code, response.text)
        )
    
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
    utils.log(params)
    response = S.get(
        MY_TV_BASE_URL + "api/v1.11/get/content/categories/%s?include=items,items.channel&page[number]=%s&filter[lang]=en" % (params["id"], params["page"]),
        headers=req_headers()
    )
     # TODO: try out decorator
    if response.status_code != 200:
        raise ApiError(
            "Got incorrect response code while requesting category series. Response code: %s ;\nText: %s" % (response.status_code, response.text)
        )
    
    series = []
    for item in response.json()["included"]:
        series.append({
            "id": item["attributes"]["series-id"],
            "title": item["attributes"]["series-name"],
            "description":  item["attributes"]["description"],
            "image": "%s/images/vod/%s/poster-large?width=555" % (API_ENDPOINT, item["id"])
        })
        
    return series

def get_series_episodes(series_id, page_size=1000, lang="en"):
    response = S.get(
        MY_TV_BASE_URL + "api/v1.11/get/content/episodes/%s?page[size]=%s&filter[lang]=%s" % (series_id, page_size, lang),
        headers=req_headers()
    )
    # TODO: try out decorator
    if response.status_code != 200:
        raise ApiError(
            "Got incorrect response code while requesting channel list. Response code: %s ;\nText: %s" % (response.status_code, response.text)
        )
        
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
    return {
        "id": episode["id"],
        "image": "%s/images/vod/%s/poster-large?width=555" % (API_ENDPOINT, episode["id"]),
        "title": episode["attributes"]["episode-name"],
        "description": episode["attributes"]["description"],
    }

def get_channels():
    config.login_check()

    url = API_ENDPOINT + '/packaging/services?flattenBundles=true'
    response = S.get(url, headers=req_headers())

    response_text = response.text
    response_code = response.status_code

    if response_code != 200:
        raise ApiError(
            "Got incorrect response code while requesting channel list. Reponse code: " + response_code + ";\nText: " + response_text)

    channels = []
    for item in response.json():
        if "type" not in item or "id" not in item:
            continue

        channels.append({
            'id': item["id"],
            'name': item["title"],
            'image': API_ENDPOINT + "/images/channel/"+str(item['id'])+"/logo/dark?height=200"
        })

    return channels


def get_stream_url(data_url, channel_or_vod):
    utils.log("Getting URL for channel: " + data_url)
    config.login_check()

    url = API_ENDPOINT + "/stream/v2/%s/%s" % (channel_or_vod, data_url)
    
    response = S.get(url, headers=req_headers())

    response_text = response.text
    response_code = response.status_code

    if response_code != 200:
        config.set_setting_bool(constants.LOGGED_IN, False)
        raise ApiError(
            "Got incorrect response code while requesting stream info. Response code: %s;\nText: %s" % (response_code, response_text)
        )

    json_object = response.json()
    
    return { 'stream': json_object["streams"]["dash"], 'licUrl': json_object["drm"]["com.widevine.alpha"] }

def get_license_token(data_url, channel_or_vod):
    utils.log("Getting Licence token for channel: " + data_url)
    config.login_check()
    
    # because API
    if channel_or_vod == "vod":
        channel_or_vod = "svod"

    url = API_ENDPOINT + "/access-rights/resource-auth/%s/%s" % (channel_or_vod, data_url)
    response = S.get(url, headers=req_headers())

    response_text = response.text
    response_code = response.status_code

    if response_code != 200:
        config.set_setting_bool(constants.LOGGED_IN, False)
        raise ApiError(
            "Got incorrect response code while requesting licence token. Response code: %s;\nText: %s" % (response_code, response_text)
        )
    
    utils.log(response.status_code)
    utils.log(response.text)

    return response.json()["token"]


def get_epg(date):
    utils.log("Getting EPG for date: " + date)

    timestampFrom = utils.unixTSFromDateString(date)
    timestampTo=int(timestampFrom+86400)

    url = API_ENDPOINT + "/get/content/epgs/?include=channel&page[size]=100000&filter[utTo]="+str(timestampTo)+"&filter[utFrom]="+str(timestampFrom)
    opener = None
    response = opener.open(url)

    response_text = response.read()
    response_code = response.getcode()

    if response_code != 200:
        raise ApiError("Got bad response from EPG service. Response code: " + response_code)

    json_object = None
    try:
        json_object = json.loads(response_text)
    except ValueError as e:
        raise ApiError("Did not receive json, something wrong: " + response_text)

    return json_object
