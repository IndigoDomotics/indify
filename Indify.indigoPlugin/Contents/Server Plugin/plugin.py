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

def spotifyerror(htmlreturn):

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
    elif htmlreturn == '<Response [401]>':
        spotifyerror = "Spotify 401: Unauthorized - The request requires user authentication or, if the request included authorization credentials, authorization has been refused for those credentials."
        spotifylevel = "Unauthorized"
    elif htmlreturn == '<Response [403]>':
        spotifyerror = "Spotify 403: Forbidden - The server understood the request, but is refusing to fulfill it."
        spotifylevel = "Error"
    elif htmlreturn == '<Response [404]>':
        spotifyerror = "Spotify 404: Not Found - The requested resource could not be found. This error can be due to a temporary or permanent condition."
        spotifylevel = 'Error'
    elif htmlreturn == '<Response [429]>':
        spotifyerror = "Spotify 429: Too Many Requests - Rate limiting has been applied."
        spotifylevel = "Error"
    elif htmlreturn == '<Response [500]>':
        spotifyerror = "Spotify 500: Internal Server Error. You should never receive this error because our clever coders catch them all ... but if you are unlucky enough to get one, please report it to us through a comment at the bottom of this page."
        spotifylevel = "Error"
    elif htmlreturn == '<Response [502]>':
        spotifyerror = "Spotify 502: Bad Gateway - The server was acting as a gateway or proxy and received an invalid response from the upstream server."
        spotifylevel = "Error"
    elif htmlreturn == '<Response [503]>':
        spotifyerror = "Spotify 503: Service Unavailable - The server is currently unable to handle the request due to a temporary condition which will be alleviated after some delay. You can choose to resend the request again."
        spotifylevel = "Error"
    else:  # default, could also just omit condition or 'if True'
        spotifyerror = "Error code not found"
        spotifylevel = "Warning"

    return {"errorlevel": spotifylevel, "errormessage": spotifyerror}

def callspotifycommand(callid, device, type, spotifyurl, spotifydata=None, spotifyparams=None):
    spotifydata = spotifydata if spotifydata else {}
    spotifyparams = spotifyparams if spotifyparams else {}
    spotifykey = device.pluginProps["SpotifyKey"]

    spotifyheader = {"Authorization": "Bearer " + spotifykey}
    jsondata = json.dumps(spotifydata)
    returncode = {"errorlevel": "Failed", "errormessage": "Undefined Error"}
    response = ""

    if type == "get":
        try:
            response = requests.get(spotifyurl, headers=spotifyheader, data=jsondata, params=spotifyparams, timeout=(3, 6))
            returncode = spotifyerror(str(response))
        except Exception as errtxt:
            indigo.server.log(callid + ".01: " + str(errtxt) + ":" + str(response))
    elif type == "put":
        try:
            response = requests.put(spotifyurl, headers=spotifyheader, data=jsondata, params=spotifyparams, timeout=(3, 6))
            returncode = spotifyerror(str(response))
        except Exception as errtxt:
            indigo.server.log(callid + ".01: " + str(errtxt) + ":" + str(response))

    if returncode["errorlevel"] == "Success":
        return(response.text)
    elif returncode["errorlevel"] == "Unauthorized":
        refreshkey = device.pluginProps["RefreshKey"]
        RefreshKey(device, refreshkey)
    else:
        indigo.server.log(callid + ".02: " + returncode["errormessage"])
        return("Error")

#001
def getspotifydevice(device):
    deviceid = "Device Not Found"
    restricted = "true"
    response = callspotifycommand("001", device, "get", "https://api.spotify.com/v1/me/player/devices")

    if response != "Error":
        data = json.loads(response)
        spotifydevice = device.pluginProps["SpotifyDevice"]
        for spotifydevices in data['devices']:
            if spotifydevices['name'] == spotifydevice:
                deviceid = (spotifydevices['id'])
                restricted = (spotifydevices['is_restricted'])

    return deviceid

    #if str(restricted) == "true":
        #return deviceid
    #else:
        #indigo.server.log("error 001.5: Device not available")
        #device.updateStateOnServer("state", value="unavailable")
        #return "Unavailable"

