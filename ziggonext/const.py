"""Python client for Ziggo Next."""

# Box states
ONLINE_RUNNING = "ONLINE_RUNNING"
ONLINE_STANDBY = "ONLINE_STANDBY"

BOX_PLAY_STATE_CHANNEL = "linear"
BOX_PLAY_STATE_REPLAY = "replay"
BOX_PLAY_STATE_DVR = "nDVR"
BOX_PLAY_STATE_BUFFER = "reviewbuffer"

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
