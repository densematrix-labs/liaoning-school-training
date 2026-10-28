"""Safe, read-only diagnostics for the configured MySQL source."""
import os
import pymysql
from app.services.production_data import identifier


def inspect_source(config):
    connection=pymysql.connect(host=os.environ['SCHOOL_DB_HOST'],port=int(os.getenv('SCHOOL_DB_PORT','3306')),
        user=os.environ['SCHOOL_DB_USER'],password=os.environ['SCHOOL_DB_PASSWORD'],database=os.environ['SCHOOL_DB_DATABASE'],
        connect_timeout=10,read_timeout=30,charset='utf8mb4',
        **({'ssl':{'ca':os.environ['SCHOOL_DB_SSL_CA']}} if os.getenv('SCHOOL_DB_SSL_CA') else {}))
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT VERSION()')
            version=cursor.fetchone()[0]
            cursor.execute('SHOW GRANTS')
            grants=[row[0].upper() for row in cursor.fetchall()]
            readonly=bool(grants) and all(('GRANT USAGE ' in g or 'GRANT SELECT ' in g) and 'WITH GRANT OPTION' not in g for g in grants)
            cursor.execute('SET TRANSACTION READ ONLY')
            cursor.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT')
            cursor.execute('SELECT COUNT(*) FROM '+identifier(config['table']))
            count=cursor.fetchone()[0]
            cursor.execute('SELECT COLUMN_NAME,DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION',(os.environ['SCHOOL_DB_DATABASE'],config['table']))
            columns=[{'name':row[0],'type':row[1]} for row in cursor.fetchall()]
        return {'engine':'MySQL','version':version,'connected':True,'select_only_grants':readonly,'table':config['table'],'row_count':count,'columns':columns}
    finally:
        connection.rollback()
        connection.close()