#002
def RefreshKey(device, refreshkey):
    indigo.server.log("refresh key")

    clientid = "9b907857f3644732bfa45d4ec0ba6601"
    secretkey = "c5bc817f12f7435f91c3ee450272da29"
    success = "false"

    spotifyurl = "https://accounts.spotify.com/api/token"
    spotifydata = {'grant_type': 'refresh_token', 'refresh_token': refreshkey}
    response = requests.post(spotifyurl, data=spotifydata, auth=(clientid, secretkey))
    returncode = spotifyerror(str(response))

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
def GetCurrentSong(device, spotifykey):
    response = callspotifycommand("003", device, "get", "https://api.spotify.com/v1/me/player/currently-playing", spotifydata="", spotifyparams="")

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
            indigo.server.log('error 003.1: ' + str(errtxt) + ":" + str(response))
    else:
        return False

#004
def UpdateCurrentSong(device, playingsong):
    currenttrackid = device.states["c_track_id"]
    previoustrackid = device.states["p_track_id"]

    try:
        if playingsong['isplaying']:
            device.updateStateOnServer("state", "playing")
            if not currenttrackid:
                device.updateStateOnServer("c_album", value=playingsong['album'])
                device.updateStateOnServer("c_track", value=playingsong['track'])
                device.updateStateOnServer("c_artist", value=playingsong['artist'])
                device.updateStateOnServer("c_track_id", value=playingsong['trackid'])
                device.updateStateOnServer("c_album_id", value=playingsong['albumid'])
                device.updateStateOnServer("c_artist_id", value=playingsong['artistid'])
                device.updateStateOnServer("duration", value=playingsong['duration'])
            elif playingsong['trackid'] <> currenttrackid:
                # update previous
                device.updateStateOnServer("p_album", value=device.states['c_album'])
                device.updateStateOnServer("p_track", value=device.states['c_track'])
                device.updateStateOnServer("p_artist", value=device.states['c_artist'])
                device.updateStateOnServer("p_track_id", value=device.states['c_track_id'])
                device.updateStateOnServer("p_album_id", value=device.states['c_album_id'])
                device.updateStateOnServer("p_artist_id", value=device.states['c_artist_id'])
                # update current song
                device.updateStateOnServer("c_album", value=playingsong['album'])
                device.updateStateOnServer("c_track", value=playingsong['track'])
                device.updateStateOnServer("c_artist", value=playingsong['artist'])
                device.updateStateOnServer("c_track_id", value=playingsong['trackid'])
                device.updateStateOnServer("c_album_id", value=playingsong['albumid'])
                device.updateStateOnServer("c_artist_id", value=playingsong['artistid'])
                device.updateStateOnServer("duration", value=playingsong['duration'])
                # Update images
                UpdateCurrentImage(playingsong['imagelarge'], playingsong['imagemedium'], playingsong['imagesmall'])
        else:
            device.updateStateOnServer("state", "Paused")
    except Exception as errtxt:
        indigo.server.log('error 004: ' + str(errtxt))

#005
def SaveImage(imagename, imageurl):
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
        indigo.server.log('error 005: ' + str(errtxt))

#006
def UpdateCurrentImage(large, medium, small):
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
        SaveImage("largeimage1", large)
    except Exception as errtxt:
        indigo.server.log('error 006.1: ' + str(errtxt))

    # load medium image
    if os.path.exists(mediumimage1):
        copyfile(mediumimage1, mediumimage2)
        os.remove(mediumimage1)
    try:
        SaveImage("mediumimage1", medium)
    except Exception as errtxt:
        indigo.server.log('error 006.2: ' + str(errtxt))

    # load small image
    if os.path.exists(smallimage1):
        copyfile(smallimage1, smallimage2)
        os.remove(smallimage1)
    try:
        SaveImage(smallimage1, small)
    except Exception as errtxt:
        indigo.server.log('error 006.3: ' + str(errtxt))

