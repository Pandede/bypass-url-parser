#!/usr/bin/env python3
"""Bypass Url Parser, made with love by @TheLaluka
A tool that tests MANY url bypasses to reach a 40X protected page.

Usage:
    ./bypass-url-parser.py --url=<URL> [--outdir=<OUTDIR>] [--threads=<threads>] [--timeout=<timeout>] [(--header=<header>)...] [--spoofip=<ip>] [--debug]
    ./bypass-url-parser.py (-h | --help)
    ./bypass-url-parser.py (-v | --version)

Options:
    -h --help            Show help, you are here :)
    -v --version         Show version info.
    --url=<URL>          URL (path is optional) to run bypasses against.
    --outdir=<outdir>    Output directory for results.
    --timeout=<timeout>  Request times out after N seconds [Default: 3].
    --threads=<threads>  Scan with N parallel threads [Default: 1].
    --header=<header>    Header(s) to use, format: "Cookie: can_i_haz=fire".
    --spoofip=<ip>       IP to inject in ip-specific headers.
    --debug              Enable debugging output, to... Tou know... Debug.

Example:
    ./bypass-url-parser.py --url "http://127.0.0.1/juicy_403_endpoint/" --spoofip 8.8.8.8 --debug
    ./bypass-url-parser.py --url "http://127.0.0.1/juicy_403_endpoint/" --threads 30 --timeout 5 --header "Cookie: me_iz=damin" --header "Waf: bypazzzzz"
"""

import logging
from argparse import ArgumentParser, RawTextHelpFormatter

import coloredlogs

from src.config import DESCRIPTION, VERSION, Config
from src.parser import Bypasser

if __name__ == '__main__':
    arg_parser = ArgumentParser(
        description=DESCRIPTION,
        add_help=False,
        formatter_class=RawTextHelpFormatter
    )
    arg_parser.add_argument('-h', '--help', action='help', help='Show help, you are here :)')
    arg_parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {VERSION}', help='Show version info')
    arg_parser.add_argument('--url', type=str, required=True, help='URL (path is optional) to run bypasses against.')
    arg_parser.add_argument('--outdir', type=str, help='Output directory for results.')
    arg_parser.add_argument('--timeout', type=int, default=3, help='Request times out after N seconds [Default: 3].')
    arg_parser.add_argument('--threads', type=int, default=1, help='Scan with N parallel threads [Default: 1].')
    arg_parser.add_argument('--header', action='append', nargs=2, metavar=('key', 'value'), default=dict(), help='Header(s) to use, format: "--header Cookie can_i_haz=fire".')
    arg_parser.add_argument('--spoofip', type=str, help='IP to inject in ip-specific headers.')
    arg_parser.add_argument('--debug', action='store_true', help='Enable debugging output, to... Tou know... Debug.')
    opt = arg_parser.parse_args()
    config = Config.parse_obj(vars(opt))

    logger = logging.getLogger('bup')
    coloredlogs.install(
        logger=logger, level=logging.DEBUG if config.debug else logging.INFO
    )

    bypasser = Bypasser()
    curls = bypasser.generate_curls(config.url, config.header)
    responses = bypasser.run_curls(curls, config.timeout, config.threads)
    bypasser.save(config.outdir, responses)
