# -*- coding: utf-8 -*-
import sys
import requests
import xbmc, xbmcaddon, xbmcgui, xbmcplugin

from resources.lib.sonarr_api import SonarrAPI
from resources.lib.listing import add_entries, parameters_string_to_dict
from resources.lib._json import write_json, read_json, get_appended_path,\
     dir_db, dir_shows

addonID = "plugin.program.sonarr"
addon = xbmcaddon.Addon(id=addonID)
fanart = ''
pluginhandle = int(sys.argv[1])
loglevel = 1
log_msg = addonID + ' - '
TRANSLATE = addon.getLocalizedString

base_url = addon.getSetting('base-url')
api_key = addon.getSetting('api-key')

vw_moni, vw_perc, vw_total = False, False, False
vw_aired = False
if addon.getSetting('view-moni') == 'true': vw_moni = True
if addon.getSetting('view-perc') == 'true': vw_perc = True
if addon.getSetting('view-total') == 'true': vw_total = True
if addon.getSetting('view-aired') == 'true': vw_aired = True

if not base_url.endswith('/'):
    base_url += '/'
host_url = base_url + 'api'

snr = SonarrAPI(host_url, api_key)


def root():
    mall_shows = {'name': TRANSLATE(30005), 'mode': 'getAllShows', 'type': 'dir'}
    madd_show = {'name': TRANSLATE(30009), 'mode': 'addShow', 'type': 'dir'}
    main = [mall_shows, madd_show]
    add_entries(main)
    xbmcplugin.endOfDirectory(pluginhandle)


def add_show(term=None):
    dialog = xbmcgui.Dialog()
    term = dialog.input('Add Show', type=xbmcgui.INPUT_ALPHANUM)
    # if user cancels, return
    if not term:
        return -1
    # show lookup
    shows = []
    data = snr.lookup_series(term)
    for show in data:
        shows.append(show['title'])
    if not shows:
        # NOTHING FOUND NOTIFICATION
        return -1
    # open dialog for choosing show
    dialog = xbmcgui.Dialog()
    ret = dialog.select(TRANSLATE(30210), shows)
    if ret == -1:
        return -1
    xbmc.log('RET', level=0)
    xbmc.log(str(ret))
    # open dialog for choosing quality
    quality_profile_id = list_quality_profiles()
    if quality_profile_id == -1:
        return -1
    tvdbId = data[ret]['tvdbId']
    title = data[ret]['title']
    #seasons = data['seasons']
    data = {
        'tvdbId': tvdbId,
        'title': title,
        'qualityProfileId': quality_profile_id,
        'rootFolderPath': snr.get_root_folder()[0]['path'],
        # 'titleSlug': '',
        # 'seasons': [],
        'addOptions': {
            'ignoreEpisodesWithFile': 'true',
            'ignoreEpisodesWithoutFiles': 'true'
        }
    }
    snr.add_series(data)


def list_quality_profiles():
    profiles = []
    data = snr.get_quality_profiles()
    for profile in data:
        profile_id = profile['id']
        profile_name = profile['name']
        profiles.append({'name': profile_name, 'id': profile_id})
    profiles_key_list = []
    for profile in profiles:
        profiles_key_list.append(profile['name'])
    dialog = xbmcgui.Dialog()
    ret = dialog.select(TRANSLATE(30211), profiles_key_list)
    if ret == -1:
        return -1
    id = profiles[ret]['id']
    return id


def list_shows(data):
    shows = []
    for show in data:
        name = show['title'].encode('utf-8')
        thumb = host_url + show['images'][2]['url'] + '&apikey={}'.format(api_key)
        #banner = host_url + show['images'][1]['url'] + '&apikey={}'.format(api_key)
        fanart = host_url + show['images'][0]['url'] + '&apikey={}'.format(api_key)
        show_id = show['id']
        seasons = show['seasons']
        dir_show = get_appended_path(dir_shows, str(show_id))
        file = 'seasons.json'
        file_path = get_appended_path(dir_show, file)
        write_json(file_path, seasons)
        shows.append({'name': name, 'url': str(show_id), 'mode': 'getShow', 'type': 'dir',
                      'images': {'thumb': thumb, 'fanart': fanart}})
    add_entries(shows)
    xbmcplugin.endOfDirectory(pluginhandle)


