"""Python client for Ziggo Next."""
import json
from logging import Logger
import random
import time

import paho.mqtt.client as mqtt
from paho.mqtt.client import Client
import requests
from .models import ZiggoNextSession, ZiggoNextBoxState, ZiggoChannel, ZiggoNextBox
from .exceptions import ZiggoNextConnectionError, ZiggoNextError

from .const import (
    BOX_PLAY_STATE_BUFFER,
    BOX_PLAY_STATE_CHANNEL,
    BOX_PLAY_STATE_DVR,
    BOX_PLAY_STATE_REPLAY,
    ONLINE_RUNNING,
    ONLINE_STANDBY,
    UNKNOWN,
    MEDIA_KEY_PLAY_PAUSE,
    MEDIA_KEY_CHANNEL_DOWN,
    MEDIA_KEY_CHANNEL_UP,
    MEDIA_KEY_POWER
)
API_BASE_URL = "https://web-api-prod-obo.horizon.tv/oesp/v3/NL/nld/web"
API_URL_SESSION = API_BASE_URL + "/session"
API_URL_TOKEN = API_BASE_URL + "/tokens/jwt"
API_URL_LISTING_FORMAT = API_BASE_URL + "/listings/?byStationId={stationId}&byScCridImi={id}"
API_URL_RECORDING_FORMAT = API_BASE_URL + "/listings/?byScCridImi={id}"
API_URL_CHANNELS = API_BASE_URL + "/channels"
API_URL_SETTOP_BOXES = API_BASE_URL + "/settopboxes/profile"
DEFAULT_HOST = "obomsg.prod.nl.horizon.tv"
DEFAULT_PORT = 443


def _makeId(stringLength=10):
    letters = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choice(letters) for i in range(stringLength))


