"""Python client for Ziggo Next."""
class ZiggoNextSession:
    householdId: str
    oespToken: str

    def __init__(self, houseHoldId, oespToken):
        self.householdId = houseHoldId
        self.oespToken = oespToken

class ZiggoNextBoxPlayingInfo:
    channelId: str
    title: str
    image: str
    sourceType: str
    paused: bool

    def __init__(self):
        self.channelId = None
        self.title = None
        self.image = None
        self.sourceType = None
        self.paused = False
        self.channelTitle = None

    def setPaused(self, paused: bool):
        self.paused = paused

    def setChannel(self, channelId):
        self.channelId = channelId

    def setTitle(self, title):
        self.title = title

    def setChannelTitle(self, title):
        self.channelTitle = title

    def setImage(self, image):
        self.image = image

    def setSourceType(self, sourceType):
        self.sourceType = sourceType

class ZiggoChannel:
    serviceId: str
    title: str
    streamImage: str
    logoImage: str
    channelNumber: str

    def __init__(self, serviceId, title, streamImage, logoImage, channelNumber):
        self.serviceId = serviceId
        self.title = title
        self.streamImage = streamImage
        self.logoImage = logoImage
        self.channelNumber = channelNumber