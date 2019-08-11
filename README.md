# chaanbot

A python 3 [matrix](https://matrix.org) bot using [matrix-python-sdk](https://github.com/matrix-org/matrix-python-sdk).

Bot is under active development and severe breaking changes should be expected until a stable release is created.

#Install instructions
Install dependencies:
```
sudo apt-get install python3-pip python3-dev nginx
sudo pip3 install virtualenv
```

Add user for bot. Not required but recommended.
```
sudo adduser --disabled-password chaanbot
sudo su chaanbot
```

Create virtual environment and install bot:
```
python3 -m venv chaanbot
source chaanbot/bin/activate
cd chaanbot
python3 -m pip install --no-cache-dir --index-url https://test.pypi.org/simple/ --no-deps chaanbot
```

Start bot to initialize config file creation, then edit the config file to your liking.
Output of running the bot will show where the config file is located.
```
chaanbot
nano .config/chaanbot/chaanbot.cfg
```

Bot should now be runnable as chaanbot user:
```
chaanbot
```

For convenience bot can be added as service.
With sudo access, copy chaanbot.service file to /etc/systemd/system/chaanbot.service:
```
sudo nano /etc/systemd/system/chaanbot.service
```
Bot is now startable from systemctl:

```
sudo systemctl start chaanbot
```

And can be set to run on boot:
```
sudo systemctl enable chaanbot
```

# Upgrading version
```
sudo su chaanbot
source /home/chaanbot/chaanbot/bin/activate
python3 -m pip install -U --index-url https://test.pypi.org/simple/ --no-deps chaanbot
```