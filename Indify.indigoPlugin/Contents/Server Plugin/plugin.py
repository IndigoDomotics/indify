#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com
#version 1.0.3 : Private Beta

import indigo
import os, os.path
import sys
from shutil import copyfile

from ghpu import GitHubPluginUpdater

import time
from time import sleep
import datetime

import requests, base64
import json

########################################
# Global variable
########################################

spotifydevice = ""

########################################
# Custom procedures
########################################

def convertms(millis):
    seconds = (millis / 1000) % 60
    minutes = (millis / (1000 * 60)) % 60
    return seconds, minutes

def spotifyerror(logger, htmlreturn):

    spotifyerror = ""
    spotifylevel = ""

    if htmlreturn == '<Response [200]>':
        spotifyerror = "Spotify 200: OK - The request has succeeded. The client can read the result of the request in the body and the headers of the response."
        spotifylevel = "Success"
    elif htmlreturn == '<Response [201]>':
        spotifyerror = "Spotify 201: Created - The request has been fulfilled and resulted in a new resource being created."
        spotifylevel = "Success"
    elif htmlreturn == '<Response [202]>':
        spotifyerror = "Spotify 202: Accepted - The request has been accepted for processing, but the processing has not been completed."
        spotifylevel = "Warning"
    elif htmlreturn == '<Response [203]>':
        spotifyerror = "Spotify 203: No Content - The request has succeeded but returns no message body."
        spotifylevel = "Warning"
    elif htmlreturn == '<Response [204]>':
        spotifyerror = "Spotify 204: No Content - The request has succeeded but returns no message body."
        spotifylevel = "Success"
    elif htmlreturn == '<Response [304]>':
        spotifyerror = "Spotify 304: Not Modified. See Conditional requests."
        spotifylevel = "Warning"

    elif htmlreturn == '<Response [400]>':
        spotifyerror = "Spotify 400: Bad Request - The request could not be understood by the server due to malformed syntax. The message body will contain more information; see Error Details."
        spotifylevel = "Error"
        logger.debug(spotifyerror)
    elif htmlreturn == '<Response [401]>':
        spotifyerror = "Spotify 401: Unauthorized - The request requires user authentication or, if the request included authorization credentials, authorization has been refused for those credentials."
        spotifylevel = "Unauthorized"
        logger.debug(spotifyerror)
    elif htmlreturn == '<Response [403]>':
        spotifyerror = "Spotify 403: Forbidden - The server understood the request, but is refusing to fulfill it."
        spotifylevel = "Error"
        logger.debug(spotifyerror)
    elif htmlreturn == '<Response [404]>':
        spotifyerror = "Spotify 404: Not Found - The requested resource could not be found. This error can be due to a temporary or permanent condition."
        spotifylevel = 'Error'
        logger.debug(spotifyerror)
    elif htmlreturn == '<Response [429]>':
        spotifyerror = "Spotify 429: Too Many Requests - Rate limiting has been applied."
        spotifylevel = "Error"
        logger.debug(spotifyerror)
    elif htmlreturn == '<Response [500]>':
        spotifyerror = "Spotify 500: Internal Server Error. You should never receive this error because our clever coders catch them all ... but if you are unlucky enough to get one, please report it to us through a comment at the bottom of this page."
        spotifylevel = "Error"
        logger.debug(spotifyerror)
    elif htmlreturn == '<Response [502]>':
        spotifyerror = "Spotify 502: Bad Gateway - The server was acting as a gateway or proxy and received an invalid response from the upstream server."
        spotifylevel = "Error"
        logger.debug(spotifyerror)
    elif htmlreturn == '<Response [503]>':
        spotifyerror = "Spotify 503: Service Unavailable - The server is currently unable to handle the request due to a temporary condition which will be alleviated after some delay. You can choose to resend the request again."
        spotifylevel = "Error"
        logger.debug(spotifyerror)
    else:  # default, could also just omit condition or 'if True'
        spotifyerror = "Error code not found: " + htmlreturn
        spotifylevel = "Warning"
        logger.debug(spotifyerror)

    return {"errorlevel": spotifylevel, "errormessage": spotifyerror}

