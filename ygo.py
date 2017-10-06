import argparse
import os.path
import sqlite3

from ygo import globals
from ygo import i18n
from ygo.parsers.login_parser import LoginParser
from ygo.server import Server
from ygo.utils import parse_lflist
from ygo.websockets import start_websocket_server

def main():
  server = Server(port = 4000, default_parser = LoginParser)
  if os.path.exists('locale/de/cards.cdb'):
    globals.german_db = sqlite3.connect('locale/de/cards.cdb')
  if os.path.exists('locale/ja/cards.cdb'):
    globals.japanese_db = sqlite3.connect('locale/ja/cards.cdb')
  if os.path.exists('locale/es/cards.cdb'):
    globals.spanish_db = sqlite3.connect('locale/es/cards.cdb')
  for i in ('en', 'de', 'ja', 'es'):
    globals.strings[i] = i18n.parse_strings(os.path.join('locale', i, 'strings.conf'))
  globals.lflist = parse_lflist('lflist.conf')
  parser = argparse.ArgumentParser()
  parser.add_argument('-p', '--port', type=int, default=4000, help="Port to bind to")
  parser.add_argument('-w', '--websocket-port', type=int)
  parser.add_argument('--websocket-cert', '-c')
  parser.add_argument('--websocket-key', '-k')
  args = parser.parse_args()
  server.port = args.port
  if args.websocket_port:
    start_websocket_server(args.websocket_port, args.websocket_cert, args.websocket_key)
  globals.server = server
  server.run()

main()