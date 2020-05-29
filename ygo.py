import argparse
import re
if not hasattr(re, '_pattern_type'):
	re._pattern_type = re.Pattern
import os.path
import sys

from ygo import globals
from ygo.exceptions import LanguageError
from ygo.language_handler import LanguageHandler
from ygo.parsers.login_parser import LoginParser
from ygo.server import Server
from ygo.utils import parse_lflist
from ygo.websockets import start_websocket_server

def main():
	globals.language_handler = LanguageHandler()
	print("Adding languages...")
	globals.language_handler.add('english', 'en')
	globals.language_handler.add("german", "de")
	globals.language_handler.add('japanese', 'ja')
	globals.language_handler.add('spanish', 'es')
	globals.language_handler.add('portuguese', 'pt')
	globals.language_handler.add('italian', 'it')
	globals.language_handler.add('french', 'fr')
	print("{count} languages added successfully.".format(count = len(globals.language_handler.get_available_languages())))
	try:
		globals.language_handler.set_primary_language('english')
	except LanguageError as e:
		print("Error setting primary language: "+str(e))
		sys.exit()
	globals.banlists = parse_lflist('lflist.conf')
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--port', type=int, default=4000, help="Port to bind to")
	parser.add_argument('-w', '--websocket-port', type=int)
	parser.add_argument('--websocket-cert', '-c')
	parser.add_argument('--websocket-key', '-k')
	args = parser.parse_args()
	server = Server(port = 4000, default_parser = LoginParser)
	server.port = args.port
	if args.websocket_port:
		start_websocket_server(args.websocket_port, args.websocket_cert, args.websocket_key)
	globals.server = server
	server.run()

main()