#007
def LoadPlayListPage(device, spotifykey, pagenumber, itemsperpage):
    if pagenumber < 1:
        pagenumber = 1

    playlistpage = ((pagenumber - 1) * itemsperpage) #+ 1
    playlistcounter = 0
    playlistimages = "no images"

    response = callspotifycommand("007", device, "get", "https://api.spotify.com/v1/me/playlists", "", {'limit': itemsperpage, 'offset': playlistpage})

    #spotifyurl = "https://api.spotify.com/v1/me/playlists"
    #spotifyheader = {"Authorization": "Bearer " + spotifykey}
    #spotifyparam = {'limit': itemsperpage, 'offset': playlistpage}
    #response = requests.get(spotifyurl, headers=spotifyheader, params=spotifyparam)
    # indigo.server.log(str(response))

    if response != "Error":
        data = json.loads(response)
        device.updateStateOnServer("totalplaylists", value=data['total'])
        maindirectory = "/Library/Application Support/Perceptive Automation/Indigo 7/IndigoWebServer/plugins/Indify/"

        if len(data['items']) > 0:
            for playlistcounter in range(1, 11):
                device.updateStateOnServer("playlist_" + str(playlistcounter), value="")
                device.updateStateOnServer("playlistid_" + str(playlistcounter), value="")
                device.updateStateOnServer("playlistuser_" + str(playlistcounter), value="")
                oldplaylistimage = maindirectory + "playlistimage" + str(playlistcounter) + ".png"
                copyfile("./Clear.jpg", oldplaylistimage)

            playlistcounter = 0
            for playlist in data['items']:
                playlistcounter = playlistcounter + 1
                device.updateStateOnServer("playlist_" + str(playlistcounter), value=playlist['name'])
                device.updateStateOnServer("playlistid_" + str(playlistcounter), value=playlist['id'])
                device.updateStateOnServer("playlistuser_" + str(playlistcounter), value=playlist['owner']['id'])
                playlistimages = playlist['images']

                if len(playlistimages) > 0:

                    if len(playlistimages) == 2:
                        imagenumber = 1
                    else:
                        imagenumber = 0

                    try:
                        SaveImage("playlistimage" + str(playlistcounter), playlistimages[imagenumber]["url"])
                    except Exception as errtxt:
                        indigo.server.log("007: No playlist image: " + str(errtxt))

            device.updateStateOnServer("playlistpage", value=str(pagenumber))

#008
def LoadPlaylistDetail(device, spotifykey, userid, playlistid):

    response = callspotifycommand("008", device, "get", "https://api.spotify.com/v1/users/" + userid + "/playlists/" + playlistid, "", {"fields": "name,description,id"})

    #spotifyurl = "https://api.spotify.com/v1/users/" + userid + "/playlists/" + playlistid
    #spotifyheader = {"Authorization": "Bearer " + spotifykey}
    #spotifyparam = {"fields": "name,description,id"}
    #response = requests.get(spotifyurl, headers=spotifyheader, params=spotifyparam)

    # indigo.server.log(spotifyurl)
    # indigo.server.log(str(response))

    if response != "Error":
        data = json.loads(response)
        device.updateStateOnServer("playlistname", value=data['name'])
        device.updateStateOnServer("playlistdescription", value=data['description'])
        device.updateStateOnServer("playlistid", value=data['id'])
        device.updateStateOnServer("playlistuserid", value=userid)

#009
def GetUserName(spotifykey):

    response = callspotifycommand("009", device, "get", "https://api.spotify.com/v1/me", "", {"fields": "name,description,id"})
    #spotifyurl = "https://api.spotify.com/v1/me"
    #spotifyheader = {"Authorization": "Bearer " + spotifykey}
    #response = requests.get(spotifyurl, headers=spotifyheader)

    if response != "Error":
        data = json.loads(response)
        return data['id']

