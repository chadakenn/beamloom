#!/bin/bash -e
usermod -aG video,render,input beamloom
systemctl enable avahi-daemon beamloom-wifi.service beamloom-player.service beamloom-kiosk.service
