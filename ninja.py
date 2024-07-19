"""
ninja.py - steam server browser using keywords
"""

import configparser
import ipaddress
import os
import re
import sys
import time
from os.path import exists
import requests

CONFIG_FILE   = '.ninja.ini'
CURSOR        = '\033[?25h'
NOCURSOR      = '\033[?25l'
PRIVATE       = ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16']
RESET         = bool(sys.argv[1:] and sys.argv[1].lower() == 'reset')
SLEEP         = 60
TIMEOUT       = 10
ENDPOINT      = 'https://api.steampowered.com/IGameServersService/GetServerList/v1/'
FILTER        = '?filter=\\name_match\\*##KEYWORD##*&key=##KEY##'

config = configparser.ConfigParser()

def api_key():
    """ get api key from config """

    return config['API']['key']

def include():
    """ get include keywords from config """

    return config['API']['include'].split(';')

def exclude():
    """ get exclude keywords from config """

    return config['API']['exclude'].split(';')

def private():
    """ get private network toggle from config """

    return config['API'].getboolean('private')

def get_key():
    """ get the steam web api key from input """

    key = None
    msg = 'Enter your Steam Web API Key (https://steamcommunity.com/dev/apikey): '

    while key is None:
        clear_screen()
        key_string = input(msg).strip()

        if not valid_key(key_string):
            continue

        key = key_string

    return key

def get_include():
    """ get the include keywords from input """

    key = None
    msg = 'Enter the semicolon separated keywords to search for (quakecon;qcon): '

    while key is None:
        clear_screen()
        key_string = input(msg).strip()

        if not key_string:
            continue

        key = key_string

    return key

def get_exclude():
    """ get the exclude keywords from input """

    key = None
    msg = 'Enter the semicolon separated keywords to exclude from results (sydney;denver): '
    clear_screen()
    key = input(msg).strip()

    return key

def get_private():
    """ get option to include private networkds """

    msg = 'Do you want to include private networks in search results? (y/n): '
    clear_screen()
    key = input(msg).lower().strip() == 'y'

    return str(key)

def get_settings(cfg):
    """ validates the settings of the config file """

    if not cfg.has_section('API'):
        cfg.add_section('API')

    if RESET or not cfg.has_option('API', 'key'):
        cfg.set('API', 'key', get_key())

    if RESET or not cfg.has_option('API', 'include'):
        cfg.set('API', 'include', get_include())

    if RESET or not cfg.has_option('API', 'exclude'):
        cfg.set('API', 'exclude', get_exclude())

    if RESET or not cfg.has_option('API', 'private'):
        cfg.set('API', 'private', get_private())

def load_config():
    """ load the config file """

    if exists(CONFIG_FILE):
        config.read(CONFIG_FILE)

    get_settings(config)

    with open(CONFIG_FILE, 'w', encoding='ascii') as configfile:
        config.write(configfile)

def print_line(msg):
    """ print a message with no cursor """

    print(f'{NOCURSOR}{msg}')

class BColors:
    """ font colors """

    HEADER    = '\033[95m'
    OKBLUE    = '\033[94m'
    OKCYAN    = '\033[96m'
    OKGREEN   = '\033[92m'
    WARNING   = '\033[93m'
    FAIL      = '\033[91m'
    ENDC      = '\033[0m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'

def red_text(text):
    """ highlights text in red """

    return f'{BColors.FAIL}{text}{BColors.ENDC}'

def decolor(text):
    """ remove color codes from string """

    return re.sub(r'/\^[1-8]/', '', text)

def clear_screen():
    """ clear the terminal screen """

    os.system('cls' if os.name == 'nt' else 'clear')

def get_api_url(keyword):
    """ build api url """

    url = ENDPOINT + FILTER
    url = url.replace("##KEYWORD##", keyword)
    url = url.replace("##KEY##", api_key())

    return url.strip()

