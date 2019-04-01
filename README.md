# Spotify-OLED
Spotify now playing on an OLED screen


# Part List
1. raspberry pi (or similar) (with Wifi)
2. I2C or SPI OLED display

# Steps
1. connect OLED and configure rpi settings to enable it
2. install 
  - python3 `sudo apt-get install python3`
  - pip3 `sudo apt-get install python3-pip`
  - git `sudo apt-get install git`
  - libopenjp2-7 `sudo apt-get install libopenjp2-7-dev`
3. using pip3 install the following python libraries
  - Pillow `pip3 install pillow`
  - luma.oled `pip3 install luma-oled`
4. install python library for spotify using `pip3 install git+https://github.com/plamere/spotipy.git --upgrade`
5. create a spotify api app by logging in to https://developer.spotify.com/dashboard/applications with your spotify account
6. replace details in Spotify-OLED.py with app credentials from spotify and modify screen variables to suit resolution etc.
7. spotify-oled.py to crontab to start at boot or run using `nohup python3 Spotify-OLED &`

