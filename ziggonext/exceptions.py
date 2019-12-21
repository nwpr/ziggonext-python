"""Python client for Ziggo Next."""
class ZiggoNextError(Exception):
    pass

class ZiggoNextConnectionError(ZiggoNextError):
    pass