class ZiggoNext:
    """Main class for handling connections with Ziggo Next Settop boxes."""
    mqttClient: Client
    logger: Logger

    def __init__(self, username: str, password: str) -> None:
        """Initialize connection with Ziggo Next"""
        self.username = username
        self.password = password
        self.token = None
        self.session = None
        self.mqttClient = None
        self.mqttClientId = None
        self.logger = None
        self.mqttClientConnected = False
        self.settopBoxes = {}
        self.channels = {}


    def get_session(self):
        """Get Ziggo Next Session information"""
        payload = {"username": self.username, "password": self.password}
        response = requests.post(API_URL_SESSION, json=payload)
        if response.status_code == 200:
            session = response.json()
            return ZiggoNextSession(
                session["customer"]["householdId"], session["oespToken"]
            )
        else:
            raise ZiggoNextConnectionError("Oops")

    def get_session_and_token(self):
        """Get session and token from Ziggo Next"""
        session = self.get_session()
        self.token = self._get_token(session)
        self.session = session

    def _register_settop_boxes(self, session):
        """Get settopxes"""
        jsonResult = self._do_api_call(session, API_URL_SETTOP_BOXES)
        for box in jsonResult["boxes"]:
            if not box["boxType"] == "EOS":
                continue
            boxId = box["physicalDeviceId"]
            self.settopBoxes[boxId] = ZiggoNextBox(boxId, box["customerDefinedName"], ZiggoNextBoxState(boxId, UNKNOWN))
            



    def _do_api_call(self, session, url):
        """Executes api call and returns json object"""
        headers = {
            "X-OESP-Token": session.oespToken,
            "X-OESP-Username": self.username,
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise ZiggoNextError("API call failed: " + str(response.status_code))
    
    def _get_token(self, session):
        """Get token from Ziggo Next"""
        jsonResult = self._do_api_call(session, API_URL_TOKEN)
        return jsonResult["token"]
        
    def initialize(self, logger, enableMqttLogging: bool = True):
        """Get token and start mqtt client for receiving data from Ziggo Next"""
        self.logger = logger
        self.logger.debug("Obtaining token...")
        self.get_session_and_token()
        self._register_settop_boxes(self.session)
        self.load_channels(False)
        self.mqttClientId = _makeId(30)
        self.mqttClient = mqtt.Client(self.mqttClientId, transport="websockets")
        self.mqttClient.username_pw_set(self.session.houseHoldId, self.token)
        self.mqttClient.tls_set()
        if enableMqttLogging:
            self.mqttClient.enable_logger(logger)
        self.mqttClient.on_connect = self._on_mqtt_client_connect
        self.mqttClient.on_disconnect = self._on_mqtt_client_disconnect
        self.mqttClient.connect(DEFAULT_HOST, DEFAULT_PORT)
        self.mqttClient.loop_start()

    def _on_mqtt_client_connect(self, client, userdata, flags, resultCode):
        """Handling mqtt connect result"""
        if resultCode == 0:
            client.on_message = self._on_mqtt_client_message
            self.logger.debug("Connected to mqtt client.")
            self.mqttClientConnected = True
            self._do_subscribe("$SYS") # Does this work?
            self._do_subscribe(self.session.houseHoldId) # Shouldn't be needed because of the below
            self._do_subscribe(self.session.houseHoldId + "/#")
            self._do_subscribe(self.session.houseHoldId + "/$SYS") # Shouldn't be needed because of the above
            self._do_subscribe(self.session.houseHoldId + "/+/#") # Shouldn't be needed because of the above
            self._do_subscribe(self.session.houseHoldId + "/+/status") # Shouldn't be needed because of the above
            self._do_subscribe(self.session.houseHoldId + "/" + self.mqttClientId) # Shouldn't be needed because of the above
            for box in self.settopBoxes.values():
                baseTopic = self.session.houseHoldId + "/" + box.boxId
                self._do_subscribe(baseTopic)
                self._do_subscribe(baseTopic + "/#")
                self._do_subscribe(baseTopic + "/$SYS")    
                self._do_subscribe(baseTopic + "/status")       
                self._request_settop_box_state(box.boxId)

        elif resultCode == 5:
            self.logger.debug("Not authorized mqtt client. Retry to connect")
            self.get_session_and_token()
            client.username_pw_set(self.session.houseHoldId, self.token)
            client.connect(DEFAULT_HOST, DEFAULT_PORT)
            client.loop_start()
        else:
            raise ZiggoNextError("Could not connect to Mqtt server")

    def _on_mqtt_client_disconnect(self, client, userdata, resultCode):
        """Set state to diconnect"""
        self.logger.debug("Disconnected from mqtt client.")
        self.mqttClientConnected = False

    def _on_mqtt_client_message(self, client, userdata, message):
        """Handles messages received by mqtt client"""
        jsonPayload = json.loads(message.payload)
        self.logger.debug(jsonPayload)
        if "deviceType" in jsonPayload and jsonPayload["deviceType"] == "STB":
            self._update_settopbox_state(jsonPayload)
        if "status" in jsonPayload:
            self._update_settop_box(jsonPayload)

    def _update_settopbox_state(self, payload):
        """Registers a new settop box"""
        deviceId = payload["source"]
        state = payload["state"]
        self.settopBoxes[deviceId].state.state = state
        if state == ONLINE_RUNNING:            
            self._request_settop_box_state(deviceId)
        else:
            self.settopBoxes[deviceId].reset(state)

    def _do_subscribe(self, topic):
        """Subscribes to mqtt topic"""
        self.mqttClient.subscribe(topic)
        self.logger.debug("sub to topic: {topic}".format(topic=topic))

    def remove_device(self, deviceId):
        """Unregister Ziggo Next mediabox"""
        if deviceId in self.settopBoxes.keys():
            self.logger.debug("Removing device {deviceId}".format(deviceId=deviceId))
            del self.settopBoxes[deviceId]
            self.mqttClient.unsubscribe(self.session.houseHoldId + "/" + deviceId)
            self.mqttClient.unsubscribe(
                self.session.houseHoldId + "/" + deviceId + "/status"
            )

    def _request_settop_box_state(self, deviceId):
        """Sends mqtt message to receive state from settop box"""
        topic = self.session.houseHoldId + "/" + deviceId
        payload = {
            "id": _makeId(8),
            "type": "CPE.getUiStatus",
            "source": self.mqttClientId,
        }
        self.mqttClient.publish(topic, json.dumps(payload))

    def _update_settop_box(self, payload):
        """Updates settopbox state"""
        try:
            deviceId = payload["source"]
            statusPayload = payload["status"]
            playerState = statusPayload["playerState"]
            sourceType = playerState["sourceType"]
            stateSource = playerState["source"]
            speed = playerState["speed"]
            if sourceType == BOX_PLAY_STATE_REPLAY:
                self.settopBoxes[deviceId].state.setSourceType(BOX_PLAY_STATE_REPLAY)
                eventId = stateSource["eventId"]
                self.settopBoxes[deviceId].state.setChannel(None)
                self.settopBoxes[deviceId].state.setChannelTitle(None)
                self.settopBoxes[deviceId].state.setTitle(
                    "ReplayTV: " + self._get_recording_title(eventId)
                )
                self.settopBoxes[deviceId].state.setImage(self._get_recording_image(eventId))
                self.settopBoxes[deviceId].state.setPaused(speed == 0)
            elif sourceType == BOX_PLAY_STATE_DVR:
                self.settopBoxes[deviceId].state.setSourceType(BOX_PLAY_STATE_DVR)
                recordingId = stateSource["recordingId"]
                self.settopBoxes[deviceId].state.setChannel(None)
                self.settopBoxes[deviceId].state.setChannelTitle(None)
                self.settopBoxes[deviceId].state.setTitle(
                    "Recording: " + self._get_recording_title(recordingId)
                )
                self.settopBoxes[deviceId].state.setImage(
                    self._get_recording_image(recordingId)
                )
                self.settopBoxes[deviceId].state.setPaused(speed == 0)
            elif sourceType == BOX_PLAY_STATE_BUFFER:
                self.settopBoxes[deviceId].state.setSourceType(BOX_PLAY_STATE_BUFFER)
                channelId = stateSource["channelId"]
                channel = self.channels[channelId]
                eventId = stateSource["eventId"]
                self.settopBoxes[deviceId].state.setChannel(channelId)
                self.settopBoxes[deviceId].state.setChannelTitle(None)
                self.settopBoxes[deviceId].state.setTitle(
                    "Uitgesteld: " + self._get_recording_title(eventId)
                )
                self.settopBoxes[deviceId].state.setImage(channel.streamImage)
                self.settopBoxes[deviceId].state.setPaused(speed == 0)
            elif playerState["sourceType"] == BOX_PLAY_STATE_CHANNEL:
                self.settopBoxes[deviceId].state.setSourceType(BOX_PLAY_STATE_CHANNEL)
                channelId = stateSource["channelId"]
                eventId = stateSource["eventId"]
                channel = self.channels[channelId]
                self.settopBoxes[deviceId].state.setChannel(channelId)
                self.settopBoxes[deviceId].state.setChannelTitle(channel.title)
                self.settopBoxes[deviceId].state.setTitle(
                    self._get_channel_title(channelId, eventId)
                )
                self.settopBoxes[deviceId].state.setImage(channel.streamImage)
                self.settopBoxes[deviceId].state.setPaused(False)
            else:
                self.settopBoxes[deviceId].state.setSourceType(BOX_PLAY_STATE_CHANNEL)
                eventId = stateSource["eventId"]
                self.settopBoxes[deviceId].state.setChannel(None)
                self.settopBoxes[deviceId].state.setTitle("Playing something...")
                self.settopBoxes[deviceId].state.setImage(None)
                self.settopBoxes[deviceId].state.setPaused(speed == 0)
        except Exception as error:
            self.logger.error(error)
    

    def get_settop_box_state(self, boxId: str):
        """Retuns the state from given settop box"""
        return self.settopBoxes[boxId].state.state

    def _send_key_to_box(self, boxId: str, key: str):
        """Sends emulated (remote) key press to settopbox"""
        payload = (
            '{"type":"CPE.KeyEvent","status":{"w3cKey":"'
            + key
            + '","eventType":"keyDownUp"}}'
        )
        self.mqttClient.publish(self.session.houseHoldId + "/" + boxId, payload)
        time.sleep(1)
        self._request_settop_box_state(boxId)

    def select_source(self, source, boxId):
        """Changes te channel from the settopbox"""
        channel = [src for src in self.channels.values() if src.title == source][0]
        payload = (
            '{"id":"'
            + _makeId(8)
            + '","type":"CPE.pushToTV","source":{"clientId":"'
            + self.mqttClientId
            + '","friendlyDeviceName":"Home Assistant"},"status":{"sourceType":"linear","source":{"channelId":"'
            + channel.serviceId
            + '"},"relativePosition":0,"speed":1}}'
        )

        self.mqttClient.publish(self.session.houseHoldId + "/" + boxId, payload)
        self._request_settop_box_state(boxId)

    def pause(self, boxId):
        """Pauses the given settopbox"""
        boxState = self.settopBoxes[boxId].state
        if boxState.state == ONLINE_RUNNING and not boxState.paused:
            self._send_key_to_box(boxId, MEDIA_KEY_PLAY_PAUSE)

    def play(self, boxId):
        """Resumes the settopbox"""
        boxState = self.settopBoxes[boxId].state
        if boxState.state == ONLINE_RUNNING and boxState.paused:
            self._send_key_to_box(boxId, MEDIA_KEY_PLAY_PAUSE)

    def next_channel(self, boxId):
        """Select the next channel for given settop box."""
        boxState = self.settopBoxes[boxId].state
        if boxState.state == ONLINE_RUNNING:
            self._send_key_to_box(boxId, MEDIA_KEY_CHANNEL_UP)

    def previous_channel(self, boxId):
        """Select the previous channel for given settop box."""
        boxState = self.settopBoxes[boxId].state
        if boxState.state == ONLINE_RUNNING:
            self._send_key_to_box(boxId, MEDIA_KEY_CHANNEL_DOWN)

    def turn_on(self, boxId):
        """Turn the settop box on."""
        boxState = self.settopBoxes[boxId].state
        if boxState.state == ONLINE_STANDBY:
            self._send_key_to_box(boxId, MEDIA_KEY_POWER)

    def turn_off(self, boxId):
        """Turn the settop box off."""
        boxState = self.settopBoxes[boxId].state
        if boxState.state == ONLINE_RUNNING:
           self._send_key_to_box(boxId, MEDIA_KEY_POWER)

    def is_available(self, boxId):
        boxState = self.settopBoxes[boxId].state
        state = boxState.state
        return (state == ONLINE_RUNNING or state == ONLINE_STANDBY)

    def _get_recording_title(self, scCridImi):
        """Get recording title."""
        response = requests.get(API_URL_RECORDING_FORMAT.format(id=scCridImi))
        if response.status_code == 200:
            content = response.json()
            return content["listings"][0]["program"]["title"]
        return None

    def _get_recording_image(self, scCridImi):
        """Get recording image."""
        response = requests.get(API_URL_RECORDING_FORMAT.format(id=scCridImi))
        if response.status_code == 200:
            content = response.json()
            return content["listings"][0]["program"]["images"][0]["url"]
        return None

    def _get_channel_title(self, channelId, scCridImi):
        """Get channel title"""
        response = requests.get(
            API_URL_LISTING_FORMAT.format(stationId=channelId, id=scCridImi)
        )
        if response.status_code == 200:
            content = response.json()
            return content["listings"][0]["program"]["title"]
        return None

    def load_channels(self, updateState: bool = True):
        """Refresh channels list for now-playing data."""
        self.logger.debug("Updating channels...")
        response = requests.get(API_URL_CHANNELS)
        if response.status_code == 200:
            content = response.json()

            for channel in content["channels"]:
                station = channel["stationSchedules"][0]["station"]
                serviceId = station["serviceId"]
                self.channels[serviceId] = ZiggoChannel(
                    serviceId,
                    channel["title"],
                    station["images"][0]["url"],
                    station["images"][2]["url"],
                    channel["channelNumber"],
                )
            self.logger.debug("Updating channels complete...")
            if updateState:
                self.logger.debug("Updating boxes with new channel info...")
                for deviceId in self.settopBoxes.keys():
                    box = self.settopBoxes[deviceId].state
                    channelId = box.channelId
                    if channelId is not None:
                        box.setImage(self.channels[channelId].streamImage)
        else:
            self.logger.error("Can't retrieve channels...")

    def disconnect(self):
        """Disconnect from mqtt."""
        self.mqttClient.disconnect()