# gdoormon

Shuts the garage door if it's left open for too long, or when it's open and
nobody is home. 

Determines who's home by polling an Airport for wireless clients. Wireless
clients need to register their MAC address via the webserver started on port
8080.

Determines if the door is open using an Arduino with an HC-SR04 rangefinder and
ethernet shield. See ```doorsensor/arduino_sensor_server/``` for more details.

Before it shuts the door, it alerts subscribers via XMPP that the door
will be shutting; the alert and door closure can be snoozed via XMPP.

Shuts the door using an Pololu Micro Maestro server controller to drive a
servo to hit a button (e.g. garage door remote button).

Tested on Raspian 7 (wheezy) and Ubuntu 12.04 (precise).

## Hardware Deps

You'll need:
  - A garage door and remote or button you can push.
  - An 802.11n Airport Extreme with SNMP enabled.
  - An Arduino with an Ethernet shield, HC-SR04 rangefinder and 3 LEDs
  - A Pololu Micro Maestro connected to a servo that can press the garage door button.


### Enable SNMP on the Airport

SNMP is used to get connected wireless clients from the Airport. 
**Newer 802.11ac Airports do not support SNMP.**

SNMP is enabled by default on older Airports, but you might have some work to
do if it's not (e.g. you may need to get an older version of the Airport
configuration tool).

Adding support for dd-wrt routers is planned.

### Setup the Arduino

Needs an HC-SR04 ultrasonic rangefinder, 3 LEDs (with resistors), and an
ethernet shield. See the sketch in ```doorsensor/arduino_sensor_server/arduino_sensor_server.ino```
for more info.

Mount the Arduino where the rangefinder can tell if the door is open or not.
You can adjust the threshold in the config file. The HC-SR04 is accurate to
about 30cm.


### Setup the Maestro

#### Enable "USB Dual Port" on the Maestro

The Pololu Maestro Control Center can set this.

#### Strap the servo to a garage door remote

You may need to tweak the servo angles defined in ```doorcontrol/maestro.py```
Using a relay wired to a door controller is planned, but a servo was more fun.

## Software Deps

### Get the source.

    git clone

### Install debian binary deps

    sudo apt-get install build-essential python-dev
    sudo apt-get install python-virtualenv
    sudo apt-get install libsnmp-python

### Setup virtualenv and install python modules

Note: you'll need to use Python 2. If Python 3 is your default python
interpreter (```python --version```), pass ```--python=python2``` to
virtualenv.

```sh
cd gdoormon  # or whichever dir this README file lives
virtualenv --system-site-packages deps
source deps/bin/activate
pip install -r requirements.txt
```

*Or* use apt if you don't want to use virtualenv:

    sudo apt-get install python-openssl  # for xmpp
    sudo apt-get install wokkel          # for xmpp; also installs twisted
    sudo apt-get install python-mox      # for tests

### Setup an XMPP account

You can't use your own account because you can't send messages to yourself
(AFAIK).

### Edit the config

Edit example.confg and update values as appropriate, save it as
"gdoormon.config". 


## Testing

run these after install deps to verify everything is working:

```sh
# Verify code compiles, deps are satisifed, etc.
./unittest.sh
# Verify airport connectivity.
deps/bin/twistd -ny testing/presence_regtest.py 
# Verify the servo controller works:
deps/bin/twistd -ny testing/maestro_regtest.py
# Verify xmpp works
XMPP_USER=foo@example.org XMPP_PASSWD=hunter2 deps/bin/twistd -ny testing/xmpp_regtest.py
```

## Running the server

Start the server as a daemon with:

    gdoormonctl.sh start

Logs will be written to ```gdoormon.log```

For testing, run ```deps/bin/twistd -ny main.py```

### Subscribe to XMPP notifications

Message the xmpp bot the word "subscribe".

### Register wireless clients

Connect to the web server on port 8080 using your phone's web browser and
register your phone's MAC address.

### Controlling the server

    gdoormonctl.sh start
    gdoormonctl.sh status
    gdoormonctl.sh stop

### Starting on boot

If you want to start it on boot, edit /etc/rc.local to call
```gdoormonctl.sh start```

If your distro uses systemd, copy ```gdoormon.service``` to /etc/systemd/system


## Code layout

  - ```chatcontrol/```
    - modules for communication
  - ```doorcontrol/```
    - modules for controlling the door
    - arduino sketch
  - ```doorsensor/```
    - modules for detecting if the door is open
  - ```presence/```
    - modules for detecting if someone is home
  - ```state/```
    - state machine logic
  - ```testing/```
    - regression tests


## TODO

  - [x] reformat this file using github markdown
  - [ ] use unnamed virtualenv
  - [ ] get more things via xmpp:
    - [ ] current state
    - [ ] help
  - [ ] after an alert, warn that the timeout is approaching
  - [ ] add chat subscriptions to:
    - [ ] when registered clients connect/disconnect
    - [ ] when nobody/somebody is home
    - [ ] when the door changes state
  - [ ] add a "manual-only" mode that requires a human to hit the button
  - [ ] pylint
  - [ ] broadcast who comes home and last person who left
    - [ ] register user name when registering (default to "user1", "user2", etc.)
  - [ ] support rpi gpio
  - [ ] support dd-wrt
  - [ ] drop pololu+servo, use a wired relay
  - [ ] support irc

vim: set ft=markdown