def callspotifycommand(logger, callid, device, type, spotifyurl, spotifydata=None, spotifyparams=None):
    spotifydata = spotifydata if spotifydata else {}
    spotifyparams = spotifyparams if spotifyparams else {}
    spotifykey = device.pluginProps["SpotifyKey"]
    verboselogging = device.pluginProps["verboselogging"]

    spotifyheader = {"Authorization": "Bearer " + spotifykey}
    jsondata = json.dumps(spotifydata)
    returncode = {"errorlevel": "Failed", "errormessage": "Undefined Error"}
    response = ""

    logger.debug("calling:" + spotifyurl)

    if type == "get":
        try:
            response = requests.get(spotifyurl, headers=spotifyheader, data=jsondata, params=spotifyparams, timeout=(3, 6))
            returncode = spotifyerror(logger, str(response))
        except Exception as errtxt:
            logger.debug(callid + ".01: " + str(errtxt) + ":" + str(response))
    elif type == "put":
        try:
            response = requests.put(spotifyurl, headers=spotifyheader, data=jsondata, params=spotifyparams, timeout=(3, 6))
            returncode = spotifyerror(logger, str(response))
        except Exception as errtxt:
            logger.debug(callid + ".01: " + str(errtxt) + ":" + str(response))
    elif type == "post":
        try:
            indigo.server.log(spotifyurl)
            response = requests.post(spotifyurl, headers=spotifyheader, data=jsondata, params=spotifyparams, timeout=(3, 6))
            returncode = spotifyerror(logger, str(response))
        except Exception as errtxt:
            logger.debug(callid + ".01: " + str(errtxt) + ":" + str(response))

    if returncode["errorlevel"] == "Success":
        return(response.text)
    elif returncode["errorlevel"] == "Unauthorized":
        refreshkey = device.pluginProps["RefreshKey"]
        RefreshKey(logger, device, refreshkey)
    else:
        if str(verboselogging) == "True":
            indigo.server.log(callid + ".02: " + returncode["errormessage"])
        return("Error")

#001
def getspotifydevice(logger, device):
    deviceid = "Device Not Found"
    restricted = "true"
    deviceactive = "false"
    response = callspotifycommand(logger, "001", device, "get", "https://api.spotify.com/v1/me/player/devices")

    if response != "Error":
        data = json.loads(response)
        spotifydevice = device.pluginProps["SpotifyDevice"]
        for spotifydevices in data['devices']:
            if spotifydevices['name'] == spotifydevice:
                deviceid = (spotifydevices['id'])
                restricted = (spotifydevices['is_restricted'])
                deviceactive = (spotifydevices['is_active'])

    if deviceactive == "false":
        deviceid = "Device Not Found"
        device.updateStateOnServer("state", value="unavailable")

    return deviceid

#002
def RefreshKey(logger, device, refreshkey):
    indigo.server.log("refresh key")

    clientid = "9b907857f3644732bfa45d4ec0ba6601"
    secretkey = "c5bc817f12f7435f91c3ee450272da29"
    success = "false"

    spotifyurl = "https://accounts.spotify.com/api/token"
    spotifydata = {'grant_type': 'refresh_token', 'refresh_token': refreshkey}
    response = requests.post(spotifyurl, data=spotifydata, auth=(clientid, secretkey))
    returncode = spotifyerror(logger, str(response))

    if returncode["errorlevel"] == "Success":
        tokendata = response.json()
        localPropsCopy = device.pluginProps
        localPropsCopy['SpotifyKey'] = str(tokendata['access_token'])
        device.replacePluginPropsOnServer(localPropsCopy)
        success = "True"
    else:
        indigo.server.log("002 Key Refresh Failed: " + returncode["errorcode"])

    return success

#003
def GetCurrentSong(logger, device, spotifykey):
    response = callspotifycommand(logger, "003", device, "get", "https://api.spotify.com/v1/me/player/currently-playing", spotifydata="", spotifyparams="")

    if response != "Error":
        try:
            data = json.loads(response)

            # get album information
            album = data['item']['album']

            # get artist information
            artist = data['item']['artists'][0]

            # get image information
            imagelarge = album['images'][0]
            imagemedium = album['images'][1]
            imagesmall = album['images'][2]

            return {'isplaying': data['is_playing'],
                    'track': data['item']['name'],
                    'trackid': data['item']['id'],
                    'duration': data['item']['duration_ms'],
                    'progress': data['progress_ms'],
                    'album': album['name'],
                    'albumid': album['id'],
                    'artist': artist['name'],
                    'artistid': artist['id'],
                    'imagelarge': imagelarge['url'],
                    'imagemedium': imagemedium['url'],
                    'imagesmall': imagesmall['url']
                    }
        except Exception as errtxt:
            logger.debug('error 003.1: ' + str(errtxt) + ":" + str(response))
    else:
        return False

