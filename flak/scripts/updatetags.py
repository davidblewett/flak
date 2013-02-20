import collections
import fnmatch
from itertools import imap
import os
import sys

from pyramid.paster import bootstrap
from pyramid.paster import setup_logging
from pyramid.request import Request
from pyramid.settings import aslist
from pyramid.scripting import prepare

from sqlalchemy import engine_from_config
import transaction

from mutagen import flac
from walkdir import filtered_walk, file_paths

from flak.models import DBSession
from flak.models import LibraryFolder
from flak.models import LibraryFile
from flak.views import API


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    env = bootstrap(config_uri)
    settings = env['registry'].settings
    api_call_limit = int(settings.get('flak.api_call_limit', 50))
    library_paths = aslist(settings.get('flak.library_paths', []))
    api = API(env['request'], count=api_call_limit)

    with transaction.manager:
        consume(api.call('insert_libraryfiles',
                         get_flacs(get_file_paths(library_paths))),
                None)

    env['closer']()


def get_flacs(fpaths):
    for fpath in fpaths:
        try:
            parsed_flac = flac.FLAC(fpath)
        except (flac.error,), e:
            continue
        yield parsed_flac

def get_file_paths(root_paths, extension='flac'):
    pattern = '*.%s' % extension
    for root in root_paths:
        paths = file_paths(filtered_walk(root, included_files=[pattern]))
        for file_path in paths:
            yield file_path

def consume(iterator, n):
    "Advance the iterator n-steps ahead. If n is none, consume entirely."
    # Use functions that consume iterators at C speed.
    if n is None:
        # feed the entire iterator into a zero-length deque
        collections.deque(iterator, maxlen=0)
    else:
        # advance to the empty slice starting at position n
        next(islice(iterator, n, n), None)