def list_seasons(show_id):
    seasons = []
    #show_id = xbmc.getInfoLabel("ListItem.tvshowtitle")
    dir_show = get_appended_path(dir_shows, str(show_id))
    file_db = get_appended_path(dir_show, 'seasons.json')
    data = read_json(file_db)
    #show_id = xbmc.getInfoLabel("ListItem.tvshowtitle")
    for season in data:
        name = get_season_name(season)
        season_id = season['seasonNumber']
        seasons.append({'name': name, 'url': str(show_id), 'season': str(season_id), 'mode': 'getSeason', 'type': 'dir'})
    add_entries(seasons)
    xbmcplugin.endOfDirectory(pluginhandle)


def list_season(show_id, season_id):
    xbmc.log("List Season")
    season = []
    #show_id = xbmc.getInfoLabel("ListItem.tvshowtitle")
    #season_id = xbmc.getInfoLabel("ListItem.season")
    xbmc.log("season_id")
    xbmc.log(str(season_id))
    dir_show = get_appended_path(dir_shows, str(show_id))
    file_db = get_appended_path(dir_show, 'episodes.json')
    xbmc.log('filedb')
    xbmc.log(str(file_db))
    data = read_json(file_db)
    for episode in data:
        if str(episode['seasonNumber']) != season_id:
            continue
        else:
            xbmc.log("FOUND")
            name = get_episode_name(episode)
            episode = episode['episodeNumber']
            season.append({'name': name, 'mode': 'end', 'show': str(show_id), 'episode': episode, 'type': 'dir'})
    add_entries(season)
    xbmcplugin.endOfDirectory(pluginhandle)


def get_episode_name(episode):
    name = str(episode['seasonNumber']) + 'x'
    name += str(episode['episodeNumber']).zfill(2)
    if episode['hasFile']:
        name += ' [COLOR FF3576F9]%s[/COLOR] ' % episode['title']
    else:
        name += ' [COLOR FFF7290A]%s[/COLOR] ' % episode['title']
    if vw_aired and 'airDate' in episode:
        name += (' [COLOR FF494545]%s[/COLOR]' % episode['airDate'])
    return name.encode('utf-8')


def get_season_name(season):
    season_id = season['seasonNumber']
    name = TRANSLATE(30020)
    name += str(season_id).zfill(2)
    # Get percentage
    if vw_perc:
        perc = int(season['statistics']['percentOfEpisodes'])
        if perc == 100:
            perc = '[COLOR FF3576F9]{}%[/COLOR]'.format(perc)  # blue
        elif 50 <= perc < 100:
            perc = '[COLOR FFFA7544]{}%[/COLOR]'.format(perc)  # yellow
        elif perc < 50:
            perc = '[COLOR FFF7290A]{}%[/COLOR]'.format(perc)  # red
        name += ' ' + str(perc)
    # get episodes counter
    if vw_total:
        epi_count = str(season['statistics']['episodeCount'])
        epi_total_count = str(season['statistics']['totalEpisodeCount'])
        name += ' {}/{} '.format(epi_count, epi_total_count)
    # get monitor stats
    if vw_moni:
        xbmc.log('VW MONI TRUE')
        if season['monitored'] == 'false':
            name += '[COLOR FF494545]%s[/COLOR]' % TRANSLATE(30025)
        else:
            name += '[COLOR FF494545]%s[/COLOR]' % TRANSLATE(30026)
    else:
        xbmc.log('VW MONI FALSE')
    return name

'''
def toggle_monitored():
    # TODO ?
    season_id = xbmc.getInfoLabel("ListItem.Season")
'''


def get_show(show_id):
    list_seasons(show_id)
    get_all_episodes(show_id)


def get_all_shows():
    data = snr.get_series()
    ord_data = sorted(data, key=lambda k: k['title'])   # order titles alphabetically
    list_shows(ord_data)


def get_all_episodes(show_id):
    data = snr.get_episodes_by_series_id(show_id)
    dir_show = get_appended_path(dir_shows, str(show_id))
    file_db = get_appended_path(dir_show, 'episodes.json')
    write_json(file_db, data)


params = parameters_string_to_dict(sys.argv[2])
mode = params.get('mode')
url = params.get('url')
name = params.get('name')
season = params.get('season')
if type(url) == type(str()):
    url = str(url)


if mode == None:
    root()
if mode == 'getAllShows':
    get_all_shows()
elif mode == 'getShow':
    get_show(url)
elif mode == 'getSeason':
    list_season(url, season)
elif mode == 'addShow':
    add_show(url)