#004
def UpdateCurrentSong(logger, device, playingsong):
    currenttrackid = device.states["c_track_id"]
    previoustrackid = device.states["p_track_id"]

    try:
        if playingsong['isplaying']:
            keyValueList = [{'key': 'state', 'value': 'playing'}]
            if not currenttrackid:
                keyValueList.append({'key': "c_album", 'value': playingsong['album']})
                keyValueList.append({'key': "c_track", 'value': playingsong['track']})
                keyValueList.append({'key': "c_artist", 'value': playingsong['artist']})
                keyValueList.append({'key': "c_track_id", 'value': playingsong['trackid']})
                keyValueList.append({'key': "c_album_id", 'value': playingsong['albumid']})
                keyValueList.append({'key': "c_artist_id", 'value': playingsong['artistid']})
                keyValueList.append({'key': "duration", 'value': playingsong['duration']})
            elif playingsong['trackid'] <> currenttrackid:
                # update previous
                keyValueList.append({'key': "p_album", 'value': device.states['c_album']})
                keyValueList.append({'key': "p_track", 'value': device.states['c_track']})
                keyValueList.append({'key': "p_artist", 'value': device.states['c_artist']})
                keyValueList.append({'key': "p_track_id", 'value': device.states['c_track_id']})
                keyValueList.append({'key': "p_album_id", 'value': device.states['c_album_id']})
                keyValueList.append({'key': "p_artist_id", 'value': device.states['c_artist_id']})
                # update current song
                keyValueList.append({'key': "c_album", 'value': playingsong['album']})
                keyValueList.append({'key': "c_track", 'value': playingsong['track']})
                keyValueList.append({'key': "c_artist", 'value': playingsong['artist']})
                keyValueList.append({'key': "c_track_id", 'value': playingsong['trackid']})
                keyValueList.append({'key': "c_album_id", 'value': playingsong['albumid']})
                keyValueList.append({'key': "c_artist_id", 'value': playingsong['artistid']})
                keyValueList.append({'key': "duration", 'value': playingsong['duration']})
                # Update images
                UpdateCurrentImage(logger, playingsong['imagelarge'], playingsong['imagemedium'], playingsong['imagesmall'])
        else:
            keyValueList = [{'key': 'state', 'value': 'paused'}]
        device.updateStatesOnServer(keyValueList)
    except Exception as errtxt:
        logger.debug('error 004: ' + str(errtxt))

#005
def SaveImage(logger, imagename, imageurl):
    # indigo.server.log("update image")

    maindirectory = "/Library/Application Support/Perceptive Automation/Indigo 7/IndigoWebServer/plugins/Indify/"
    imagepath = maindirectory + imagename + ".png"

    if not os.path.exists(maindirectory):
        os.makedirs(maindirectory)

    # load large image
    if os.path.exists(imagepath):
        os.remove(imagepath)
    try:
        imgdata = requests.get(imageurl).content
        with open(imagepath, 'wb') as handler:
            handler.write(imgdata)
    except Exception as errtxt:
        logger.debug('error 005: ' + str(errtxt))

#006
def UpdateCurrentImage(logger, large, medium, small):
    # indigo.server.log("update image")
    maindirectory = "/Library/Application Support/Perceptive Automation/Indigo 7/IndigoWebServer/plugins/Indify/"
    largeimage1 = maindirectory + "largeimage1.png"
    largeimage2 = maindirectory + "largeimage2.png"
    mediumimage1 = maindirectory + "medioumimage1.png"
    mediumimage2 = maindirectory + "mediumimage2.png"
    smallimage1 = maindirectory + "smallimage1.png"
    smallimage2 = maindirectory + "smallimage2.png"

    if not os.path.exists(maindirectory):
        os.makedirs(maindirectory)

    if os.path.exists(largeimage1):
        copyfile(largeimage1, largeimage2)
        os.remove(largeimage1)
    try:
        SaveImage(logger, "largeimage1", large)
    except Exception as errtxt:
        logger.debug('error 006.1: ' + str(errtxt))

    # load medium image
    if os.path.exists(mediumimage1):
        copyfile(mediumimage1, mediumimage2)
        os.remove(mediumimage1)
    try:
        SaveImage(logger, "mediumimage1", medium)
    except Exception as errtxt:
        logger.debug('error 006.2: ' + str(errtxt))

    # load small image
    if os.path.exists(smallimage1):
        copyfile(smallimage1, smallimage2)
        os.remove(smallimage1)
    try:
        SaveImage(logger, "smallimage1", small)
    except Exception as errtxt:
        logger.debug('error 006.3: ' + str(errtxt))