def api_call(url):
    """ makes a call to the Steam API """

    body = None
    error = None

    try:
        response = requests.get(
            url,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        body = response.json()
    except requests.HTTPError as e:
        error = f'HTTPError {e.response.status_code}'
    except requests.exceptions.ConnectionError:
        error = 'ConnectionError'
    except requests.exceptions.ReadTimeout:
        error = 'ReadTimeout'
    except requests.exceptions.JSONDecodeError:
        error = 'JSONDecodeError'
    except KeyError:
        error = 'KeyError'

    return body, error

def valid_key(string):
    """ Validate API Key """

    if not string:
        return False

    if not len(string) == 32:
        return False

    if not string.isalnum():
        return False

    return True

def valid_response(body):
    """ Validate JSON has required keys """

    if not body:
        return False

    if not 'response' in body:
        return False

    if not 'servers' in body['response']:
        return False

    return True

def print_servers(servers):
    """ print a list of servers """

    sort = dict(sorted(servers.items(), key=lambda x: (x[1]['game'], x[1]['name'])))

    ln_addr = 0
    ln_game = 0
    ln_pass = 0
    ln_name = 0
    ln_play = 0
    ln_map  = 0

    for a, s in sort.items():
        if len(a) > ln_addr:
            ln_addr = len(a)

        if len(s['game']) > ln_game:
            ln_game = len(s['game'])

        if len(s['password']) > ln_pass:
            ln_pass = len(s['password'])

        if len(s['name']) > ln_name:
            ln_name = len(s['name'])

        if len(s['players']) > ln_play:
            ln_play = len(s['players'])

        if len(s['map']) > ln_map:
            ln_map = len(s['map'])

    clear_screen()

    for address, server in sort.items():
        line = ''
        line += server['game'].ljust(ln_game)
        line += ' - '
        line += server['password'].ljust(ln_pass)
        line += server['name'].ljust(ln_name)
        line += ' - '
        line += server['players'].ljust(ln_play)
        line += ' - '
        line += server['map'].ljust(ln_map)
        line += ' - '
        line += f'steam://connect/{address}'

        print_line(line)

def private_network(ip):
    """ is IP in a private network range """

    for network in PRIVATE:
        if ipaddress.IPv4Address(ip) in ipaddress.IPv4Network(network):
            return True

    return False

def create_server(server_json):
    """ create server dictionary from json """  

    name = decolor(server_json['name'].strip())

    if exclude()[0] and any(ex.lower().strip() in name.lower() for ex in exclude()):
        return None

    addr        = server_json['addr'].strip()
    address     = addr.split(':')
    ip          = address[0].strip()

    if not private() and private_network(ip):
        return None

    gameport    = server_json['gameport']
    join_addr   = f'{ip}:{gameport}'

    product     = server_json['product'].strip()
    map_name    = decolor(server_json['map'].strip())

    players     = server_json['players']
    max_players = server_json['max_players']
    current_players = f'{players}/{max_players}'

    gametype    = server_json['gametype'].strip().lower().split(',')
    pw          = 'pw' in gametype
    password    = ''
    if pw:
        password = 'ꗃ '

    return {
        'game': product,
        'name': name,        
        'password': password,
        'players': current_players,
        'map': map_name,
        'address': join_addr 
    }

def get_servers(keyword):
    """ get servers by keyword """    
    servers = {}

    url = get_api_url(keyword)
    body, error = api_call(url)

    if error:
        print_line(red_text(f'ERROR: {error}'))
        time.sleep(SLEEP)

    if not valid_response(body):
        return servers

    for server in body['response']['servers']:
        server_dict = create_server(server)
        if server_dict:
            servers[server_dict['address']] = server_dict

    return servers

def run():
    """ run the server browser """

    while True:
        servers = {}

        for keyword in include():
            servers.update(get_servers(keyword))

        print_servers(servers)
        time.sleep(SLEEP)

load_config()
clear_screen()
print_line('Loading Servers...')

try:
    run()
except KeyboardInterrupt:
    pass

print(CURSOR, end='')