#010
def LoadTrackPage(device, userid, playlistid, spotifykey, pagenumber, itemsperpage):

    if pagenumber < 1:
        pagenumber = 1
    trackpage = ((pagenumber - 1) * itemsperpage) + 1
    trackcounter = 0

    #spotifyurl = "https://api.spotify.com/v1/users/" + userid + "/playlists/" + playlistid + "/tracks"
    #spotifyheader = {"Authorization": "Bearer " + spotifykey}
    #spotifyparam = {'limit': itemsperpage, 'offset': trackpage}
    #response = requests.get(spotifyurl, headers=spotifyheader, params=spotifyparam)
    # indigo.server.log(str(response))

    response = callspotifycommand("010", device, "get", "https://api.spotify.com/v1/users/" + userid + "/playlists/" + playlistid + "/tracks", "", {'limit': itemsperpage, 'offset': trackpage})

    if response != "Error":
        data = json.loads(response)
        device.updateStateOnServer("totaltracks", value=data['total'])

        indigo.server.log(str(len(data['items'])))
        if len(data['items']) > 0:
            for trackcounter in range(1, 11):
                device.updateStateOnServer("trackname_" + str(trackcounter), value="")
                device.updateStateOnServer("trackartist_" + str(trackcounter), value="")
            trackcounter = 0
            for tracks in data['items']:
                trackname = tracks['track']['name']
                indigo.server.log(str(trackcounter))
                try:
                    artist = tracks['track']['album']['artists'][0]['name']
                except Exception as errtxt:
                    artist = "Unknown"
                trackcounter = trackcounter + 1
                device.updateStateOnServer("trackname_" + str(trackcounter), value=trackname)
                device.updateStateOnServer("trackartist_" + str(trackcounter), value=artist)
            device.updateStateOnServer("trackpage", value=str(pagenumber))

#011
def GetPlayerState(device, spotifykey):
    response = callspotifycommand("011", device, "get", "https://api.spotify.com/v1/me/player", "", "")

    if response != "Error":
        data = json.loads(response)

        return {'isplaying':data['is_playing'],
                'shuffle':data['shuffle_state'],
                'repeat':data['repeat_state'],
                'spotifydevice':data['device']['id'],
                'spotifydevicename':data['device']['name'],
                'spotifyvolume': data['device']['volume_percent']}
    else:
        return "False"

#012
def ChangeShuffle(device, spotifykey,shuffleaction):
    #spotifyurl = "https://api.spotify.com/v1/me/player/shuffle"
    #spotifyheader = {"Authorization": "Bearer " + spotifykey}
    #spotifyparam ={"state": shuffleaction}
    #response = requests.put(spotifyurl, headers=spotifyheader, params=spotifyparam)
    response = callspotifycommand("012", device, "put", "https://api.spotify.com/v1/me/player/shuffle", "", {"state": shuffleaction})

#013
def ChangeRepeat(device, spotifykey,repeataction):
    #spotifyurl = "https://api.spotify.com/v1/me/player/repeat"
    #spotifyheader = {"Authorization": "Bearer " + spotifykey}
    #spotifyparam ={"state": repeataction}
    #response = requests.put(spotifyurl, headers=spotifyheader, params=spotifyparam)
    response = callspotifycommand("013", device, "put", "https://api.spotify.com/v1/me/player/repeat", "", {"state": repeataction})

