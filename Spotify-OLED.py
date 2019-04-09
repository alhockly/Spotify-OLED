#!/usr/bin/env python3
import os
import sys
import time
import signal
import json
import spotipy
import spotipy.util as util
import time
import json

from luma.core.render import canvas
from PIL import ImageFont
from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1309, ssd1325, ssd1331, sh1106
from threading import Thread
import threading
from json.decoder import JSONDecodeError
from datetime import datetime
from datetime import timedelta
import RPi.GPIO as GPIO





font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "fonts",'cour.ttf'))

font = ImageFont.truetype(font_path, 18)

# rev.1 users set port=0
# substitute spi(device=0, port=0) below if using that interface
serial = i2c(port=1, address=0x3C)

# substitute ssd1331(...) or sh1106(...) below if using that device
device = ssd1306(serial)
Width=128
Height=64

scrollspeed=5
scrollbackspeed=8
songfontsize=19
artistfontsize=17
networktimeout=3

client_id = 
client_secret = 
redirect_uri = 'http://localhost/'

username = 
scope = 'user-read-playback-state user-library-modify'

saved=False




GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


class Spotify:

    def my_callback(self,channel):

        try:

            ##https://developer.spotify.com/documentation/web-api/reference/library/save-tracks-user/
            ids=[]
            ids.append(self.trackuri)
            results = self.sp.current_user_saved_tracks_add(tracks=ids)
            print("Added track to saved tracks")
            global saved
            saved=True

        except TypeError:
            print("nothing playing to like")


    def __init__(self, username, scope, client_id, client_secret, redirect_uri):
        GPIO.add_event_detect(21, GPIO.BOTH, callback=self.my_callback, bouncetime=300)
        self.username = username
        self.scope = scope
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.nothingplaying = True
        self.track=""

        self.durationMs = 1
        self.progressMs = 1
        self.shuffleState = False
        self.isPlaying = False

        try:
            self.token = util.prompt_for_user_token(username, scope, client_id, client_secret, redirect_uri)

        except (AttributeError, JSONDecodeError):
            os.remove(".cache-{}".format(username))
            self.token = util.prompt_for_user_token(username, scope, client_id, client_secret, redirect_uri)


    def reload(self):
        try:
            if self.token:
                self.sp = spotipy.Spotify(auth=self.token)

                try:
                    playback = self.sp.current_playback()

                    try:
                        self.track = playback['item']['name']
                        self.trackuri = playback['item']["uri"]
                        self.artists = playback['item']['artists']
                        self.durationMs = playback['item']['duration_ms']
                        self.progressMs = playback['progress_ms']
                        self.shuffleState = playback['shuffle_state']
                        self.isPlaying = playback['is_playing']
                        self.nothingplaying=False
                    except TypeError:
                        self.nothingplaying=True

                except spotipy.client.SpotifyException:
                    print("token expired getting new one")
                    # re-authenticate when token expires
                    self.token = util.prompt_for_user_token(username, scope, client_id, client_secret, redirect_uri)
                    self.sp = spotipy.Spotify(auth=self.token)

                    try:
                        playback = self.sp.current_playback()
                        self.track = playback['item']['name']
                        self.trackuri = playback['item']["uri"]
                        self.artists = playback['item']['artists']
                        self.durationMs = playback['item']['duration_ms']
                        self.progressMs = playback['progress_ms']
                        self.shuffleState = playback['shuffle_state']
                        self.isPlaying = playback['is_playing']
                        self.nothingplaying=False
                    except TypeError:
                        self.nothingplaying = True

            else:
                print("Unable to retrieve current playback - Can't get token for ", username)
        except:
            print("network fail")


    def __str__(self):
        if self.isPlaying and not self.nothingplaying:
            return "playing "+self.track+" by "+str(self.artists[0]["name"])+" from Spotify"
        return "nothing playing"



