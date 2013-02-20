import datetime
from json import dumps

from pyramid.config import Configurator
from pyramid.renderers import JSON
from sqlalchemy import engine_from_config

from mutagen import flac

from flak import adapters
from flak.models import DBSession
from flak.models import Base


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    # Setup database
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    # setup JSON adapters
    adapters.renderer = JSON()
    adapters.renderer.add_adapter(flac.FLAC, adapters.flac)
    adapters.renderer.add_adapter(datetime.datetime, adapters.datetime)
    adapters.renderer.add_adapter(flac.StreamInfo, adapters.attrs)
    adapters.renderer.add_adapter(flac.SeekTable, adapters.seektable)
    adapters.renderer.add_adapter(flac.CueSheet, adapters.cuesheet)
    adapters.renderer.add_adapter(flac.Picture, adapters.picture)
    adapters.renderer.add_adapter(flac.Padding, adapters.attrs)

    # generate config
    config = Configurator(settings=settings)
    config.include('pyramid_tm')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_renderer('json', adapters.renderer)
    config.add_route('home', '/')
    config.scan()

    return config.make_wsgi_app()
