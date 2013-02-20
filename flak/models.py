from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import event

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class LibraryFolder(Base):
    __tablename__ = 'library_folders'
    root_path = Column(Text, primary_key=True)

    def __init__(self, root_path):
        self.name = root_path


class LibraryFile(Base):
    __tablename__ = 'library_files'
    # '%x' % f.info.md5_signature
    signature = Column(Text, primary_key=True)
    path = Column(Text, primary_key=True)
    size = Column(Integer)
    mtime = Column(DateTime(timezone=True))
    stream_info = Column(Text)
    seek_table = Column(Text)
    tags = Column(Text)

    def __init__(self, signature):
        self.name = signature

FUNCTIONS = [
"""
CREATE OR REPLACE FUNCTION get_attr(data json, key text)
RETURNS text[] AS $$
return data[key];
$$ LANGUAGE plv8 IMMUTABLE STRICT;
""",
"""
CREATE OR REPLACE FUNCTION get_searchable_text(data json)
RETURNS text AS $$
var all_text = [];

for(var key in data){
    all_text.push.apply(all_text, data[key]);
}

return all_text.join(' ');
$$ LANGUAGE plv8 IMMUTABLE STRICT;
""",
"""
CREATE OR REPLACE FUNCTION searchable_text_trigger()
RETURNS trigger AS $$
begin
  new.searchable_text :=
     to_tsvector('pg_catalog.english',
                 get_searchable_text(COALESCE(new.tags, '{}')));
  return new;
end
$$ LANGUAGE plpgsql;
""",
"""
CREATE OR REPLACE FUNCTION insert_libraryfiles(data json)
RETURNS json AS $$
var result = [];
var plan = plv8.prepare("INSERT INTO library_files (signature, path, size, mtime, stream_info, seek_table, tags) VALUES($1, $2, $3, $4, $5, $6, $7) RETURNING *",
                        ['text', 'text', 'integer', 'timestamptz', 'json', 'json', 'json'] );

for(var i=0; i<data.length; i++){
    var record = data[i];
    plv8.elog(WARNING, record.signature, record.path, record.size, record.mtime, record.stream_info,
                            record.seek_table, record.tags)
    var row = plan.execute([record.signature, record.path, record.size, record.mtime, record.stream_info,
                            record.seek_table, record.tags]);
    row.status = 'success';
    row.err_msg = '';
    result.push(row);
}

plan.free();
return result;
$$ LANGUAGE plv8 IMMUTABLE STRICT;
""",
]

def after_libraryfile_create(target, connection, **kw):
    # Update JSON columns
    sql = 'ALTER TABLE %s ALTER COLUMN %s TYPE json USING %s::json'
    for fname in ['stream_info', 'seek_table', 'tags']:
        connection.execute(sql % (target.name, fname, fname))

    # Add full-text search bits
    for function in FUNCTIONS:
        connection.execute(function)
    fts = [
        'ALTER TABLE %s ADD COLUMN searchable_text tsvector;',
        """
        CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
            ON %s FOR EACH ROW EXECUTE PROCEDURE searchable_text_trigger();
        """,
        """
        CREATE INDEX library_files_searchable_text
            ON %s USING gin(searchable_text)
        """,
    ]
    for sql in fts:
        connection.execute(sql % target.name)

event.listen(LibraryFile.__table__, "after_create", after_libraryfile_create)