class Scrollthread(Thread):

    def __init__(self, word,fontsize,ypos):
        Thread.__init__(self)
        self.word=word
        self.end=False
        self.Width=Width
        self.x=5
        self.ypos=ypos
        self.font = ImageFont.truetype(font_path, fontsize)
        self.move=False          ##true= moving to the right
        self.scrolling = False
        self.nothingplaying=False
        with canvas(device) as draw:
            self.w,self.h = draw.textsize(self.word,font=self.font)


    def calcscrolling(self):
        with canvas(device) as draw:
            self.w, self.h = draw.textsize(self.word, font=self.font)
            if(self.w>Width+2):
                self.scrolling=True


    def run(self):  ##scroll
        #print("scrolling",self.word)

        while True:
            lastmove =self.move
            if(self.scrolling and self.end==False):                     ###This could be cleaner by only using one while loop and a reverse variable

                if(self.move):
                    self.x += scrollbackspeed
                else:
                    self.x -= scrollspeed

                if (self.x < ((Width-self.w)-10) and self.move==False):      #was moving left and has moved enough
                    self.move=True

                else:
                    if((self.x>0 and self.move==True)):                     #was moving right and more than 0
                        self.move=False


                if(self.move==False and lastmove==True):
                    self.end=True
                    self.x=0
                    time.sleep(3)
            time.sleep(.2)


    def drawobj(self):
        if not self.nothingplaying:
            draw.text((self.x, self.ypos), self.word, font=self.font, fill="white")
            #print("drawn at",self.x,self.ypos)



class Seekthread(Thread):
    def __init__(self,currentpos,songlen,isplaying):
        Thread.__init__(self)
        self.padding=2
        self.currentpos=currentpos
        self.lasttime=int(time.time())
        self.songlen=songlen
        self.end=False
        self.isplaying=isplaying            ####these sound the same but they are different. isplaying ->  music playing (true) or is paused (false)
        self.nothingplaying=False           ##There are no devices connected to spotify, or an advert is playing (true), no device connected (false)


    def run(self):
        while True:

            diff=time.time()-self.lasttime
            self.lasttime=time.time()
            self.currentpos+=diff
            percent=self.currentpos/self.songlen
            #print(int(percent*100),"%")
            self.xpos=int((percent)*(Width-self.padding*2))+2
            if(percent>=1):
                self.end=True
            else:
                self.end=False
            time.sleep(1)

    def setcurrentpos(self,currentpos):
        self.currentpos=currentpos

    def drawobj(self):
        if not self.nothingplaying:
            if(self.isplaying):
                draw.rectangle((5, (Height - 6), (Width - 5), (Height - 2)), "black", "white",1)  ###scroll bar 6 high with 5 xpadding and 2 bottom padding
                ##10 high * 4 wide current position marker
                draw.rectangle((self.xpos - 2, (Height - 10), (self.xpos + 2), (Height)), "black", "white", 4)
            else:
                ####draw pause
                draw.rectangle((66, (Height - 14), (70), (Height)), "black", "white", 2)
                draw.rectangle((54, (Height - 14), (58), (Height)), "black", "white", 2)
        else:
            font = ImageFont.truetype(font_path, 12)
            w,h = draw.textsize("Nothing playing",font)
            draw.text(((Width/2)-(w/2),Height-h),"Nothing playing",font=font,fill="white")


def removefeat(trackname):
    if "(feat" in trackname:
        start = trackname.index("(feat")
        end=trackname.index(")")+2
        return trackname.replace(trackname[start:end],"")
    if "(with." in trackname:
        start = trackname.index("(with.")
        end.trackname.index(")")+2
        return trackname.replace(trackname[start:end], "")
    if "(featuring." in trackname:
        start = trackname.index("(featuring.")
        end.trackname.index(")")+2
        return trackname.replace(trackname[start:end], "")

    return trackname

def concatartists(artists):
    if len(artists)>1:
        names =""
        names+=artists[0]["name"]
        for i in range(1,len(artists)):
            names+=","+artists[i]["name"]
        return names
    else:
        return artists[0]["name"]




