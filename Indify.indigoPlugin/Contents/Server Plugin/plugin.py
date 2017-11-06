#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com
#version 1.0.2 - Private Beta

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

def getspotifydevice(device):

    spotifyid = ""

    try:
        spotifykey = device.pluginProps["SpotifyKey"]
        spotifydevice = device.pluginProps["SpotifyDevice"]
        spotifyurl = "https://api.spotify.com/v1/me/player/devices"
        spotifyheader = {"Authorization": "Bearer " + spotifykey}

        response = requests.get(spotifyurl, headers=spotifyheader, timeout=(1, 6))

        data = json.loads(response.text)
        for spotifydevices in data['devices']:
            if spotifydevices['name'] == spotifydevice:
                spotifyid=(spotifydevices['id'])
    except:
        indigo.server.log("Spotify not authenticated")

    return spotifyid

def RefreshKey(device, refreshkey):
    indigo.server.log("refresh key")

    clientid = "9b907857f3644732bfa45d4ec0ba6601"
    secretkey = "c5bc817f12f7435f91c3ee450272da29"

    spotifyurl = "https://accounts.spotify.com/api/token"
    spotifydata = {'grant_type': 'refresh_token', 'refresh_token': refreshkey}
    response = requests.post(spotifyurl, data=spotifydata, auth=(clientid, secretkey))

    tokendata = json.loads(response.text)

    # check for success
    localPropsCopy = device.pluginProps
    localPropsCopy['SpotifyKey'] = str(tokendata['access_token'])
    device.replacePluginPropsOnServer(localPropsCopy)

def GetCurrentSong(spotifykey):
    # indigo.server.log("current song")

    spotifyurl = "https://api.spotify.com/v1/me/player/currently-playing"
    spotifyheader = {"Authorization": "Bearer " + spotifykey}

    response = requests.get(spotifyurl, headers=spotifyheader, timeout=(1, 6))
    # indigo.server.log(str(response))
    #indigo.server.log("resp:" + str(response.text))

    if str(response) == "<Response [200]>":
        try:
            data = json.loads(response.text)

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
            indigo.server.log('error 95a:' + str(errtxt) + ":" + str(response))

    else:
        return False

def UpdateCurrentSong(device, playingsong):
    currenttrackid = device.states["c_track_id"]
    previoustrackid = device.states["p_track_id"]

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

def UpdateCurrentImage(large, medium, small):
    # indigo.server.log("update image")

    maindirectory = "/Library/Application Support/Perceptive Automation/Indigo 7/IndigoWebServer/plugins/Indify/"
    largeimage1 = maindirectory + "largeimage1.png"
    largeimage2 = maindirectory + "largeimage2.png"
    mediumimage1 = maindirectory + "mediumimage1.png"
    mediumimage2 = maindirectory + "mediumimage2.png"
    smallimage1 = maindirectory + "smallimage1.png"
    smallimage2 = maindirectory + "smallimage2.png"

    if not os.path.exists(maindirectory):
        os.makedirs(maindirectory)

    # load large image
    if os.path.exists(largeimage1):
        copyfile(largeimage1, largeimage2)
        os.remove(largeimage1)
    try:
        imgdata = requests.get(large).content
        with open(largeimage1, 'wb') as handler:
            handler.write(imgdata)
    except Exception as errtxt:
        img = "error 110"

    # load medium image
    if os.path.exists(mediumimage1):
        copyfile(mediumimage1, mediumimage2)
        os.remove(mediumimage1)
    try:
        imgdata = requests.get(medium).content
        with open(mediumimage1, 'wb') as handler:
            handler.write(imgdata)
    except Exception as errtxt:
        img = "error 120"

    # load small image
    if os.path.exists(smallimage1):
        copyfile(smallimage1, smallimage2)
        os.remove(smallimage1)
    try:
        imgdata = requests.get(small).content
        with open(smallimage1, 'wb') as handler:
            handler.write(imgdata)
    except Exception as errtxt:
        img = "error 130"

