import datetime
import dateutil.parser
from xml.etree import ElementTree
import os

import pytz
import xbmcgui

from . import api
from . import config
from . import constants
from . import utils
import xbmcaddon
import xbmcvfs

EPG_FILE = "lattelecom-epg.xml"
M3U_FILE = "channels.m3u"

DATE_FORMAT_JSON = "%Y-%m-%d %H:%M:%S"

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


def build_epg():
    utils.log("Building EPG data")

    channels = api.get_channels()

    yesterday = (datetime.date.today() - datetime.timedelta(days = 3)).strftime('%s')
    tomorrow = (datetime.date.today() + datetime.timedelta(days = 3)).strftime('%s')
    
    channel_epgs = api.get_epg(yesterday, tomorrow)

    xml_tv = ElementTree.Element("tv")
    m3u = "#EXTM3U tvg-shift=0\n"

    for channel in channels:
        m3u += f'#EXTINF:-1 tvg-id="{channel["id"]}" tvg-name="{channel["name"]}" tvg-logo="{channel["image"]}" group-title={channel["group"]} catchup="vod", {channel["name"]}' + "\n"  
        m3u += "plugin://plugin.video.tetplus-unofficial/?action=play_stream&type=channel&data_url=%s\n" % (channel["id"])

    for channel in channels:

        xml_chan = ElementTree.SubElement(xml_tv, "channel", id=str(channel["id"]))
        ElementTree.SubElement(xml_chan, "display-name", lang="en").text = channel["name"]

    offset_hours=riga_offset_hours()
    offset = "%s%02d00" % (("" if offset_hours < 0 else "+"), offset_hours)
    date_format_xml = "%Y%m%d%H%M%S " + offset

    for item in channel_epgs:
        for epg in item["epgs"]:
            catchup_dict = { "catchup-id": "plugin://plugin.video.tetplus-unofficial/?action=play_stream&type=epg&data_url=%s" % (epg["id"])}
            xml_prog = ElementTree.SubElement(xml_tv, "programme", catchup_dict,
                                            start=
                                                dateutil.parser.isoparse(epg["start"]).strftime(
                                                date_format_xml),
                                            stop=
                                                dateutil.parser.isoparse(epg["end"]).strftime(
                                                date_format_xml), 
                                            channel=str(item["id"]))
            ElementTree.SubElement(xml_prog, "title", lang="en").text = epg["title"]
            ElementTree.SubElement(xml_prog, "desc", lang="en").text = (epg["summary"] if "summary" in epg else "")
            ElementTree.SubElement(xml_prog, "icon", src="%s/images/epg/%s?quality=80&width=280" % (api.API_BASEURL, epg["id"]))

    indent(xml_tv)
    xml_str = ElementTree.tostring(xml_tv, encoding="utf-8", method="xml").decode("utf-8")

    text_file = open(config.DATADIR + EPG_FILE, "w", encoding="utf-8")
    text_file.write('<?xml version="1.0" encoding="utf-8" ?>' + "\n" + xml_str)
    text_file.close()

    text_file = open(config.DATADIR + M3U_FILE, "w", encoding="utf-8")
    text_file.write(m3u)
    text_file.close()

    mark_updated()

def riga_offset_hours():
    offset_seconds = riga.utcoffset(datetime.datetime.utcnow()).seconds
    return offset_seconds / 3600.0

