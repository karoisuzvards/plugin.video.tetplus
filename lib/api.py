import json
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
from . import config
from . import utils
from . import constants
import time
import datetime
import ssl

from .exceptions import ApiError

try:
    import xbmc, xbmcplugin
except:
    pass

API_BASEURL = "https://api-prd.shortcut.lv"
API_ENDPOINT = API_BASEURL + "/api"

def get_url_opener(referrer=None):
    opener = urllib.request.build_opener()
    # Headers from Firefox 107
    opener.addheaders = [
        ('User-Agent',
	'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:107.0) Gecko/20100101 Firefox/107.0'),
        ('Content-Type', 'application/json'),
        ('Accept', 'application/json'),
        ('Authorization','Bearer <you_wish>'),
        ('X-Device-ID','{"app":{"name":"Tet+","version":"2022_12_19-14_31_59-d62690b4"},"os":{"name":"Mac","version":"mac-os-x-15"},"browser":{"name":"Firefox","version":"108.0"}}'),
    ]
    return opener


def login(force=False):
    utils.log("User: " + config.get_setting(constants.USERNAME) + "; Logged in: " + str(config.get_setting_bool(
        constants.LOGGED_IN)) + "; Token: " + config.get_setting(constants.TOKEN))

    if force is False and not utils.isEmpty(config.get_setting(constants.TOKEN)) and config.get_setting_bool(constants.LOGGED_IN):
        utils.log("Already logged in")
        return

    opener = get_url_opener()

    values = {'id': config.get_setting(constants.USERNAME),
              'uid': config.get_unique_id(),
              'password': config.get_setting(constants.PASSWORD)}

    response = opener.open(API_ENDPOINT + '/post/user/users', urllib.parse.urlencode(values).encode("utf-8"))

    response_code = response.getcode()
    response_text = response.read()

    if response_code == 422:
        raise ApiError("Login failed, Status: 422 Unprocessable Entity. Did you enter username/password?")

    if response_code == 401:
        raise ApiError("Login failed, Status: 401 unauthorized. Check your username/password")

    if response_code != 200:
        raise ApiError(
            "Got incorrect response code during login. Reponse code: " + response_code + "; Text: " + response_text)

    json_object = None
    try:
        json_object = json.loads(response_text)
    except ValueError as e:
        config.set_setting_bool(constants.LOGGED_IN, False)
        config.set_setting(constants.TOKEN, "")
        utils.log("Did not receive json, something wrong: " + response_text)
        raise ApiError("Failed to log in, API error")

    utils.log(response_text)

    config.set_setting_bool(constants.LOGGED_IN, True)
    config.set_setting(constants.TOKEN, json_object["data"]["attributes"]["token"])

    utils.log("Login success! Token: " + config.get_setting(constants.TOKEN))
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