#007
def LoadPlayListPage(logger, device, spotifykey, pagenumber, itemsperpage):
    if pagenumber < 1:
        pagenumber = 1

    playlistpage = ((pagenumber - 1) * itemsperpage) #+ 1
    playlistcounter = 0
    playlistimages = "no images"

    response = callspotifycommand(logger, "007", device, "get", "https://api.spotify.com/v1/me/playlists", "", {'limit': itemsperpage, 'offset': playlistpage})

    if response != "Error":
        data = json.loads(response)
        device.updateStateOnServer("totalplaylists", value=data['total'])
        maindirectory = "/Library/Application Support/Perceptive Automation/Indigo 7/IndigoWebServer/plugins/Indify/"
        keyValueList = []

        if len(data['items']) > 0:
            for playlistcounter in range(1, 11):
                keyValueList.append({'key': 'playlist_' + str(playlistcounter), 'value': ''})
            for playlistcounter in range(1, 11):
                keyValueList.append({'key': 'playlistid_' + str(playlistcounter), 'value': ''})
            for playlistcounter in range(1, 11):
                keyValueList.append({'key': 'playlistuser_' + str(playlistcounter), 'value': ''})
                oldplaylistimage = maindirectory + "playlistimage" + str(playlistcounter) + ".png"
                copyfile("./Clear.jpg", oldplaylistimage)

            playlistcounter = 0
            playlistidcounter = 10
            playlistusercounter = 20

            for playlist in data['items']:
                keyValueList[playlistcounter]['value'] = playlist['name']
                keyValueList[playlistidcounter]['value'] = playlist['id']
                keyValueList[playlistusercounter]['value'] = playlist['owner']['id']

                playlistimages = playlist['images']

                playlistcounter = playlistcounter + 1
                playlistidcounter = playlistidcounter + 1
                playlistusercounter = playlistusercounter + 1

                if len(playlistimages) > 0:

                    if len(playlistimages) == 2:
                        imagenumber = 1
                    else:
                        imagenumber = 0

                    try:
                        SaveImage(logger, "playlistimage" + str(playlistcounter), playlistimages[imagenumber]["url"])
                    except Exception as errtxt:
                        logger.debug("007: No playlist image: " + str(errtxt))

            device.updateStatesOnServer(keyValueList)

#008
def LoadPlaylistDetail(logger, device, spotifykey, userid, playlistid):

    response = callspotifycommand(logger, "008", device, "get", "https://api.spotify.com/v1/users/" + userid + "/playlists/" + playlistid, "", {"fields": "name,description,id"})

    if response != "Error":
        data = json.loads(response)
        device.updateStateOnServer("playlistname", value=data['name'])
        device.updateStateOnServer("playlistdescription", value=data['description'])
        device.updateStateOnServer("playlistid", value=data['id'])
        device.updateStateOnServer("playlistuserid", value=userid)

#009
def GetUserName(logger, spotifykey):

    response = callspotifycommand(logger, "009", device, "get", "https://api.spotify.com/v1/me", "", {"fields": "name,description,id"})

    if response != "Error":
        data = json.loads(response)
        return data['id']

#010
def LoadTrackPage(logger, device, userid, playlistid, spotifykey, pagenumber, itemsperpage):

    if pagenumber < 1:
        pagenumber = 1
    trackpage = ((pagenumber - 1) * itemsperpage)
    trackcounter = 0

    response = callspotifycommand(logger, "010", device, "get", "https://api.spotify.com/v1/users/" + userid + "/playlists/" + playlistid + "/tracks", "", {'limit': itemsperpage, 'offset': trackpage})

    if response != "Error":
        data = json.loads(response)
        device.updateStateOnServer("totaltracks", value=data['total'])
        keyValueList = []

        if len(data['items']) > 0:
            for trackcounter in range(1, 11):
                keyValueList.append({'key': 'trackname_' + str(trackcounter), 'value': ''})
            for trackcounter in range(1, 11):
                keyValueList.append({'key': 'trackartist_' + str(trackcounter), 'value': ''})

            trackcounter = 0
            artistcounter = 10
            for tracks in data['items']:
                trackname = tracks['track']['name']
                try:
                    artist = tracks['track']['artists'][0]['name']
                except Exception as errtxt:
                    artist = "Unknown"
                    logger.debug("Artist Unknown")
                keyValueList[trackcounter]['value']=trackname
                keyValueList[artistcounter]['value']=artist
                trackcounter = trackcounter + 1
                artistcounter = artistcounter + 1

            device.updateStatesOnServer(keyValueList)

