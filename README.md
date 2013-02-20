flak README
==================

Getting Started
---------------

- cd <directory containing this file>

- python2.7 bootstrap.py

- bin/buildout -v

- bin/supervisord

- bin/initialize_flak_db development.ini

- edit development.ini to point flak.library_paths to your music library

- bin/update_tags development.ini

- Then search via:
  - bin/psql -U flak -c "
SELECT *
FROM library_files
WHERE searchable_text @@ to_tsquery('beethoven & sonata & piano')"