#014
def SetVolume(device, spotifykey, newvolume):
    #spotifyurl = "https://api.spotify.com/v1/me/player/volume"
    #spotifyheader = {"Authorization": "Bearer " + spotifykey}
    #spotifyparam ={"volume_percent": newvolume}
    #response = requests.put(spotifyurl, headers=spotifyheader, params=spotifyparam)
    response = callspotifycommand("014", device, "put", "https://api.spotify.com/v1/me/player/volume", "", {"volume_percent": newvolume})

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
                            playerstate = GetPlayerState(device, spotifykey)
                        except Exception as errtxt:
                            indigo.server.log('error 85:' + str(errtxt))

                        if str(playerstate) != "False" and (str(playerstate['isplaying']) == "True"):
                            spotifydevice = playerstate['spotifydevice']
                            device.updateStateOnServer("state", "playing")

                            #Check volume
                            if int(playerstate['spotifyvolume']) != int(device.states["volume"]):
                                device.updateStateOnServer("volume", playerstate['spotifyvolume'])

                            #Check repeat
                            if playerstate['repeat'] != device.states["repeat"]:
                                if device.states["repeat"] == "off":
                                    device.updateStateOnServer("repeat", value="context")
                                else:
                                    device.updateStateOnServer("repeat", value="off")

                            #Check shuffle
                            if str(playerstate['shuffle']) != str(device.states["shuffle"]):
                                if str(device.states["shuffle"]) == "False":
                                    device.updateStateOnServer("shuffle", value="True")
                                else:
                                    device.updateStateOnServer("shuffle", value="False")

                            #Update song information
                            playingsong = GetCurrentSong(device, spotifykey)
                            timeremaining = playingsong['duration'] - playingsong['progress']
                            consec, conmin = convertms(playingsong['duration'])
                            device.updateStateOnServer("durationtext", value=str(conmin) + ":" + str(consec).zfill(2))

                            if playingsong['track'] != device.states["c_track"]:
                                UpdateCurrentSong(device, playingsong)

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
            indigo.server.log("Running the most recent version of Indyfy")
        else:
            indigo.server.log(
                "The current version of Indyfy is " + str(CurrentVersion) + " and the running version " + str(
                    ActiveVersion) + ".")

    def updatePlugin(self):
        ActiveVersion = str(self.pluginVersion)
        CurrentVersion = str(self.updater.getVersion())
        if ActiveVersion == CurrentVersion:
            indigo.server.log("Already running the most recent version of Indyfy")
        else:
            indigo.server.log(
                "The current version of Indyfy is " + str(CurrentVersion) + " and the running version " + str(
                    ActiveVersion) + ".")
            self.updater.update()

    def RefreshKey(self):
        indigo.server.log("?? Refresh Key")

    ############################################################################
    # Plugin Actions object callbacks
    ############################################################################
    #015
    def toggle(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        state = device.states["state"]
        spotifydevice = getspotifydevice(device)

        if state == "playing":
            response = callspotifycommand("015", device, "put", "https://api.spotify.com/v1/me/player/pause")
            if response != "Error":
                device.updateStateOnServer("state", value="paused")

        else:
            response = callspotifycommand("015", device, "put", "https://api.spotify.com/v1/me/player/", {"device_ids":[spotifydevice], "play":True})
            if response != "Error":
                device.updateStateOnServer("state", value="playing")

    #016
    def play(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifydevice = getspotifydevice(device)

        response = callspotifycommand("016", device, "put", "https://api.spotify.com/v1/me/player/",{"device_ids": [spotifydevice], "play": True})
        if response != "Error":
            device.updateStateOnServer("state", value="playing")

    #017
    def pause(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        response = callspotifycommand("017", device, "put", "https://api.spotify.com/v1/me/player/pause")
        if response != "Error":
            device.updateStateOnServer("state", value="paused")

    #018
    def next(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        state = device.states["state"]
        if state == "playing":
            spotifyurl = "https://api.spotify.com/v1/me/player/next"
            response = callspotifycommand("018", device, "put", "https://api.spotify.com/v1/me/player/next")

    #019
    def previous(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        state = device.states["state"]
        if state == "playing":
            spotifyurl = "https://api.spotify.com/v1/me/player/next"
            response = callspotifycommand("019", device, "put", "https://api.spotify.com/v1/me/player/previous")

    def repeat(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        repeat = device.states["repeat"]
        if repeat == "off":
            device.updateStateOnServer("repeat", value="context")
            ChangeRepeat(device, spotifykey, "context")
        else:
            device.updateStateOnServer("repeat", value="off")
            ChangeRepeat(device, spotifykey, "off")

    def shuffle(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        shuffle = device.states["shuffle"]
        if shuffle == "False":
            device.updateStateOnServer("shuffle", value="True")
            ChangeShuffle(device, spotifykey, "True")
        else:
            device.updateStateOnServer("shuffle", value="False")
            ChangeShuffle(device, spotifykey, "False")

    def setvolume(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        newvolume = int(pluginAction.props["setpercent"])
        SetVolume(device, spotifykey, newvolume)
        device.updateStateOnServer("volume", value=newvolume)

    def increasevolume(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        oldvolume = int(device.states['volume'])
        increasepercent = int(pluginAction.props["increasepercent"])
        if int(oldvolume) < 100:
            newvolume=oldvolume+increasepercent
            SetVolume(device, spotifykey, newvolume)
            device.updateStateOnServer("volume", value=newvolume)

    def decreasevolume(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        oldvolume = device.states['volume']
        decreasepercent = int(pluginAction.props["decreasepercent"])
        if int(oldvolume) > 0:
            newvolume=oldvolume - decreasepercent
            SetVolume(device, spotifykey, newvolume)
            device.updateStateOnServer("volume", value=newvolume)

    def loadplaylistpage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        state = device.states["state"]
        itemsperpage = int(device.pluginProps["PlaylistsPerPage"])

        pagenumber = int(pluginAction.props["pagenumber"])
        LoadPlayListPage(device, spotifykey, pagenumber, itemsperpage)

    def nextplaylistpage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        playlistpage = int(device.states["playlistpage"])
        itemsperpage = int(device.pluginProps["PlaylistsPerPage"])

        pagenumber = playlistpage + 1
        LoadPlayListPage(device, spotifykey, pagenumber, itemsperpage)

    def previousplaylistpage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        playlistpage = int(device.states["playlistpage"])
        itemsperpage = int(device.pluginProps["PlaylistsPerPage"])

        pagenumber = playlistpage - 1
        LoadPlayListPage(device, spotifykey, pagenumber, itemsperpage)

    def selectplaylist(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]

        selectedplaylist = int(pluginAction.props["selectedplaylist"])
        playlistid = device.states["playlistid_" + str(selectedplaylist)]
        playlistuser = device.states["playlistuser_" + str(selectedplaylist)]
        LoadPlaylistDetail(device, spotifykey, playlistuser, playlistid)
        itemsperpage = int(device.pluginProps["TracksPerPage"])
        LoadTrackPage(device, playlistuser, playlistid, spotifykey, 1, itemsperpage)

    def loadtrackspage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        pagenumber = int(pluginAction.props["trackpagenumber"])
        playlistid = device.states["playlistid"]
        playlistuser = device.states["playlistuserid"]
        itemsperpage = int(device.pluginProps["TracksPerPage"])

        LoadTrackPage(device, playlistuser, playlistid, spotifykey, pagenumber, itemsperpage)

    def nexttrackspage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        trackpage = int(device.states["trackpage"])
        playlistid = device.states["playlistid"]
        playlistuser = device.states["playlistuserid"]
        itemsperpage = int(device.pluginProps["TracksPerPage"])

        pagenumber = trackpage + 1
        LoadTrackPage(device, playlistuser, playlistid, spotifykey, pagenumber, itemsperpage)

    def previoustrackspage(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        trackpage = int(device.states["trackpage"])
        playlistid = device.states["playlistid"]
        playlistuser = device.states["playlistuserid"]
        itemsperpage = int(device.pluginProps["TracksPerPage"])

        pagenumber = trackpage - 1
        LoadTrackPage(device, playlistuser, playlistid, spotifykey, pagenumber, itemsperpage)

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
            keysuccess = RefreshKey(device, refreshkey)
            if keysuccess == "True":
                indigo.server.log("New Key Aquired")
            else:
                #### add code to retry device lookup without getting into crazy loop
                #### set spotify state to offline
                #### wait 30 seconds and try again
                spotifydevicearray.append(("0", "Error in Spotify key Lookup"))

        return spotifydevicearray

    #020
    def playselectedplaylist(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifydevice = getspotifydevice(device)

        spotifydata = {"context_uri": "spotify:user:" + device.states["playlistuserid"] + ":playlist:" + device.states["playlistid"], "device_ids": [spotifydevice]}
        response = callspotifycommand("020", device, "put", "https://api.spotify.com/v1/me/player/play", spotifydata)

        if response != "Error":
            device.updateStateOnServer("state", value="playing")

    #021
    def playplaylist(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifydevice = getspotifydevice(device)
        selectedplaylist = int(pluginAction.props["PlaySelectedPlaylist"])
        playlistid = device.states["playlistid_" + str(selectedplaylist)]
        playlistuser = device.states["playlistuser_" + str(selectedplaylist)]

        spotifydata = {"context_uri": "spotify:user:" + playlistuser + ":playlist:" + playlistid, "device_ids": [spotifydevice]}
        response = callspotifycommand("021", device, "put", "https://api.spotify.com/v1/me/player/play", spotifydata)

        if response != "Error":
            device.updateStateOnServer("state", value="playing")

    def validatespotifyid(self, valuesDict, typeId, devId):
        device = indigo.devices[devId]
        device.replacePluginPropsOnServer(valuesDict)
        indigo.server.log("Updating Spotify device list")