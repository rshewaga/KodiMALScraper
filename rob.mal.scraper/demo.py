# -*- coding: utf-8 -*-
"""
Proof of concept MyAnimeList TV show scraper.
Based on https://github.com/xbmc/xbmc/tree/master/addons/metadata.demo.tv
"""

import sys
import urllib.parse
import requests

import xbmcgui
import xbmcplugin
import xbmc

def get_params():
    param_string = sys.argv[2][1:]
    if param_string:
        return dict(urllib.parse.parse_qsl(param_string))
    return {}

params = get_params()
plugin_handle = int(sys.argv[1])
action = params.get('action')

def getBestTitle(_titles:list) -> str:
    '''
    For the given list of titles from Jikan, return the highest ranked title.
    Rank from best to worst: Default, English, Synonym, Japanese
    Input is an array of dictionaries. Each dictionary has a 'type' and 'title'.
        [
            {
                "type": "Default",
                "title": Tengen Toppa Gurren Lagann
            },
            {
                "type": "English",
                "title": Gurren Lagann
            }
        ]
    '''

    res:str = ""
    titleSetFrom:int = 1000 # Number representing which rank last set the title. Lower = better.
    for variation in _titles:
        if(variation['type'] == 'Default'):
            res = variation['title']
            titleSetFrom = 0
        if(variation['type'] == 'English' and titleSetFrom >= 1):
            res = variation['title']
            titleSetFrom = 1
        if(variation['type'] == 'Synonym' and titleSetFrom >= 2):
            res = variation['title']
            titleSetFrom = 2
        if(variation['type'] == 'Japanese' and titleSetFrom >= 3):
            res = variation['title']
            titleSetFrom = 3
    
    return res

def getGenres(_data:dict) -> list:
    '''
    For the given Jikan data item, return the list of genres
    Input:
        data {
            ...,
            "genres": [
                {
                    "mal_id": 1,
                    "type": "anime",
                    "name": "Action",
                    "url": "https://myanimelist.net/anime/genre/1/Action"
                },
                {
                    "mal_id": 2,
                    "type": "anime",
                    "name": "Adventure",
                    "url": "https://myanimelist.net/anime/genre/2/Adventure"
                }
            ],
            ...
        }
    Output:
        ['Action', 'Adventure']
    '''

    res:list[str] = []

    for item in _data['genres']:
        res.append(item['name'])

    return res

def getStudios(_data:dict) -> list:
    '''
    For the given Jikan data item, return the list of studios
    Input:
        data {
            ...,
            "studios": [
                {
                    "mal_id": 6,
                    "type": "anime",
                    "name": "Gainax",
                    "url": "https://myanimelist.net/anime/producer/6/Gainax"
                },
                {
                    "mal_id": 7,
                    "type": "anime",
                    "name": "J.C.Staff",
                    "url": "https://myanimelist.net/anime/producer/7/J.C.Staff"
                }
            ],
            ...
        }
    Output:
        ['Gainax', 'J.C.Staff']
    '''

    res:list[str] = []

    for item in _data['studios']:
        res.append(item['name'])

    return res

def action_find(_globalParams:dict):
    inputTitle = _globalParams['title']
    inputYear = _globalParams.get('year', 'not specified')
    xbmc.log(f'Find movie with title "{inputTitle}" from year {inputYear}', xbmc.LOGDEBUG)

    # Request Jikan with the search query being the show title
    url:str = 'https://api.jikan.moe/v4/anime'
    params:dict = {'q': inputTitle}
    req:requests.Response = requests.get(url, params=params)
    json:dict = req.json()
    #xbmc.log(str(json), xbmc.LOGDEBUG)

    if(len(json['data']) < 1):
        xbmc.log("Didn't find any MAL results")
        return

    xbmc.log("Found {0} results".format(len(json['data'])))

    # The first result is taken as the best
    res:dict = json['data'][0]

    title:str = getBestTitle(res['titles'])

    liz = xbmcgui.ListItem(title, offscreen=True)
    liz.setArt({'thumb': res['images']['jpg']['large_image_url']})
    #liz.setProperty('relevance', '0.5')
    xbmcplugin.addDirectoryItem(handle=plugin_handle, url='/mal/showid/{0}'.format(res['mal_id']), listitem=liz, isFolder=True)
    #liz = xbmcgui.ListItem('Demo show 2', offscreen=True)
    #liz.setArt({'thumb': 'DefaultVideo.png'})
    #liz.setProperty('relevance', '0.3')
    #xbmcplugin.addDirectoryItem(handle=plugin_handle, url='/path/to/show2', listitem=liz, isFolder=True)