#011
def GetPlayerState(logger, device, spotifykey):
    response = callspotifycommand(logger, "011", device, "get", "https://api.spotify.com/v1/me/player", "", "")

    if response != "Error":
        data = json.loads(response)
        return {'result':'True',
                'isplaying':data['is_playing'],
                'shuffle':data['shuffle_state'],
                'repeat':data['repeat_state'],
                'spotifydevice':data['device']['id'],
                'spotifydevicename':data['device']['name'],
                'spotifyvolume': data['device']['volume_percent'],
                'spotifycontexttype': data['context']['type'],
                'spotifycontexturi': data['context']['uri']}
    else:
        indigo.server.log('error 86: Unable to obtain player state')
        return {'result':"False"}

#012
def ChangeShuffle(logger, device, spotifykey,shuffleaction):
    #spotifyurl = "https://api.spotify.com/v1/me/player/shuffle"
    #spotifyheader = {"Authorization": "Bearer " + spotifykey}
    #spotifyparam ={"state": shuffleaction}
    #response = requests.put(spotifyurl, headers=spotifyheader, params=spotifyparam)
    response = callspotifycommand(logger, "012", device, "put", "https://api.spotify.com/v1/me/player/shuffle", "", {"state": shuffleaction})

#013
def ChangeRepeat(logger, device, spotifykey,repeataction):
    #spotifyurl = "https://api.spotify.com/v1/me/player/repeat"
    #spotifyheader = {"Authorization": "Bearer " + spotifykey}
    #spotifyparam ={"state": repeataction}
    #response = requests.put(spotifyurl, headers=spotifyheader, params=spotifyparam)
    response = callspotifycommand(logger, "013", device, "put", "https://api.spotify.com/v1/me/player/repeat", "", {"state": repeataction})

#014
def SetVolume(logger, device, spotifykey, newvolume):
    #spotifyurl = "https://api.spotify.com/v1/me/player/volume"
    #spotifyheader = {"Authorization": "Bearer " + spotifykey}
    #spotifyparam ={"volume_percent": newvolume}
    #response = requests.put(spotifyurl, headers=spotifyheader, params=spotifyparam)
    response = callspotifycommand(logger, "014", device, "put", "https://api.spotify.com/v1/me/player/volume", "", {"volume_percent": newvolume})

#008
def GetContextDetail(logger, device, type, spotifykey, contextmeta):

    if type == "playlist":
        userid = contextmeta[2]
        id = contextmeta[4]
        response = callspotifycommand(logger, "008", device, "get", "https://api.spotify.com/v1/users/" + userid + "/playlists/" + id, "", {"fields": "name,description,id"})
        if response != "Error":
            data = json.loads(response)
            device.updateStateOnServer("context1", value=data['name'])
            device.updateStateOnServer("context2", value=data['description'])
    elif type == "artist":
        id = contextmeta[2]
        response = callspotifycommand(logger, "008", device, "get", "https://api.spotify.com/v1/artists/" + id)
        if response != "Error":
            data = json.loads(response)
            device.updateStateOnServer("context1", value=data['name'])
            device.updateStateOnServer("context2", value='')
    elif type == "album":
        id = contextmeta[2]
        response = callspotifycommand(logger, "008", device, "get", "https://api.spotify.com/v1/albums/" + id)
        if response != "Error":
            data = json.loads(response)
            device.updateStateOnServer("context1", value=data['name'] + " (" + data['release_date'] + ")")
            device.updateStateOnServer("context2", value=data['artists'][0]['name'])
    else:
        indigo.server.log("Not implemented yet")

