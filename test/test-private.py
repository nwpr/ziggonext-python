from ziggonext import ZiggoNext, ZiggoNextConnectionError, ZiggoNextError, ZiggoNextSession
import pdb
def main(loop):
    print('test')
    try:
        print("test")
        client = ZiggoNext("r.offereins@gmail.com", "fictive:)")
        session = client.get_session()
        print(session)
    except (Exception):
        print("cannot connect")
