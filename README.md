# chaanbot

A python 3 [matrix](https://matrix.org) bot using [matrix-python-sdk](https://github.com/matrix-org/matrix-python-sdk).
The bot is extensible and currently provides:

* Highlight module allows users to easily notify groups of users. E.g. "!hl javadevs spring-boot vs micronaut?" would
  highlight/notify any user in the javadevs group.
* Weather module allows users to broadcast weather reports.
* More to come!

Bot is under active development and severe breaking changes should be expected until a stable release is created.

# Install instructions

Chaanbot requires Python 3.

Add user for bot. Not required but recommended:

```
sudo adduser --disabled-password chaanbot
sudo su chaanbot
```

Create virtual environment and install bot and its dependencies:

```
python3 -m venv chaanbot
source chaanbot/bin/activate
python3 -m pip install chaanbot
```

Start bot to initialize config file creation, then edit the config file to your liking. Config file location is the
user's config directory as determined by appdirs, typical locations are:

        Mac OS X:  ~/Library/Application Support/chaanbot/chaanbot.cfg
        Unix:      ~/.config/chaanbot/chaanbot.cfg or in $XDG_CONFIG_HOME, if defined
        Win *:     C:\Users\<username>\AppData\[local or roaming]\chaanbot\chaanbot\chaanbot.cfg

Output of running the bot will also show where the config file is located:

```
chaanbot
nano .config/chaanbot/chaanbot.cfg
```

Bot should now be runnable as chaanbot user:

```
chaanbot
```

For convenience bot can be added as service. With sudo access, copy chaanbot.service file to
/etc/systemd/system/chaanbot.service:

```
sudo nano /etc/systemd/system/chaanbot.service
```

Bot is now startable from systemctl:

```
sudo service chaanbot start
```

And can be set to run on boot:

```
sudo systemctl enable chaanbot
```

# Upgrading version

## Upgrading from 1.x to 2.0

In 2.0 acces token login is (hopefully temporarily) disabled, use password login instead. See chaanbot.cfg.sample for
how to set password.

## Commands

```
sudo su chaanbot
source /home/chaanbot/chaanbot/bin/activate
python3 -m pip install -U chaanbot
```

# TODO

## Core

* Improve error handling
* Integration tests and better test coverage
* Improve installation documentation for non-Ubuntu installations

## Modules

* Make weather coordinates not room-dependent
