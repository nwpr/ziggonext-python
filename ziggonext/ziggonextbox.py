"""ZiggoNextBox"""
import paho.mqtt.client as mqtt
from paho.mqtt.client import Client
import json
import requests
from logging import Logger
import random
import time
import sys, traceback
from .models import ZiggoNextSession, ZiggoNextBoxPlayingInfo, ZiggoChannel
from .const import (
    BOX_PLAY_STATE_BUFFER,
    BOX_PLAY_STATE_CHANNEL,
    BOX_PLAY_STATE_DVR,
    BOX_PLAY_STATE_REPLAY,
    BOX_PLAY_STATE_APP,
    ONLINE_RUNNING,
    ONLINE_STANDBY,
    UNKNOWN,
    MEDIA_KEY_PLAY_PAUSE,
    MEDIA_KEY_CHANNEL_DOWN,
    MEDIA_KEY_CHANNEL_UP,
    MEDIA_KEY_POWER,
    COUNTRY_URLS_HTTP,
    COUNTRY_URLS_MQTT
)
DEFAULT_PORT = 443

def _makeId(stringLength=10):
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choice(letters) for i in range(stringLength))

class ZiggoNextBox:
    
    box_id: str
    name: str
    state: str = UNKNOWN
    info: ZiggoNextBoxPlayingInfo
    available: bool = False
    channels: ZiggoChannel = {}

    def __init__(self, box_id:str, name:str, householdId:str, token:str, country_code:str, logger:Logger):
        self.box_id = box_id
        self.name = name
        self._householdId = householdId
        self._token = token
        self.info = ZiggoNextBoxPlayingInfo()
        self.logger = logger
        self._mqttClientConnected = False
        self._createUrls(country_code)
        self.mqttClientId = _makeId(30)
        self.mqttClient = mqtt.Client(self.mqttClientId, transport="websockets")
        self.mqttClient.username_pw_set(householdId, token)
        self.mqttClient.tls_set()
        self.mqttClient.on_connect = self._on_mqtt_client_connect
        self.mqttClient.on_disconnect = self._on_mqtt_client_disconnect
        self.mqttClient.connect(self._mqtt_broker, DEFAULT_PORT)
        self.mqttClient.loop_start()
        self.channels = {}
        

    def _createUrls(self, country_code: str):
        baseUrl = COUNTRY_URLS_HTTP[country_code]
        self._api_url_listing_format =  baseUrl + "/listings/?byStationId={stationId}&byScCridImi={id}"
        self._api_url_recording_format =  baseUrl + "/listings/?byScCridImi={id}"
        self._mqtt_broker = COUNTRY_URLS_MQTT[country_code]
    
    def _on_mqtt_client_connect(self, client, userdata, flags, resultCode):
        """Handling mqtt connect result"""
        if resultCode == 0:
            client.on_message = self._on_mqtt_client_message
            self.logger.debug("Connected to mqtt client.")
            self.mqttClientConnected = True
            payload = {
                "source": self.mqttClientId,
                "state": "ONLINE_RUNNING",
                "deviceType": "HGO",
            }
            topic = self._householdId + "/" + self.mqttClientId + "/status"
            self.mqttClient.publish(topic, json.dumps(payload))
            self._do_subscribe(self._householdId)
            self._do_subscribe(self._householdId + "/+/status")

        elif resultCode == 5:
            self.logger.debug("Not authorized mqtt client. Retry to connect")
            client.username_pw_set(self._householdId, self._token)
            client.connect(self._mqtt_broker, DEFAULT_PORT)
            client.loop_start()
        else:
            raise Exception("Could not connect to Mqtt server")
    
    def _on_mqtt_client_disconnect(self, client, userdata, resultCode):
        """Set state to diconnect"""
        self.logger.debug("Disconnected from mqtt client: " + resultCode)
        self.mqttClientConnected = False

    def _on_mqtt_client_message(self, client, userdata, message):
        """Handles messages received by mqtt client"""
        jsonPayload = json.loads(message.payload)
        self.logger.debug(jsonPayload)
        if "deviceType" in jsonPayload and jsonPayload["deviceType"] == "STB":
            self._update_settopbox_state(jsonPayload)
        if "status" in jsonPayload:
            self._update_settop_box(jsonPayload)
    
    def _do_subscribe(self, topic):
        """Subscribes to mqtt topic"""
        self.mqttClient.subscribe(topic)
        self.logger.debug("subscribed to topic: {topic}".format(topic=topic))
    
    def _update_settopbox_state(self, payload):
        """Registers a new settop box"""
        deviceId = payload["source"]
        if deviceId != self.box_id:
            return
        state = payload["state"]
        
        if self.state == UNKNOWN:
            self._request_settop_box_state() 
            self._do_subscribe(self._householdId + "/" + self.mqttClientId)
            baseTopic = self._householdId + "/" + self.box_id
            self._do_subscribe(baseTopic)
            self._do_subscribe(baseTopic + "/status")
        if state == ONLINE_STANDBY :
            self.info = ZiggoNextBoxPlayingInfo()
        else:
            self._request_settop_box_state()
        self.state = state
        
    
    def _request_settop_box_state(self):
        """Sends mqtt message to receive state from settop box"""
        self.logger.debug("Request box state for box " + self.name)
        topic = self._householdId + "/" + self.box_id
        payload = {
            "id": _makeId(8),
            "type": "CPE.getUiStatus",
            "source": self.mqttClientId,
        }
        self.mqttClient.publish(topic, json.dumps(payload))
    
    def _update_settop_box(self, payload):
        """Updates settopbox state"""
        deviceId = payload["source"]
        if deviceId != self.box_id:
            return
        self.logger.debug(payload)
        statusPayload = payload["status"]
        uiStatus = statusPayload["uiStatus"]
        if uiStatus == "mainUI":
            playerState = statusPayload["playerState"]
            sourceType = playerState["sourceType"]
            stateSource = playerState["source"]
            speed = playerState["speed"]
            if self.info is None:
                self.info = ZiggoNextBoxPlayingInfo()
            if sourceType == BOX_PLAY_STATE_REPLAY:
                self.info.setSourceType(BOX_PLAY_STATE_REPLAY)
                eventId = stateSource["eventId"]
                self.info.setChannel(None)
                self.info.setChannelTitle(None)
                self.info.setTitle(
                    "ReplayTV: " + self._get_recording_title(eventId)
                )
                self.info.setImage(self._get_recording_image(eventId))
                self.info.setPaused(speed == 0)
            elif sourceType == BOX_PLAY_STATE_DVR:
                self.info.setSourceType(BOX_PLAY_STATE_DVR)
                recordingId = stateSource["recordingId"]
                self.info.setChannel(None)
                self.info.setChannelTitle(None)
                self.info.setTitle(
                    "Recording: " + self._get_recording_title(recordingId)
                )
                self.info.setImage(
                    self._get_recording_image(recordingId)
                )
                self.info.setPaused(speed == 0)
            elif sourceType == BOX_PLAY_STATE_BUFFER:
                self.info.setSourceType(BOX_PLAY_STATE_BUFFER)
                channelId = stateSource["channelId"]
                channel = self.channels[channelId]
                eventId = stateSource["eventId"]
                self.info.setChannel(channelId)
                self.info.setChannelTitle(channel.title)
                self.info.setTitle(
                    "Delayed: " + self._get_recording_title(eventId)
                )
                self.info.setImage(channel.streamImage)
                self.info.setPaused(speed == 0)
            elif playerState["sourceType"] == BOX_PLAY_STATE_CHANNEL:
                self.info.setSourceType(BOX_PLAY_STATE_CHANNEL)
                channelId = stateSource["channelId"]
                eventId = stateSource["eventId"]
                channel = self.channels[channelId]
                self.info.setChannel(channelId)
                self.info.setChannelTitle(channel.title)
                self.info.setTitle(
                    self._get_channel_title(channelId, eventId)
                )
                self.info.setImage(channel.streamImage)
                self.info.setPaused(False)
            else:
                self.info.setSourceType(BOX_PLAY_STATE_CHANNEL)
                eventId = stateSource["eventId"]
                self.info.setChannel(None)
                self.info.setTitle("Playing something...")
                self.info.setImage(None)
                self.info.setPaused(speed == 0)
        elif uiStatus == "apps":
            appsState = statusPayload["appsState"]
            logoPath = appsState["logoPath"]
            if not logoPath.startswith("http:"):
                logoPath = "https:" + logoPath
            self.info.setSourceType(BOX_PLAY_STATE_APP)
            self.info.setChannel(None)
            self.info.setChannelTitle(appsState["appName"])
            self.info.setTitle(appsState["appName"])
            self.info.setImage(logoPath)
            self.info.setPaused(False)
    
    def _get_recording_title(self, scCridImi):
        """Get recording title."""
        response = requests.get(self._api_url_recording_format.format(id=scCridImi))
        if response.status_code == 200:
            content = response.json()
            return content["listings"][0]["program"]["title"]
        return None
    
    def _get_recording_image(self, scCridImi):
        """Get recording image."""
        response = requests.get(self._api_url_recording_format.format(id=scCridImi))
        if response.status_code == 200:
            content = response.json()
            return content["listings"][0]["program"]["images"][0]["url"]
        return None

    def _get_channel_title(self, channelId, scCridImi):
        """Get channel title"""
        response = requests.get(
            self._api_url_listing_format.format(stationId=channelId, id=scCridImi)
        )
        if response.status_code == 200:
            content = response.json()
            if len(content["listings"]) > 0:
                return content["listings"][0]["program"]["title"]
        return None
    
    def send_key_to_box(self,key: str):
        """Sends emulated (remote) key press to settopbox"""
        payload = (
            '{"type":"CPE.KeyEvent","status":{"w3cKey":"'
            + key
            + '","eventType":"keyDownUp"}}'
        )
        self.mqttClient.publish(self._householdId+ "/" + self.box_id, payload)
        self._request_settop_box_state()
    
    def set_channel(self, serviceId):
        payload = (
            '{"id":"'
            + _makeId(8)
            + '","type":"CPE.pushToTV","source":{"clientId":"'
            + self.mqttClientId
            + '","friendlyDeviceName":"Home Assistant"},"status":{"sourceType":"linear","source":{"channelId":"'
            + serviceId
            + '"},"relativePosition":0,"speed":1}}'
        )

        self.mqttClient.publish(self._householdId + "/" + self.box_id, payload)
        self._request_settop_box_state()
    
    def turn_off(self):
        self.info = ZiggoNextBoxPlayingInfo()