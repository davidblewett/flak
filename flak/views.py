import logging

import transaction

from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy import bindparam
from sqlalchemy import func
from sqlalchemy.exc import DBAPIError
from sqlalchemy.sql.expression import select

from zope.sqlalchemy import mark_changed

from flak.models import DBSession
from flak.models import LibraryFolder
from flak.models import LibraryFile


@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    try:
        one = DBSession.query(LibraryFolders).filter(LibraryFolders.name == 'one').first()
    except DBAPIError:
        return Response(conn_err_msg, content_type='text/plain', status_int=500)
    return {'one': one, 'project': 'flak'}

conn_err_msg = """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to run the "initialize_flak_db" script
    to initialize your database tables.  Check your virtual
    environment's "bin" directory for this script and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""

class API(object):
    def __init__(self, request, count=50):
        self.request = request
        self._call_per = count
        self.queue = []
        self.logger = logging.getLogger('flak.api')
        self.session = DBSession()

    def call_per(self, count):
        self._call_per = count

    def call(self, func_name, param_generator):
        self.logger.debug('Beginning API call: %s', func_name)
        for params in param_generator:
            # NOTE: we queue the original params, so that the JSON
            #       encoder can encode a batch at a time when flushed
            #self.logger.debug('Queueing %s: %s', func_name, params)
            self.queue.append(params)
            if len(self.queue) >= self._call_per:
                for result in self.flush(func_name):
                    #self.logger.debug('Yielding result %s: %r',
                    #                  func_name, result)
                    yield result
        if self.queue:
            for result in self.flush(func_name):
                #self.logger.debug('Yielding result %s: %r', func_name, result)
                yield result
        self.logger.debug('API call finished: %s', func_name)

    def flush(self, func_name):
        if not self.queue:
            return []
        self.logger.debug('Flushing %d items', len(self.queue))
        sp = transaction.savepoint()
        api_func = getattr(func, func_name)
        json = render_to_response('json', self.queue).body
        param = bindparam('json_in', value=json)
        statement = select(['*'], from_obj=api_func(param))
        results = self.session.execute(statement, {'json_in': json})
        mark_changed(self.session)
        self.queue = []
        return results
