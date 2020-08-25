"""Python client for Ziggo Next."""

# Box states
ONLINE_RUNNING = "ONLINE_RUNNING"
ONLINE_STANDBY = "ONLINE_STANDBY"
UNKNOWN = "UNKNOWN"

BOX_PLAY_STATE_CHANNEL = "linear"
BOX_PLAY_STATE_REPLAY = "replay"
BOX_PLAY_STATE_DVR = "nDVR"
BOX_PLAY_STATE_BUFFER = "reviewbuffer"
BOX_PLAY_STATE_APP = "app"

# List with available media keys.
MEDIA_KEY_POWER = "Power"
MEDIA_KEY_ENTER = "Enter"  # Not yet implemented
MEDIA_KEY_ESCAPE = "Escape"  # Not yet implemented

MEDIA_KEY_HELP = "Help"  # Not yet implemented
MEDIA_KEY_INFO = "Info"  # Not yet implemented
MEDIA_KEY_GUIDE = "Guide"  # Not yet implemented

MEDIA_KEY_CONTEXT_MENU = "ContextMenu"  # Not yet implemented
MEDIA_KEY_CHANNEL_UP = "ChannelUp"
MEDIA_KEY_CHANNEL_DOWN = "ChannelDown"

MEDIA_KEY_RECORD = "MediaRecord"  # Not yet implemented
MEDIA_KEY_PLAY_PAUSE = "MediaPlayPause"
MEDIA_KEY_STOP = "MediaStop"  # Not yet implemented
MEDIA_KEY_REWIND = "MediaRewind"  # Not yet implemented
MEDIA_KEY_FAST_FORWARD = "MediaFastForward"  # Not yet implemented

COUNTRY_URLS_HTTP = {
    "nl": "https://web-api-prod-obo.horizon.tv/oesp/v3/NL/nld/web",
    "ch": "https://web-api-prod-obo.horizon.tv/oesp/v3/CH/eng/web",
    "be-nl": "https://web-api-prod-obo.horizon.tv/oesp/v3/BE/nld/web",
    "be-fr": "https://web-api-prod-obo.horizon.tv/oesp/v3/BE/fr/web",
    "at": "https://prod.oesp.magentatv.at/oesp/v3/AT/deu/web"
}
COUNTRY_URLS_PERSONALIZATION_FORMAT = {
    "nl": "https://prod.spark.ziggogo.tv/nld/web/personalization-service/v1/customer/{household_id}/devices",
    "ch": "https://prod.spark.ziggogo.tv/eng/web/personalization-service/v1/customer/{household_id}/devices",
    "be-nl": "https://prod.spark.ziggogo.tv/nld/web/personalization-service/v1/customer/{household_id}/devices",
    "be-fr": "https://prod.spark.ziggogo.tv/nld/web/personalization-service/v1/customer/{household_id}/devices",
    "at": "https://prod.spark.magentatv.at/deu/web/personalization-service/v1/customer/{household_id}/devices"
} 


COUNTRY_URLS_MQTT = {
    "nl": "obomsg.prod.nl.horizon.tv",
    "ch": "obomsg.prod.ch.horizon.tv",
    "be-nl": "obomsg.prod.be.horizon.tv",
    "be-fr": "obomsg.prod.be.horizon.tv",
    "at": "obomsg.prod.at.horizon.tv"
}