def configure_epg():
    os.chdir(config.DATADIR)
    os.chdir("..")
    try:
        os.mkdir("pvr.iptvsimple")
    except OSError as error:
        pass
    
    text_file = open(os.path.join(os.getcwd(),"pvr.iptvsimple","settings.xml"),"w", encoding="utf-8")
    
    text_file.write("""
<settings version="2">
    <setting id="m3uPathType">0</setting>
    <setting id="m3uPath">{m3u_path}</setting>
    <setting id="m3uUrl" default="true" />
    <setting id="m3uCache" default="true">true</setting>
    <setting id="startNum" default="true">1</setting>
    <setting id="numberByOrder" default="true">false</setting>
    <setting id="m3uRefreshMode" default="true">0</setting>
    <setting id="m3uRefreshIntervalMins" default="true">60</setting>
    <setting id="m3uRefreshHour" default="true">4</setting>
    <setting id="tvGroupMode" default="true">0</setting>
    <setting id="numTvGroups" default="true">1</setting>
    <setting id="oneTvGroup" default="true" />
    <setting id="twoTvGroup" default="true" />
    <setting id="threeTvGroup" default="true" />
    <setting id="fourTvGroup" default="true" />
    <setting id="fiveTvGroup" default="true" />
    <setting id="customTvGroupsFile" default="true">special://userdata/addon_data/pvr.iptvsimple/channelGroups/customTVGroups-example.xml</setting>
    <setting id="tvChannelGroupsOnly" default="true">false</setting>
    <setting id="radioGroupMode" default="true">0</setting>
    <setting id="numRadioGroups" default="true">1</setting>
    <setting id="oneRadioGroup" default="true" />
    <setting id="twoRadioGroup" default="true" />
    <setting id="threeRadioGroup" default="true" />
    <setting id="fourRadioGroup" default="true" />
    <setting id="fiveRadioGroup" default="true" />
    <setting id="customRadioGroupsFile" default="true">special://userdata/addon_data/pvr.iptvsimple/channelGroups/customRadioGroups-example.xml</setting>
    <setting id="radioChannelGroupsOnly" default="true">false</setting>
    <setting id="epgPathType">0</setting>
    <setting id="epgPath">{epg_path}</setting>
    <setting id="epgUrl" default="true" />
    <setting id="epgCache" default="true">true</setting>
    <setting id="epgTimeShift">{offset}</setting>
    <setting id="epgTSOverride" default="true">false</setting>
    <setting id="useEpgGenreText" default="true">false</setting>
    <setting id="genresPathType" default="true">0</setting>
    <setting id="genresPath" default="true">special://userdata/addon_data/pvr.iptvsimple/genres/genreTextMappings/genres.xml</setting>
    <setting id="genresUrl" default="true" />
    <setting id="logoPathType" default="true">1</setting>
    <setting id="logoPath" default="true" />
    <setting id="logoBaseUrl">https://tet.plus/</setting>
    <setting id="useLogosLocalPathOnly" default="true">false</setting>
    <setting id="logoFromEpg" default="true">1</setting>
    <setting id="timeshiftEnabled" default="true">false</setting>
    <setting id="timeshiftEnabledAll" default="true">true</setting>
    <setting id="timeshiftEnabledHttp" default="true">true</setting>
    <setting id="timeshiftEnabledUdp" default="true">true</setting>
    <setting id="timeshiftEnabledCustom" default="true">false</setting>
    <setting id="catchupEnabled">true</setting>
    <setting id="catchupQueryFormat" default="true" />
    <setting id="catchupDays" default="true">5</setting>
    <setting id="allChannelsCatchupMode" default="true">0</setting>
    <setting id="catchupOverrideMode" default="true">0</setting>
    <setting id="catchupCorrection" default="true">0</setting>
    <setting id="catchupPlayEpgAsLive" default="true">false</setting>
    <setting id="catchupWatchEpgBeginBufferMins" default="true">5</setting>
    <setting id="catchupWatchEpgEndBufferMins" default="true">15</setting>
    <setting id="catchupOnlyOnFinishedProgrammes" default="true">false</setting>
    <setting id="transformMulticastStreamUrls" default="true">false</setting>
    <setting id="udpxyHost" default="true">127.0.0.1</setting>
    <setting id="udpxyPort" default="true">4022</setting>
    <setting id="useFFmpegReconnect" default="true">true</setting>
    <setting id="useInputstreamAdaptiveforHls" default="true">false</setting>
    <setting id="defaultUserAgent" default="true" />
    <setting id="defaultInputstream" default="true" />
    <setting id="defaultMimeType" default="true" />
</settings>
    """.format(epg_path=config.DATADIR + EPG_FILE, offset=riga_offset_hours(), m3u_path=config.DATADIR + M3U_FILE))
    text_file.close()

    xbmcgui.Dialog().ok("Configuration overwritten", "Please restart Kodi for changes to take effect")