########################################
class Plugin(indigo.PluginBase):
    ########################################

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.debug = False
        self.updater = GitHubPluginUpdater(self)

    #########################################
    # Plugin startup and shutdown
    #########################################
    def startup(self):
        self.debugLog(u"startup called")

    def shutdown(self):
        self.debugLog(u"shutdown called")

    def didDeviceCommPropertyChange(self, origDev, newDev):
        return False

    #########################################
    # Main Loop
    #########################################
    def runConcurrentThread(self):
        try:

            #########################################
            # Variable Setup
            #########################################

            timeremaining = 0
            refreshduration = 5
            refreshcycle = refreshduration
            repeat = ""
            shuffle = ""

            logdevice = self.logger

            while True:
                for device in indigo.devices.iter("self"):

                    #########################################
                    # Main Code
                    #########################################

                    state = device.states["state"]

                    if state == "playing":
                        timeremaining = timeremaining - 1000
                        device.updateStateOnServer("timeremaining", value=timeremaining)
                        consec, conmin = convertms(timeremaining)
                        device.updateStateOnServer("timeremainingtext", value=str(conmin) + ":" + str(consec).zfill(2))
                    else:
                        device.updateStateOnServer("timeremainingtext", value="0")

                    refreshcycle = refreshcycle + 1

                    #Check for status of player every five seconds
                    if timeremaining < 0 or refreshcycle > refreshduration:
                        spotifykey = device.pluginProps["SpotifyKey"]
                        refreshkey = device.pluginProps["RefreshKey"]
                        refreshcycle = 0
                        playingsong = False
                        playerstate = False

                        try:
                            playerstate = GetPlayerState(self.logger, device, spotifykey)
                        except Exception as errtxt:
                            self.log.debug("error 85:" + str(errtxt))

                        #indigo.server.log(str(playerstate))
                        #indigo.server.log("A:" + getspotifydevice(device))
                        #indigo.server.log("1:" + str(playerstate['isplaying']))

                        if getspotifydevice(self.logger, device) != "Device Not Found" and (str(playerstate['result']) == "True") and (str(playerstate['isplaying']) == "True"):
                            spotifydevice = playerstate['spotifydevice']
                            keyValueList = [{'key': 'state', 'value': 'playing'}]
                            #device.updateStateOnServer("state", "playing")

                            contextmeta = playerstate['spotifycontexturi'].split(":")
                            #indigo.server.log(playlistmeta[2])
                            #indigo.server.log(playlistmeta[4])
                            #indigo.server.log(str(contextmeta))
                            #indigo.server.log(playerstate['spotifycontexttype'])

                            GetContextDetail(self.logger, device, playerstate['spotifycontexttype'], spotifykey, contextmeta)

                            #Check volume
                            if int(playerstate['spotifyvolume']) != int(device.states["volume"]):
                                keyValueList.append({'key': 'volume', 'value': playerstate['spotifyvolume']})
                                #device.updateStateOnServer("volume", playerstate['spotifyvolume'])

                            #Check repeat
                            if playerstate['repeat'] != device.states["repeat"]:
                                if device.states["repeat"] == "off":
                                    keyValueList.append({'key': 'repeat', 'value': 'context'})
                                    #device.updateStateOnServer("repeat", value="context")
                                else:
                                    keyValueList.append({'key': 'repeat', 'value': 'off'})
                                    #device.updateStateOnServer("repeat", value="off")

                            #Check shuffle
                            if str(playerstate['shuffle']) != str(device.states["shuffle"]):
                                if str(device.states["shuffle"]) == "False":
                                    keyValueList.append({'key': 'shuffle', 'value': 'True'})
                                    #device.updateStateOnServer("shuffle", value="True")
                                else:
                                    keyValueList.append({'key': 'shuffle', 'value': 'False'})
                                    #device.updateStateOnServer("shuffle", value="False")

                            #Update song information
                            playingsong = GetCurrentSong(self.logger, device, spotifykey)
                            if playingsong != False:
                                timeremaining = playingsong['duration'] - playingsong['progress']
                                consec, conmin = convertms(playingsong['duration'])
                                keyValueList.append({'key': 'durationtext', 'value': str(conmin) + ":" + str(consec).zfill(2)})
                                if playingsong['track'] != device.states["c_track"]:
                                    UpdateCurrentSong(self.logger, device, playingsong)

                            device.updateStatesOnServer(keyValueList)

                        else:
                            if getspotifydevice(logger, device) != "Device Not Found":
                                device.updateStateOnServer("state", value="paused")

                    self.sleep(1)

        except self.StopThread:
            indigo.server.log("thread stopped")
            pass

    ################################################################################
    # Plugin menus
    ################################################################################

    def checkForUpdate(self):
        ActiveVersion = str(self.pluginVersion)
        CurrentVersion = str(self.updater.getVersion())
        if ActiveVersion == CurrentVersion:
            indigo.server.log("Running the most recent version of Indify")
        else:
            indigo.server.log(
                "The current version of Indify is " + str(CurrentVersion) + " and the running version " + str(
                    ActiveVersion) + ".")

    def updatePlugin(self):
        ActiveVersion = str(self.pluginVersion)
        CurrentVersion = str(self.updater.getVersion())
        if ActiveVersion == CurrentVersion:
            indigo.server.log("Already running the most recent version of Indify")
        else:
            indigo.server.log(
                "The current version of Indify is " + str(CurrentVersion) + " and the running version " + str(
                    ActiveVersion) + ".")
            self.updater.update()

    def RefreshKey(self):
        indigo.server.log("?? Refresh Key")
        #RefreshKey(device, refreshkey)

    ############################################################################
    # Plugin Actions object callbacks
    ############################################################################
    #015
    def toggle(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        state = device.states["state"]
        spotifydevice = getspotifydevice(self.logger, device)

        if state == "playing":
            response = callspotifycommand(self.logger, "015", device, "put", "https://api.spotify.com/v1/me/player/pause")
            if response != "Error":
                device.updateStateOnServer("state", value="paused")

        else:
            response = callspotifycommand(self.logger, "015", device, "put", "https://api.spotify.com/v1/me/player/", {"device_ids":[spotifydevice], "play":True})
            if response != "Error":
                device.updateStateOnServer("state", value="playing")

    #016
    def play(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifydevice = getspotifydevice(self.logger, device)

        response = callspotifycommand(self.logger, "016", device, "put", "https://api.spotify.com/v1/me/player/",{"device_ids": [spotifydevice], "play": True})
        if response != "Error":
            device.updateStateOnServer("state", value="playing")

    #017
    def pause(self, pluginAction):

        device = indigo.devices[pluginAction.deviceId]
        response = callspotifycommand(self.logger, "017", device, "put", "https://api.spotify.com/v1/me/player/pause")
        if response != "Error":
            device.updateStateOnServer("state", value="paused")

    #018
    def next(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        state = device.states["state"]
        if state == "playing":
            response = callspotifycommand(self.logger, "018", device, "post", "https://api.spotify.com/v1/me/player/next")

    #019
    def previous(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        state = device.states["state"]
        if state == "playing":
            response = callspotifycommand(self.logger, "019", device, "post", "https://api.spotify.com/v1/me/player/previous")

    #020
    def playuri(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifyuri = pluginAction.props["spotifyuri"]
        uribody = {"context_uri": spotifyuri}
        response = callspotifycommand(self.logger, "020", device, "put", "https://api.spotify.com/v1/me/player/play", uribody)

    def repeat(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        repeat = device.states["repeat"]
        if repeat == "off":
            device.updateStateOnServer("repeat", value="context")
            ChangeRepeat(self.logger, device, spotifykey, "context")
        else:
            device.updateStateOnServer("repeat", value="off")
            ChangeRepeat(self.logger, device, spotifykey, "off")

    def shuffle(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        shuffle = device.states["shuffle"]
        if shuffle == "False":
            device.updateStateOnServer("shuffle", value="True")
            ChangeShuffle(self.logger, device, spotifykey, "True")
        else:
            device.updateStateOnServer("shuffle", value="False")
            ChangeShuffle(self.logger, device, spotifykey, "False")

    def setvolume(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        newvolume = int(pluginAction.props["setpercent"])
        SetVolume(self.logger, device, spotifykey, newvolume)
        device.updateStateOnServer("volume", value=newvolume)

    def increasevolume(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        oldvolume = int(device.states['volume'])
        increasepercent = int(pluginAction.props["increasepercent"])
        if int(oldvolume) < 100:
            newvolume=oldvolume+increasepercent
            SetVolume(self.logger, device, spotifykey, newvolume)
            device.updateStateOnServer("volume", value=newvolume)

    def decreasevolume(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        oldvolume = device.states['volume']
        decreasepercent = int(pluginAction.props["decreasepercent"])
        if int(oldvolume) > 0:
            newvolume=oldvolume - decreasepercent
            SetVolume(self.logger, device, spotifykey, newvolume)
            device.updateStateOnServer("volume", value=newvolume)

    def loadplaylistpage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        state = device.states["state"]
        itemsperpage = int(device.pluginProps["PlaylistsPerPage"])

        pagenumber = int(pluginAction.props["pagenumber"])
        LoadPlayListPage(self.logger, device, spotifykey, pagenumber, itemsperpage)

    def nextplaylistpage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        playlistpage = int(device.states["playlistpage"])
        itemsperpage = int(device.pluginProps["PlaylistsPerPage"])

        pagenumber = playlistpage + 1
        LoadPlayListPage(self.logger, device, spotifykey, pagenumber, itemsperpage)

    def previousplaylistpage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        playlistpage = int(device.states["playlistpage"])
        itemsperpage = int(device.pluginProps["PlaylistsPerPage"])

        pagenumber = playlistpage - 1
        LoadPlayListPage(self.logger, device, spotifykey, pagenumber, itemsperpage)

    def selectplaylist(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]

        selectedplaylist = int(pluginAction.props["selectedplaylist"])
        playlistid = device.states["playlistid_" + str(selectedplaylist)]
        playlistuser = device.states["playlistuser_" + str(selectedplaylist)]
        LoadPlaylistDetail(self.logger, device, spotifykey, playlistuser, playlistid)
        itemsperpage = int(device.pluginProps["TracksPerPage"])
        LoadTrackPage(self.logger, device, playlistuser, playlistid, spotifykey, 1, itemsperpage)

    def loadtrackspage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        pagenumber = int(pluginAction.props["trackpagenumber"])
        playlistid = device.states["playlistid"]
        playlistuser = device.states["playlistuserid"]
        itemsperpage = int(device.pluginProps["TracksPerPage"])

        LoadTrackPage(self.logger, device, playlistuser, playlistid, spotifykey, pagenumber, itemsperpage)

    def nexttrackspage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        trackpage = int(device.states["trackpage"])
        playlistid = device.states["playlistid"]
        playlistuser = device.states["playlistuserid"]
        itemsperpage = int(device.pluginProps["TracksPerPage"])

        pagenumber = trackpage + 1
        LoadTrackPage(self.logger, device, playlistuser, playlistid, spotifykey, pagenumber, itemsperpage)

    def previoustrackspage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        trackpage = int(device.states["trackpage"])
        playlistid = device.states["playlistid"]
        playlistuser = device.states["playlistuserid"]
        itemsperpage = int(device.pluginProps["TracksPerPage"])

        pagenumber = trackpage - 1
        LoadTrackPage(self.logger, device, playlistuser, playlistid, spotifykey, pagenumber, itemsperpage)

    #020
    def getspotifydevices(self, filter, valuesDict, typeId, devId):
        device = indigo.devices[devId]
        refreshkey = device.pluginProps["SpotifyKey"]
        keysuccess = "False"
        spotifydevicearray = []

        try:
            spotifykey = device.pluginProps["SpotifyKey"]
            spotifyurl = "https://api.spotify.com/v1/me/player/devices"
            spotifyheader = {"Authorization": "Bearer " + spotifykey}

            response = requests.get(spotifyurl, headers=spotifyheader, timeout=(1, 6))

            data = json.loads(response.text)
            for spotifydevices in data['devices']:
                spotifydevice=(spotifydevices['name'],spotifydevices['name'])
                spotifydevicearray.append(spotifydevice)
        except:
            indigo.server.log("error 020: Refreshing Spotify Key")
            keysuccess = RefreshKey(self.logger, device, refreshkey)
            if keysuccess == "True":
                self.logger.debug("New Key Aquired")
            else:
                #### add code to retry device lookup without getting into crazy loop
                #### set spotify state to offline
                #### wait 30 seconds and try again
                spotifydevicearray.append(("0", "Error in Spotify key Lookup"))

        return spotifydevicearray

    #020
    def playselectedplaylist(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifydevice = getspotifydevice(self.logger, device)

        spotifydata = {"context_uri": "spotify:user:" + device.states["playlistuserid"] + ":playlist:" + device.states["playlistid"], "device_ids": [spotifydevice]}
        response = callspotifycommand(self.logger, "020", device, "put", "https://api.spotify.com/v1/me/player/play", spotifydata)

        if response != "Error":
            device.updateStateOnServer("state", value="playing")

    #021
    def playplaylist(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifydevice = getspotifydevice(self.logger, device)
        selectedplaylist = int(pluginAction.props["PlaySelectedPlaylist"])
        playlistid = device.states["playlistid_" + str(selectedplaylist)]
        playlistuser = device.states["playlistuser_" + str(selectedplaylist)]

        spotifydata = {"context_uri": "spotify:user:" + playlistuser + ":playlist:" + playlistid, "device_ids": [spotifydevice]}
        response = callspotifycommand(self.logger, "021", device, "put", "https://api.spotify.com/v1/me/player/play", spotifydata)

        if response != "Error":
            device.updateStateOnServer("state", value="playing")

    def validatespotifyid(self, valuesDict, typeId, devId):
        device = indigo.devices[devId]
        device.replacePluginPropsOnServer(valuesDict)
        indigo.server.log("Updating Spotify device list")