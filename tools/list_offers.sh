#! /bin/sh

python -c "import sqlite3; [print(r) for r in sqlite3.connect('leboncoin_offers.db').execute('SELECT * FROM offers')]"
