import xbmc

from resources.lib import api, config, utils, exceptions, epg

utils.log("Service started")

if __name__ == '__main__':
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break
        if epg.should_update():
            epg.build_epg()
        if config.auth_token_should_update():
            config.login_and_show_notif(force=True)
