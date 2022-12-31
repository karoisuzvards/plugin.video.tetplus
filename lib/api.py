import json
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
from . import config
from . import utils
from . import constants

from .exceptions import ApiError

import requests
from bs4 import BeautifulSoup

try:
    import xbmc, xbmcplugin
except:
    pass

AUTH_API_URL = 'https://connect.tet.lv'

API_BASEURL = "https://api-prd.shortcut.lv"
API_ENDPOINT = API_BASEURL + "/api"

# TODO: move to requests
def get_url_opener():
    opener = urllib.request.build_opener()
    # Headers from Firefox 107
    opener.addheaders = [
        ('User-Agent',
	'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:107.0) Gecko/20100101 Firefox/108.0'),
        ('Content-Type', 'application/json'),
        ('Accept', 'application/json'),
        ('Authorization', 'Bearer '+ config.get_token()),
        ('X-Device-ID','{"app":{"name":"Tet+","version":"2022_12_19-14_31_59-d62690b4"},"os":{"name":"Mac","version":"mac-os-x-15"},"browser":{"name":"Firefox","version":"108.0"}}'),
    ]
    return opener


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

    response1 = requests.get(
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
    
    response = requests.post(
        AUTH_API_URL + '/authorize',
        params=url_params,
        data=form_data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded", 
            "Accept": "*/*",
            'Cookie': response1.headers["Set-Cookie"],
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


def get_channels():
    config.login_check()

    url = API_ENDPOINT + '/packaging/services?flattenBundles=true'
    opener = get_url_opener()
    response = opener.open(url)
    response_text = response.read()
    response_code = response.getcode()

    if response_code != 200:
        raise ApiError(
            "Got incorrect response code while requesting channel list. Reponse code: " + response_code + ";\nText: " + response_text)

    json_object = None
    try:
        json_object = json.loads(response_text)
    except ValueError as e:
        raise ApiError("Did not receive json, something wrong: " + response_text)

    channels = []
    for item in json_object:
        if "type" not in item or "id" not in item:
            continue

        channels.append({
            'id': item["id"],
            'name': item["title"],
        })

    return channels


def get_stream_url(data_url):
    utils.log("Getting URL for channel: " + data_url)
    config.login_check()

    url = API_ENDPOINT + "/stream/v2/channel/" + data_url
    opener = get_url_opener()
    response = opener.open(url)

    response_text = response.read()
    response_code = response.getcode()

    if response_code != 200:
        config.set_setting_bool(constants.LOGGED_IN, False)
        raise ApiError(
            "Got incorrect response code while requesting stream info. Reponse code: " + response_code + ";\nText: " + response_text)

    json_object = None
    try:
        json_object = json.loads(response_text)
    except ValueError as e:
        config.set_setting(constants.LOGGED_IN, False)
        raise ApiError("Did not receive json, something wrong: " + response_text)

    return { 'stream': json_object["streams"]["dash"], 'licUrl': json_object["drm"]["com.widevine.alpha"] }

def get_license_token(data_url):
    utils.log("Getting Licence token for channel: " + data_url)
    config.login_check()

    url = API_ENDPOINT + "/access-rights/resource-auth/channel/" + data_url
    opener = get_url_opener()
    response = opener.open(url)

    response_text = response.read()
    response_code = response.getcode()

    if response_code != 200:
        config.set_setting_bool(constants.LOGGED_IN, False)
        raise ApiError(
            "Got incorrect response code while requesting licence token. Reponse code: " + response_code + ";\nText: " + response_text)

    json_object = None
    try:
        json_object = json.loads(response_text)
    except ValueError as e:
        config.set_setting(constants.LOGGED_IN, False)
        raise ApiError("Did not receive json, something wrong: " + response_text)

    return json_object["token"]


def get_epg(date):
    utils.log("Getting EPG for date: " + date)

    timestampFrom = utils.unixTSFromDateString(date)
    timestampTo=int(timestampFrom+86400)

    url = API_ENDPOINT + "/get/content/epgs/?include=channel&page[size]=100000&filter[utTo]="+str(timestampTo)+"&filter[utFrom]="+str(timestampFrom)
    opener = get_url_opener()
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