def LoadPlayListPage(device, spotifykey, pagenumber, itemsperpage):
    if pagenumber < 1:
        pagenumber = 1

    playlistpage = ((pagenumber - 1) * itemsperpage) #+ 1
    # indigo.server.log(str(playlistpage))

    spotifyurl = "https://api.spotify.com/v1/me/playlists"
    spotifyheader = {"Authorization": "Bearer " + spotifykey}
    spotifyparam = {'limit': itemsperpage, 'offset': playlistpage}
    playlistcounter = 0
    response = requests.get(spotifyurl, headers=spotifyheader, params=spotifyparam)
    # indigo.server.log(str(response))

    if str(response) != "<Response [401]>":
        data = json.loads(response.text)
        #indigo.server.log(str(data['total']))
        device.updateStateOnServer("totalplaylists", value=data['total'])

        if len(data['items']) > 0:
            for playlistcounter in range(1, 11):
                device.updateStateOnServer("playlist_" + str(playlistcounter), value="")
                device.updateStateOnServer("playlistid_" + str(playlistcounter), value="")
                device.updateStateOnServer("playlistuser_" + str(playlistcounter), value="")
            playlistcounter = 0
            for playlist in data['items']:
                playlistcounter = playlistcounter + 1
                device.updateStateOnServer("playlist_" + str(playlistcounter), value=playlist['name'])
                device.updateStateOnServer("playlistid_" + str(playlistcounter), value=playlist['id'])
                device.updateStateOnServer("playlistuser_" + str(playlistcounter), value=playlist['owner']['id'])
            device.updateStateOnServer("playlistpage", value=str(pagenumber))

def LoadPlaylistDetail(device, spotifykey, userid, playlistid):
    # indigo.server.log("test")
    spotifyurl = "https://api.spotify.com/v1/users/" + userid + "/playlists/" + playlistid
    spotifyheader = {"Authorization": "Bearer " + spotifykey}
    spotifyparam = {"fields": "name,description,id"}
    response = requests.get(spotifyurl, headers=spotifyheader, params=spotifyparam)

    # indigo.server.log(spotifyurl)
    # indigo.server.log(str(response))

    if str(response) != "<Response [401]>":
        data = json.loads(response.text)
        # indigo.server.log(data['description'])
        device.updateStateOnServer("playlistname", value=data['name'])
        device.updateStateOnServer("playlistdescription", value=data['description'])
        device.updateStateOnServer("playlistid", value=data['id'])
        device.updateStateOnServer("playlistuserid", value=userid)

def GetUserName(spotifykey):
    spotifyurl = "https://api.spotify.com/v1/me"
    spotifyheader = {"Authorization": "Bearer " + spotifykey}
    response = requests.get(spotifyurl, headers=spotifyheader)

    if str(response) != "<Response [401]>":
        data = json.loads(response.text)
        indigo.server.log(str(len(data)))
        return data['id']

def LoadTrackPage(device, userid, playlistid, spotifykey, pagenumber, itemsperpage):
    # indigo.server.log("mark 1: " + str(pagenumber))
    if pagenumber < 1:
        pagenumber = 1

    trackpage = ((pagenumber - 1) * itemsperpage) + 1
    # indigo.server.log(str(trackpage))

    spotifyurl = "https://api.spotify.com/v1/users/" + userid + "/playlists/" + playlistid + "/tracks"
    spotifyheader = {"Authorization": "Bearer " + spotifykey}
    spotifyparam = {'limit': itemsperpage, 'offset': trackpage}
    trackcounter = 0
    response = requests.get(spotifyurl, headers=spotifyheader, params=spotifyparam)
    # indigo.server.log(str(response))

    if str(response) != "<Response [401]>":
        data = json.loads(response.text)
        # indigo.server.log(str(len(data['items'])))
        device.updateStateOnServer("totaltracks", value=data['total'])

        if len(data['items']) > 0:
            for trackcounter in range(1, 11):
                device.updateStateOnServer("trackname_" + str(trackcounter), value="")
                device.updateStateOnServer("trackartist_" + str(trackcounter), value="")
            trackcounter = 0
            for tracks in data['items']:
                trackname = tracks['track']['name']
                artist = tracks['track']['album']['artists'][0]['name']
                trackcounter = trackcounter + 1
                device.updateStateOnServer("trackname_" + str(trackcounter), value=trackname)
                device.updateStateOnServer("trackartist_" + str(trackcounter), value=artist)
            device.updateStateOnServer("trackpage", value=str(pagenumber))

def GetPlayerState(spotifykey):
    spotifyurl = "https://api.spotify.com/v1/me/player"
    spotifyheader = {"Authorization": "Bearer " + spotifykey}
    response = requests.get(spotifyurl, headers=spotifyheader)

    if str(response) != "<Response [401]>":
        data = json.loads(response.text)
        return {'shuffle':data['shuffle_state'],
                'repeat':data['repeat_state'],
                'spotifydevice':data['device']['id'],
                'spotifydevicename':data['device']['name'],
                'spotifyvolume': data['device']['volume_percent']}
    else:
        return False