def action_getdetails(_globalParams:dict):
    url = _globalParams['url']
    # url is "/mal/showid/###"
    show_id:int = int(url[12:])

    xbmc.log('Get tv show details callback with url \"{0}\"'.format(url), xbmc.LOGDEBUG)

    # Jikan request with show id
    url:str = 'https://api.jikan.moe/v4/anime/{0}/full'.format(show_id)
    req:requests.Response = requests.get(url)
    json:dict = req.json()

    res:dict = json['data']

    title:str = getBestTitle(res['titles'])
    liz = xbmcgui.ListItem(title, offscreen=True)
    tags = liz.getVideoInfoTag()
    tags.setTitle(title)
    tags.setOriginalTitle(title)
    tags.setSortTitle(title)
    tags.setPlotOutline(res['synopsis'])
    tags.setPlot(res['synopsis'])
    tags.setMpaa(res['rating'])
    tags.setGenres(getGenres(res))
    tags.setStudios(getStudios(res))
    tags.setDateAdded(res['aired']['from'][:10])
    tags.setPremiered(res['aired']['from'][:10])
    tags.setFirstAired(res['aired']['from'][:10])
    tags.setTvShowStatus(res['status'])
    tags.setEpisodeGuide('/mal/showid/{0}'.format(show_id))
    tags.setRatings({'mal': (res['score'], res['scored_by'])}, defaultrating='mal')
    tags.addSeason(1) # Needs at least one season or doesn't show up in the UI
    tags.addAvailableArtwork(res['images']['jpg']['large_image_url'], 'poster')

    xbmcplugin.setResolvedUrl(handle=plugin_handle, succeeded=True, listitem=liz)

def action_getepisodelist(_globalParams:dict):
    url = _globalParams['url']
    # url is "/mal/showid/###"
    show_id:int = int(url[12:])

    xbmc.log('Get episode list callback with url \"{0}\"'.format(url), xbmc.LOGDEBUG)

    # Jikan request for show episodes info
    url:str = 'https://api.jikan.moe/v4/anime/{0}/episodes'.format(show_id)
    req:requests.Response = requests.get(url)
    json:dict = req.json()

    res:list = json['data']

    for _ep in res:
        liz = xbmcgui.ListItem('Demo Episode 1x1', offscreen=True)
        tags = liz.getVideoInfoTag()
        tags.setTitle(_ep['title'])
        tags.setSeason(1)
        tags.setEpisode(_ep['mal_id'])
        tags.setFirstAired(_ep['aired'][:10])
        
        xbmcplugin.addDirectoryItem(handle=plugin_handle, url="/mal/showid/{0}/ep/{1}".format(show_id, _ep['mal_id']), listitem=liz, isFolder=False)

def action_getepisodedetails(_globalParams:dict):
    url = _globalParams['url']
    # url is "/mal/showid/###/ep/#"
    show_id:int = int(url[12:url[12:].find('/') + 12])
    ep_id:int = int(url[url.rfind('/') + 1:])

    xbmc.log('Get episode details callback with url \"{0}\"'.format(url), xbmc.LOGDEBUG)

    # Jikan request for show episodes info
    url:str = 'https://api.jikan.moe/v4/anime/{0}/episodes/{1}'.format(show_id, ep_id)
    req:requests.Response = requests.get(url)
    json:dict = req.json()

    res:dict = json['data']

    liz = xbmcgui.ListItem(res['title'], offscreen=True)
    tags = liz.getVideoInfoTag()
    tags.setTitle(res['title'])
    tags.setOriginalTitle(res['title'])
    tags.setSeason(1)
    tags.setEpisode(ep_id)
    tags.setPlotOutline(res['synopsis'])
    tags.setPlot(res['synopsis'])
    tags.setDuration(int(res['duration']))
    tags.setDateAdded(res['aired'][:10])
    tags.setPremiered(res['aired'][:10])
    tags.setFirstAired(res['aired'][:10])
    tags.addSeason(1) # Needs at least one season or doesn't show up in the UI

    xbmcplugin.setResolvedUrl(handle=plugin_handle, succeeded=True, listitem=liz)

if action == 'find':
    action_find(params)

elif action == 'getdetails':
    action_getdetails(params)

elif action == 'getepisodelist':
    action_getepisodelist(params)

elif action == 'getepisodedetails':
    action_getepisodedetails(params)

elif action == 'nfourl':
    nfo = params['nfo']
    xbmc.log('Find url from nfo file', xbmc.LOGDEBUG)
    liz = xbmcgui.ListItem('Demo show 1', offscreen=True)
    xbmcplugin.addDirectoryItem(handle=plugin_handle, url="/path/to/show", listitem=liz, isFolder=True)

elif action is not None:
    xbmc.log(f'Action "{action}" not implemented', xbmc.LOGDEBUG)

xbmcplugin.endOfDirectory(plugin_handle)