if __name__ == "__main__":
    try:
        with canvas(device) as draw:
            loadfont = ImageFont.truetype(font_path, 12)
            w, h = draw.textsize("loading", loadfont)
            draw.text(((Width/2)-(w/2), 32), "loading", font=loadfont, fill="white")

        spotifyobj= Spotify(username=username,scope=scope,client_id=client_id,client_secret=client_secret,redirect_uri=redirect_uri)

        lastsong=""
        spotifyobj.reload()

        justdrawtime = datetime.now() + timedelta(seconds=networktimeout)

        try:
            songscrollthread = Scrollthread(word=removefeat(spotifyobj.track), fontsize=songfontsize, ypos=5)
            artistscrollthread = Scrollthread(word=spotifyobj.artists[0]["name"], fontsize=artistfontsize, ypos=30)

        except:         ##there is no data as nothing is playing
            songscrollthread = Scrollthread(word="", fontsize=songfontsize, ypos=5)
            artistscrollthread = Scrollthread(word="", fontsize=artistfontsize, ypos=30)

        playing = True
        try:
            playing = spotifyobj.isPlaying
            lastsong = spotifyobj.track + spotifyobj.artists[0]["name"]
        except AttributeError:
            pass

        songscrollthread.start()
        artistscrollthread.start()
        seekthread = Seekthread((spotifyobj.progressMs / 1000), (spotifyobj.durationMs / 1000), isplaying=playing)
        seekthread.nothingplaying = spotifyobj.nothingplaying
        seekthread.start()

        with canvas(device) as draw:

            if not spotifyobj.nothingplaying:
                songscrollthread.drawobj()
                artistscrollthread.drawobj()
                seekthread.drawobj()

        while True:


            try:
                playing = spotifyobj.isPlaying
                lastsong=spotifyobj.track+spotifyobj.artists[0]["name"]
            except AttributeError:
                pass
            print(spotifyobj)

            songscrollthread.nothingplaying=spotifyobj.nothingplaying
            songscrollthread.scrolling=False
            songscrollthread.x=0
            songscrollthread.word=removefeat(spotifyobj.track)
            songscrollthread.calcscrolling()

            artistscrollthread.scrolling = False
            artistscrollthread.x = 0
            artistscrollthread.nothingplaying=spotifyobj.nothingplaying
            try:
                artistscrollthread.word = concatartists(spotifyobj.artists)
            except:
               pass
            artistscrollthread.calcscrolling()


            seekthread.currentpos = spotifyobj.progressMs / 1000
            seekthread.songlen=spotifyobj.durationMs/1000
            seekthread.isplaying = spotifyobj.isPlaying
            seekthread.nothingplaying=spotifyobj.nothingplaying


            if spotifyobj.progressMs<spotifyobj.durationMs:
                seekthread.end=False
            else:
                seekthread.end=True


            while seekthread.end==False and seekthread.nothingplaying==False:                            ###while song is still playing. This could be while true with seekthread.end as an interrupt

                if saved:
                    with canvas(device) as draw:
                        w, h = draw.textsize("Saved", font)
                        draw.text(((Width / 2) - (w / 2), (Height / 2) - (h / 2)), "Saved", font=ImageFont.truetype(font_path, 22), fill="white")
                    time.sleep(1)
                    saved = False

                with canvas(device) as draw:


                    songscrollthread.drawobj()
                    artistscrollthread.drawobj()
                    seekthread.drawobj()

                if(datetime.now()>justdrawtime):

                    if(songscrollthread.scrolling==False):      ###potentitally should check if both are not scrolling
                        #print("checking song")
                        spotifyobj.reload()
                        seekthread.currentpos=spotifyobj.progressMs/1000
                        seekthread.isplaying=spotifyobj.isPlaying
                        seekthread.nothingplaying = spotifyobj.nothingplaying
                        justdrawtime = datetime.now() + timedelta(seconds=networktimeout)

                        if(spotifyobj.track+spotifyobj.artists[0]["name"]!=lastsong):
                            break
                        else:
                            artistscrollthread.end = False


                    else:
                        #print("songscroll.end",songscrollthread.end,"songscroll.x",songscrollthread.x,"move",songscrollthread.move)
                        if(artistscrollthread.end):
                            artistscrollthread.end=False
                        if(songscrollthread.end):           ###potentially should check if both scrolls are at 0 but
                            #print("scroll ended, checking song")
                            spotifyobj.reload()
                            seekthread.currentpos = spotifyobj.progressMs / 1000
                            seekthread.isplaying = spotifyobj.isPlaying
                            seekthread.nothingplaying=spotifyobj.nothingplaying
                            if (spotifyobj.track + spotifyobj.artists[0]["name"] != lastsong):
                                #print("diff song")
                                break
                            else:
                                #songscrollthread.x=0
                                songscrollthread.end=False
                                artistscrollthread.end = False
                                justdrawtime = datetime.now() + timedelta(seconds=networktimeout)
                else:
                    pass
                    #print("only drawing")

            spotifyobj.reload()


    except KeyboardInterrupt:
        pass