def ChangeShuffle(spotifykey,shuffleaction):
    spotifyurl = "https://api.spotify.com/v1/me/player/shuffle"
    spotifyheader = {"Authorization": "Bearer " + spotifykey}
    spotifyparam ={"state": shuffleaction}
    response = requests.put(spotifyurl, headers=spotifyheader, params=spotifyparam)

def ChangeRepeat(spotifykey,repeataction):
    spotifyurl = "https://api.spotify.com/v1/me/player/repeat"
    spotifyheader = {"Authorization": "Bearer " + spotifykey}
    spotifyparam ={"state": repeataction}
    response = requests.put(spotifyurl, headers=spotifyheader, params=spotifyparam)

def SetVolume(spotifykey, newvolume):
    spotifyurl = "https://api.spotify.com/v1/me/player/volume"
    spotifyheader = {"Authorization": "Bearer " + spotifykey}
    spotifyparam ={"volume_percent": newvolume}
    response = requests.put(spotifyurl, headers=spotifyheader, params=spotifyparam)

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
                    spotifydevice = getspotifydevice(device)

                    if state == "playing":
                        timeremaining = timeremaining - 1000
                        device.updateStateOnServer("timeremaining", value=timeremaining)
                        consec, conmin = convertms(timeremaining)
                        device.updateStateOnServer("timeremainingtext", value=str(conmin) + ":" + str(consec).zfill(2))

                    refreshcycle = refreshcycle + 1

                    if timeremaining < 0 or refreshcycle > refreshduration:
                        refreshcycle = 0
                        playingsong = False
                        playerstate = False
                        # indigo.server.log("getting new song")

                        spotifykey = device.pluginProps["SpotifyKey"]
                        refreshkey = device.pluginProps["RefreshKey"]

                        try:
                            playerstate = GetPlayerState(spotifykey)
                        except Exception as errtxt:
                            indigo.server.log('error 85:' + str(errtxt))

                        try:
                            if not playerstate == False:
                                if int(playerstate['spotifyvolume']) != int(device.states["volume"]):
                                    device.updateStateOnServer("volume", playerstate['spotifyvolume'])

                                if playerstate['repeat'] != device.states["repeat"]:
                                    if device.states["repeat"] == "off":
                                        device.updateStateOnServer("repeat", value="context")
                                    else:
                                        device.updateStateOnServer("repeat", value="off")

                                if str(playerstate['shuffle']) != str(device.states["shuffle"]):
                                    if str(device.states["shuffle"]) == "False":
                                        device.updateStateOnServer("shuffle", value="True")
                                    else:
                                        device.updateStateOnServer("shuffle", value="False")

                        except Exception as errtxt:
                            indigo.server.log('error 90:' + str(errtxt))

                        try:
                            playingsong = GetCurrentSong(spotifykey)
                        except Exception as errtxt:
                            indigo.server.log('error 95:' + str(errtxt))

                        try:
                            if not playingsong == False:

                                if playingsong['isplaying']:
                                    device.updateStateOnServer("state", "playing")
                                else:
                                    device.updateStateOnServer("state", "paused")

                                UpdateCurrentSong(device, playingsong)
                                timeremaining = playingsong['duration'] - playingsong['progress']

                                consec, conmin = convertms(playingsong['duration'])
                                device.updateStateOnServer("durationtext",value=str(conmin) + ":" + str(consec).zfill(2))

                            else:
                                RefreshKey(device, refreshkey)

                        except Exception as errtxt:
                            indigo.server.log('error 100:' + str(errtxt))

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
    def toggle(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        state = device.states["state"]
        spotifydevice = getspotifydevice(device)

        if state == "playing":
            spotifyurl = "https://api.spotify.com/v1/me/player/pause"
            spotifyheader = {"Authorization": "Bearer " + spotifykey}
            response = requests.put(spotifyurl, headers=spotifyheader)
            device.updateStateOnServer("state", value="paused")
            ### check response
        else:
            spotifyurl = "https://api.spotify.com/v1/me/player"
            spotifyheader = {"Authorization": "Bearer " + spotifykey}
            spotifydata = {"device_ids":[spotifydevice], "play":True}
            json_string = json.dumps(spotifydata)

            response = requests.put(spotifyurl, headers=spotifyheader, data=json_string)
            device.updateStateOnServer("state", value="playing")

        indigo.server.log(str(response))

            #### check response

    def play(self, pluginAction):

        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        spotifydevice = getspotifydevice(device)

        spotifyurl = "https://api.spotify.com/v1/me/player"
        spotifyheader = {"Authorization": "Bearer " + spotifykey}
        spotifydata = {"device_ids": [spotifydevice], "play": True}
        json_string = json.dumps(spotifydata)

        response = requests.put(spotifyurl, headers=spotifyheader, data=json_string)
        device.updateStateOnServer("state", value="playing")

    ### check response

    def pause(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        spotifyurl = "https://api.spotify.com/v1/me/player/pause"
        spotifyheader = {"Authorization": "Bearer " + spotifykey}
        response = requests.put(spotifyurl, headers=spotifyheader)
        device.updateStateOnServer("state", value="paused")

    #### check response

    def next(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        state = device.states["state"]
        if state == "playing":
            spotifyurl = "https://api.spotify.com/v1/me/player/next"
            spotifyheader = {"Authorization": "Bearer " + spotifykey}
            response = requests.post(spotifyurl, headers=spotifyheader)
            indigo.server.log(str(response))
        ### check response

    def previous(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        state = device.states["state"]
        if state == "playing":
            spotifyurl = "https://api.spotify.com/v1/me/player/previous"
            spotifyheader = {"Authorization": "Bearer " + spotifykey}
            response = requests.post(spotifyurl, headers=spotifyheader)
            indigo.server.log(str(response))
        ### check response

    def repeat(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        repeat = device.states["repeat"]
        if repeat == "off":
            device.updateStateOnServer("repeat", value="context")
            ChangeRepeat(spotifykey, "context")
        else:
            device.updateStateOnServer("repeat", value="off")
            ChangeRepeat(spotifykey, "off")

    def shuffle(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        shuffle = device.states["shuffle"]
        if shuffle == "False":
            device.updateStateOnServer("shuffle", value="True")
            ChangeShuffle(spotifykey, "True")
        else:
            device.updateStateOnServer("shuffle", value="False")
            ChangeShuffle(spotifykey, "False")

    def setvolume(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        newvolume = int(pluginAction.props["setpercent"])
        SetVolume(spotifykey, newvolume)
        device.updateStateOnServer("volume", value=newvolume)

    def increasevolume(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        oldvolume = int(device.states['volume'])
        increasepercent = int(pluginAction.props["increasepercent"])
        if int(oldvolume) < 100:
            newvolume=oldvolume+increasepercent
            SetVolume(spotifykey, newvolume)
            device.updateStateOnServer("volume", value=newvolume)

    def decreasevolume(self, pluginAction):
        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        oldvolume = device.states['volume']
        decreasepercent = int(pluginAction.props["decreasepercent"])
        if int(oldvolume) > 0:
            newvolume=oldvolume - decreasepercent
            SetVolume(spotifykey, newvolume)
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

    def playselectedplaylist(self, pluginAction):

        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]

        spotifyurl = "https://api.spotify.com/v1/me/player/play"
        spotifyheader = {"Authorization": "Bearer " + spotifykey}
        spotifydata = {"context_uri": "spotify:user:" + device.states["playlistuserid"] + ":playlist:" + device.states["playlistid"]}
        json_string = json.dumps(spotifydata)

        response = requests.put(spotifyurl, headers=spotifyheader, data=json_string)
        indigo.server.log(str(response.url))
        indigo.server.log(str(response.text))
        indigo.server.log(str(response))
        device.updateStateOnServer("state", value="playing")
        ### check response

    def playplaylist(self, pluginAction):

        device = indigo.devices[pluginAction.deviceId]
        spotifykey = device.pluginProps["SpotifyKey"]
        spotifydevice = spotifydevices(device)

        selectedplaylist = int(pluginAction.props["PlaySelectedPlaylist"])
        playlistid = device.states["playlistid_" + str(selectedplaylist)]
        playlistuser = device.states["playlistuser_" + str(selectedplaylist)]

        spotifyurl = "https://api.spotify.com/v1/me/player/play"
        spotifyheader = {"Authorization": "Bearer " + spotifykey}
        spotifydata = {"context_uri": "spotify:user:" + playlistuser + ":playlist:" + playlistid, "device_ids": [spotifydevice]}
        json_string = json.dumps(spotifydata)

        response = requests.put(spotifyurl, headers=spotifyheader, data=json_string)
        indigo.server.log(str(response.url))
        indigo.server.log(str(response.text))
        indigo.server.log(str(response))
        device.updateStateOnServer("state", value="playing")
        ### check response

    def getspotifydevices(self, filter, valuesDict, typeId, devId):
        device = indigo.devices[devId]
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
            indigo.server.log("Spotify not authenticated")
            spotifydevicearray.append(("0", "Error in Spotify key Lookup"))

        return spotifydevicearray

    def validatespotifyid(self, valuesDict, typeId, devId):
        device = indigo.devices[devId]
        device.replacePluginPropsOnServer(valuesDict)
        indigo.server.log("Updating Spotify device list")