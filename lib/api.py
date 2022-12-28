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
    # ctx=ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # ctx.set_default_verify_paths()

    # https = urllib.request.HTTPSHandler(context=ctx)
    opener = urllib.request.build_opener()
    # Headers from Firefox 107
    opener.addheaders = [
        ('User-Agent',
	'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:107.0) Gecko/20100101 Firefox/107.0'),
        ('Content-Type', 'application/json'),
        ('Accept', 'application/json'),
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

    streamurl = None

    url = API_ENDPOINT + "/get/content/live-streams/" + data_url + "?include=quality"
    opener = get_url_opener()
    opener.addheaders.append(('Authorization', "Bearer " + config.get_setting(constants.TOKEN)))
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

    stream_links = {}

    for stream in json_object["data"]:

        if stream["type"] != "live-streams":
            continue

        url = stream["attributes"]["stream-url"] + "&auth_token=app_" + config.get_setting(constants.TOKEN)

        if "_lq.stream" in stream["id"]:
            stream_links["3-lq"] = url
        elif "_mq.stream" in stream["id"]:
            stream_links["2-mq"] = url
        elif "_hq.stream" in stream["id"]:
            stream_links["1-hq"] = url
        elif "_hd.stream" in stream["id"]:
            stream_links["0-hd"] = url

    for key in sorted(stream_links.keys()):
        streamurl = stream_links[key]
        break

    return streamurl


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
