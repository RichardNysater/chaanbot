import logging
import re
from typing import Optional

from chaanbot import command_utility

logger = logging.getLogger("weather")


class DarkskyWeather:
    max_days_to_send_at_once = 5
    darksky_api_url = 'https://api.darksky.net'
    config = {
        "always_run": False,
        "operations": {
            "weather": {
                "commands": ["!weather"],
                "argument_regex": "[\\d( \\d)*]?"
            },
            "add_weather_coordinates": {
                "commands": ["!addcoordinates", "!addcoords", "!setcoordinates", "!setcoords"],
                "argument_regex": "\\d{1,2}\\.?\\d+[,\\s]\\d{1,2}\\.?\\d"
                # Lat&Long are 2 digits followed by decimals
            }
        },
    }

    def __init__(self, config, matrix, database, requests):
        self.matrix = matrix
        self.requests = requests
        api_key = config.get("darksky_weather", "api_key", fallback=None)
        if api_key:
            self.config["api_key"] = api_key
        else:
            self.disabled = True
            logger.info("No API key provided for darksky weather, module disabled")

        if database:
            self.database = database
            logger.debug("Initializing highlight database if needed")
            conn = database.connect()
            conn.execute('''CREATE TABLE IF NOT EXISTS user_coordinates
            (ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            ROOM_ID TEXT NOT NULL,
            USER_ID TEXT NOT NULL,
            LATITUDE TEXT NOT NULL,
            LONGITUDE TEXT NOT NULL,
            UNIQUE(ROOM_ID, USER_ID));    
            ''')
            conn.commit()
        else:
            self.disabled = True
            logger.info("No database provided, darksky weather module disabled")

    def run(self, room, event, message) -> bool:
        if self.should_run(message):
            logger.debug("Should run darksky weather, checking next command")
            if command_utility.matches(self.config["operations"]["weather"], message):
                logger.debug("Showing weather")
                self._send_weather(room, event["sender"], message)
            elif command_utility.matches(self.config["operations"]["add_weather_coordinates"], message):
                logger.debug("Adding coordinates")
                self._add_coordinates(room, event["sender"], message)
            else:
                raise RuntimeError("Could not find command to run on message, but should have been able to")
            return True
        return False

    def should_run(self, message) -> bool:
        return not hasattr(self, "disabled") and command_utility.matches(self.config["operations"], message)

    def _send_weather(self, room, user_id, message):
        latitude, longitude = self._get_coordinates(room, user_id)
        if not latitude or not longitude:
            room.send_text("Set your coordinates by using !setcoordinates [LATITUDE] [LONGITUDE].")
            return

        argument = command_utility.get_argument(message)

        if argument:
            days = argument.strip().split(" ")
            self._send_several_days_weather(room, latitude, longitude, days)
            return
        else:
            self._send_todays_weather(room, latitude, longitude)
            return

    def _send_several_days_weather(self, room, latitude, longitude, days):
        if len(days) > self.max_days_to_send_at_once:
            room.send_text("Can only look up {} days at once.".format(self.max_days_to_send_at_once))
            return

        url = "{}/forecast/{}/{},{}?units=si&exclude=currently,minutely,hourly,alerts,flags" \
            .format(self.darksky_api_url, self.config["api_key"], latitude, longitude)

        contents = self.requests.get(url).json()
        message_for_one_day = "{}: Min: {}, Max: {}. {}\n"
        message = ""
        for days_from_today in days:
            day = "Today" if days_from_today == "0" else "Tomorrow" if days_from_today == "1" else "{} days from now" \
                .format(days_from_today)
            min_temp = contents["daily"]["data"][int(days_from_today)]["temperatureLow"]
            max_temp = contents["daily"]["data"][int(days_from_today)]["temperatureHigh"]
            summary = contents["daily"]["data"][int(days_from_today)]["summary"]
            message += message_for_one_day.format(day, min_temp, max_temp, summary)

        room.send_text(message)

    def _send_todays_weather(self, room, latitude, longitude):
        url = "{}/forecast/{}/{},{}?units=si&exclude=minutely,hourly,alerts,flags" \
            .format(self.darksky_api_url, self.config["api_key"], latitude, longitude)

        contents = self.requests.get(url).json()
        current_temp = str(contents["currently"]["temperature"])
        min_temp = str(contents["daily"]["data"][0]["temperatureLow"])
        max_temp = str(contents["daily"]["data"][0]["temperatureHigh"])
        summary = contents["currently"]["summary"]

        message = "Currently: {} (Min: {}, Max: {}). {}" \
            .format(current_temp, min_temp, max_temp, summary)
        room.send_text(message)

    def _add_coordinates(self, room, user_id, message):
        argument = command_utility.get_argument(message).strip()

        split_argument = re.split(';|,|\\s', argument, 1)
        latitude = split_argument[0].strip()
        longitude = split_argument[1].strip()
        conn = self.database.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_coordinates(ROOM_ID, USER_ID, LATITUDE, LONGITUDE) "
            "VALUES(?,?,?,?)",
            (room.room_id, user_id, latitude, longitude))
        conn.commit()
        logger.debug(
            "Inserted Lat {} Long {} for user_id {} and room {} with id {}".format(latitude, longitude, user_id,
                                                                                   room.room_id, cursor.lastrowid))
        room.send_text("Coordinates set to {},{}.".format(latitude, longitude))

    def _get_coordinates(self, room, user_id) -> (Optional[str], Optional[str]):
        conn = self.database.connect()
        result = conn.execute(
            "SELECT LATITUDE,LONGITUDE FROM user_coordinates WHERE ROOM_ID = ? AND USER_ID = ?",
            (room.room_id, user_id))
        conn.commit()
        result = result.fetchone()
        return (result[0], result[1]) if result else (None, None)
