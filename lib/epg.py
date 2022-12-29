import datetime
from xml.etree import ElementTree

import pytz
import xbmcgui

from . import api
from . import config
from . import constants
from . import utils

EPG_FILE = "lattelecom-epg.xml"
M3U_FILE = "channels.m3u"

DATE_FORMAT_JSON = "%Y-%m-%d %H:%M:%S"

from xbmcaddon import Addon

data_dir = Addon().getAddonInfo('profile')

riga = pytz.timezone('Europe/Riga')

def indent(elem, level=0):
    # http://effbot.org/zone/element-lib.htm#prettyprint
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def should_update():
    t1 = utils.dateFromString(config.get_setting(constants.LAST_EPG))
    t2 = datetime.datetime.now()
    interval = 6
    update = abs(t2 - t1) > datetime.timedelta(hours=interval)
    if update is True:
        return True


def mark_updated():
    utils.log("EPG data updated")
    config.set_setting(constants.LAST_EPG, utils.stringFromDateNow())


def merge_data(obj1, obj2):
    utils.log("Merging data")
    for item in obj2["data"]:
        obj1["data"].append(item)
    return obj1


def build_epg():
    utils.log("Building EPG data")

    today = datetime.date.today().strftime("%Y-%m-%d")
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    channels = api.get_channels()

    today_data = api.get_epg(today)
    tomorrow_data = api.get_epg(tomorrow)

    json_object = merge_data(today_data, tomorrow_data)

    xml_tv = ElementTree.Element("tv")
    m3u = "#EXTM3U tvg-shift=0\n"

    for channel in channels:
        m3u += "#EXTINF:-1 tvg-id=\"" + channel["id"] + "\" tvg-name=\"" + channel["name"] + "\" tvg-logo=\"" \
               + channel["logo"] + "\" group-title=\"Lattelecom\"," + channel["name"] + "\n"
        m3u += "plugin://lattelecomtv/?play=true&data_url=" + channel["id"] + "\n"

    for channel in json_object["included"]:

        if channel["type"] != "channels":
            continue

        xml_chan = ElementTree.SubElement(xml_tv, "channel", id=channel["id"])
        ElementTree.SubElement(xml_chan, "display-name", lang="en").text = channel["attributes"]["title"]

    offset_hours=riga_offset_hours()
    offset = "%s%02d00" % (("" if offset_hours < 0 else "+"), offset_hours)
    date_format_xml = "%Y%m%d%H%M%S " + offset

    for item in json_object["data"]:

        if item["type"] != "epgs":
            continue

        xml_prog = ElementTree.SubElement(xml_tv, "programme",
                                          start=riga.localize(
                                              utils.dateFromUnix(float(item["attributes"]["unix-start"]))).strftime(
                                              date_format_xml),
                                          stop=riga.localize(
                                              utils.dateFromUnix(float(item["attributes"]["unix-stop"]))).strftime(
                                              date_format_xml), channel=item["relationships"]["channel"]["data"]["id"])
        ElementTree.SubElement(xml_prog, "title", lang="en").text = item["attributes"]["title"]
        ElementTree.SubElement(xml_prog, "desc", lang="en").text = item["attributes"]["description"]
        ElementTree.SubElement(xml_prog, "category", lang="en").text = item["attributes"]["category"]
        ElementTree.SubElement(xml_prog, "icon", src=api.API_BASEURL + "/" + item["attributes"]["poster-url"])

    indent(xml_tv)
    xml_str = ElementTree.tostring(xml_tv, encoding="utf-8", method="xml")

    text_file = open(config.DATADIR + EPG_FILE, "w")
    text_file.write('<?xml version="1.0" encoding="utf-8" ?>' + "\n" + xml_str)
    text_file.close()

    text_file = open(config.DATADIR + M3U_FILE, "w")
    text_file.write(m3u.encode("utf-8"))
    text_file.close()

    mark_updated()

def riga_offset_hours():
    offset_seconds = riga.utcoffset(datetime.datetime.utcnow()).seconds
    return offset_seconds / 3600.0

def configure_epg():
    text_file = open(config.DATADIR + "../pvr.iptvsimple/settings.xml", "w")
    text_file.write("""
<settings version="2">
    <setting id="epgCache">true</setting>
    <setting id="epgPath">{epg_path}</setting>
    <setting id="epgPathType">0</setting>
    <setting id="epgTimeShift" default="true">{offset}</setting>
    <setting id="epgTSOverride" default="true">false</setting>
    <setting id="epgUrl" default="true"></setting>
    <setting id="logoBaseUrl">https://manstv.lattelecom.tv/</setting>
    <setting id="logoFromEpg">1</setting>
    <setting id="logoPath" default="true"></setting>
    <setting id="logoPathType">1</setting>
    <setting id="m3uCache">true</setting>
    <setting id="m3uPath">{m3u_path}</setting>
    <setting id="m3uPathType">0</setting>
    <setting id="m3uUrl" default="true"></setting>
    <setting id="startNum">1</setting>
</settings>
    """.format(epg_path=config.DATADIR + EPG_FILE, offset=riga_offset_hours(), m3u_path=config.DATADIR + M3U_FILE))
    text_file.close()

    xbmcgui.Dialog().ok("Configuration overwritten", "Please restart Kodi for changes to take effect")
