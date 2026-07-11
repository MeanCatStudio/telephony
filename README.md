# Linux Telephony

Welcome to Waylon's Telephony program

This is an application ment to recreate your typical phone's call and messaging app.
The program uses freekdesktop's modemManager and works with any linux machine with a modem attached.

## Getting Started

The program is made of a centeral deamon with apps that communicate with said deamon.
Pls set up a new session daemon with the telephony.service under systemConfigs.

Afterwards, move the two .desktop files into your applications foulder (/usr/share/applications).
This should add two new apps under your apps menu

Have a great time calling you're friends!