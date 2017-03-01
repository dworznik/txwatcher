import threading
import time
import json
import logging

from events import Events
import websocket

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

addresses_to_add = ['raz']

class TxWatcher(Events):
    __events__ = ['on_tx', 'on_block']

    def __init__(self, addresses=[]):
        self.dupa = 'init'
        self.addresses = set(addresses)
        self.events = Events()

    def on_message(self, ws, message):
        data = json.loads(message)
        log.debug("Receiving: {0}".format(data))
        if(data['op'] == 'block'):
            self.on_block(data)
        else:
            self.on_tx(data)

    def on_error(self, ws, error):
        log.exception(error)

    def on_close(self, ws):
        log.critical('Closing WebSocket connection')


    def add_new_address(self, addr):
        self.add_addresses(*[addr])

    def add_addresses(self, *addresses, **kwargs):
        for addr in addresses:
            time.sleep(0.1)
            log.debug('Sending: {"op": "addr_sub", "addr": "' + addr + '"}')
            kwargs.get('ws', self.ws).send('{"op": "addr_sub", "addr": "' + addr + '"}')

    def receive_blocks(self, **kwargs):
        log.debug('Sending: {"op": "blocks_sub"}')
        kwargs.get('ws', self.ws).send('{"op": "blocks_sub"}')

    def on_open(self, ws):
        def run(*args):
            self.add_addresses(*self.addresses, ws=ws)
            self.receive_blocks(ws=ws)
            # Ping every 30 secs so we won't get disconnected
            while 1:
                log.debug('Sending ping')
                ws.send('')
                time.sleep(30)
        t = threading.Thread(target=run)
        t.start()

    def _run_forever(self):
        global addresses_to_add
        log.info('Starting Blockchain WebSocket server...')
        self.ws = websocket.WebSocketApp("wss://ws.blockchain.info/inv",
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        self.add = addresses_to_add
        self.ws.on_open = self.on_open
        self.ws.run_forever()

    def run_forever(self):
        delay = 1
        while 1:
            # Trying to run_forever using an exponential backoff
            try:
                self._run_forever()
            except websocket.WebSocketException as exc:
                log.exception(exc)
                log.warning('Trying to restart connection in {0} seconds...'.format(delay))
                time.sleep(delay)
                delay *= 2
            except Exception as exc:
                raise exc
