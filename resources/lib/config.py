import datetime
import os
import sys
from random import randint,choice
import string

import xbmc
import xbmcaddon
import xbmcvfs

from . import api
from . import constants
from . import utils
from .exceptions import ApiError

ADDON = xbmcaddon.Addon()
APPID = xbmcaddon.Addon().getAddonInfo("id")
NAME = xbmcaddon.Addon().getAddonInfo("name")
VERSION = xbmcaddon.Addon().getAddonInfo("version")
ICON = xbmcaddon.Addon().getAddonInfo("icon")
DATADIR=xbmcvfs.translatePath( ADDON.getAddonInfo('profile') )

api_version = 383

# os.uname() is not available on Windows, so we make this optional.
try:
    uname = os.uname()
    os_string = ' (%s %s %s)' % (uname[0], uname[2], uname[4])
except AttributeError:
    os_string = ''


def set_setting(key, value):
    return xbmcaddon.Addon(APPID).setSetting(key, value)

def set_setting_bool(key, value):
    return xbmcaddon.Addon(APPID).setSettingBool(key, value)

# TODO: should be private
def get_setting(key):
    return xbmcaddon.Addon(APPID).getSetting(key)

# TODO: should be private
def get_setting_bool(key):
    return xbmcaddon.Addon(APPID).getSettingBool(key)

def get_username():
    return get_setting(constants.USERNAME)

def get_password():
    return get_setting(constants.PASSWORD)

def is_logged_in():
    return get_setting_bool(constants.LOGGED_IN)

def set_logged_in(boole):
    return set_setting_bool(constants.LOGGED_IN, boole)

def set_token(token):
    return set_setting(constants.TOKEN, token)

def get_token():
    return get_setting(constants.TOKEN)

# auth req uses 10 digit random key
# TODO: move to utils?
def get_secret_key():
    return str(randint(1000000000, 9999999999))

def showSettingsGui():
    xbmcaddon.Addon().openSettings()


def showGuiNotification(message):
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (NAME, message, 5000, ICON))


def configCheck():
    if not get_setting_bool(constants.CONFIGURED):
        set_setting_bool(constants.CONFIGURED, True)
        showSettingsGui()
        return


def login_check():
    utils.log("Login check")
    if utils.isEmpty(get_token()):
        # Ask for credentials if they are missing
        if utils.isEmpty(get_username()) or utils.isEmpty(get_password()):
            showSettingsGui()
            return
        _login_and_show_notif()
        return
    else:
        status_code = api.get_user_profile()
        if status_code == 401:
            _login_and_show_notif(True)
        else:
            utils.log("Lattelecom login token seems quite fresh.")

def _login_and_show_notif(force=False):
    # Log in and show a status notification
    try:
        api.login(force=force)
        showGuiNotification("Login successful")
    except ApiError as e:
        showGuiNotification(str(e))
        utils.log(str(e))
        pass

def logout():
    utils.log("Clearing token")
    set_logged_in(False)
    set_token(None)
    showGuiNotification("Authorization token cleared")
