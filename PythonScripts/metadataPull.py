"""
Extract metadata from Project Gutenberg RDF catalog into an array of dictionaries, then upload significant data to RDS
Create table:
CREATE TABLE booksmain(id SERIAL,title VARCHAR,author VARCHAR,languages[] VARCHAR,s3audioLocation VARCHAR,s3textLocation VARCHAR)
"""

try:
	import cPickle as pickle
except ImportError:
	import pickle
try:
    import gzip
    import tarfile
    import urllib.request
    import xml.etree.cElementTree as ElementTree
    import os
    import psycopg2
    import sys
    import boto3
    import time
    import select
    from threading import Thread
    from boto3 import Session
    from botocore.exceptions import BotoCoreError, ClientError
    import re
except:
    print('ERROR: You need to install the boto3, psycopg2, and boto3.polly libraries.')
    sys.exit(2)

instance = False
rds = boto3.client('rds')

response = rds.describe_db_instances(DBInstanceIdentifier='booksmain')
db_instances = response['DBInstances']

if len(db_instances) != 1:
    raise Exception("Hey! There's more than one instance of 'booksmain', this should not occur.")

db_instance = db_instances[0]
status = db_instance['DBInstanceStatus']
time.sleep(5)

if status == 'available':
    endpoint = db_instance['Endpoint']
    host = endpoint['Address']
    print('DB instance ready with host: %s' % host)

    instance = psycopg2.connect(database='booksMainDatabase', user='booksMainUser', password="hit51quasar", host=host, port='5432', connect_timeout=10)
    instance.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    print('Instance created')

    cur = instance.cursor()
    print('Cursor ready')

# The Python dict produced by this module
PICKLEFILE = '/tmp/metadata2.pickle.gz'
# The catalog downloaded from Gutenberg
RDFFILES = '/tmp/rdf-files.tar.bz2'
RDFURL = r'http://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.bz2'
META_FIELDS = ('id', 'author', 'title', 'downloads', 'formats', 'type',
                'LCC', 'subjects', 'authoryearofbirth', 'authoryearofdeath', 'language')
NS = dict(pg='http://www.gutenberg.org/2009/pgterms/', dc='http://purl.org/dc/terms/',
                dcam='http://purl.org/dc/dcam/', rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#')
LINEBREAKRE = re.compile('[ \t]*[\n\r]+[ \t]*')
ETEXTRE = re.compile(r'''
	e(text|b?ook)
	\s*
	(\#\s*(?P<etextid_front>\d+)
	|
	(?P<etextid_back>\d+)\s*\#)
	''', re.IGNORECASE | re.VERBOSE)

"""
Read/create cached metadata dump of Gutenberg catalog.
Returns:
    A dictionary with the following fields:
    id (int): Gutenberg identifier of text
    author (str): Last name, First name
    title (str): title of work
    subjects (list of str): list of descriptive subjects; a subject may be
        hierarchical, e.g:
        'England -- Social life and customs -- 19th century -- Fiction'
    LCC (list of str): a list of two letter Library of Congress
        Classifications, e.g., 'PS'
    language (list of str): list of two letter language codes.
    type (str): 'Text', 'Sound', ...
    formats (dict of str, str pairs): keys are MIME types, values are URLs.
    download count (int): the number of times this ebook has been
        downloaded from the Gutenberg site in the last 30 days.
Fields that are not part of the metadata are set to None.
http://www.gutenberg.org/wiki/Gutenberg:Help_on_Bibliographic_Record_Page
"""
def readmetadata():
    if os.path.exists(PICKLEFILE):
        metadata = pickle.load(gzip.open(PICKLEFILE, 'rb'))
    else:
        metadata = []
        for xml in getrdfdata():
            ebook = xml.find(r'{%(pg)s}ebook' % NS)
            if ebook is None:
                continue
            result = parsemetadata(ebook)
            if result is not None:
                print(result['id'])
                metadata.append(result)
        uploadDataToRDS(metadata)
    return metadata

"""
Downloads Project Gutenberg RDF catalog.
Yields:
	xml.etree.ElementTree.Element: An etext meta-data definition.
"""
def getrdfdata():
	if not os.path.exists(RDFFILES):
		_, _ = urllib.request.urlretrieve(RDFURL, RDFFILES)
	with tarfile.open(RDFFILES) as archive:
		for tarinfo in archive:
			yield ElementTree.parse(archive.extractfile(tarinfo))

"""
Parses an etext meta-data definition to extract fields.
Args:
	ebook (xml.etree.ElementTree.Element): An ebook meta-data definition.
"""
# Added default values to ensure no used values are None
def parsemetadata(ebook):
    result = dict.fromkeys(META_FIELDS)
    # get etext no
    about = ebook.get('{%(rdf)s}about' % NS)
    result['id'] = int(os.path.basename(about))
    # author
    creator = ebook.find('.//{%(dc)s}creator' % NS)
    if creator is not None:
        name = creator.find('.//{%(pg)s}name' % NS)
        if name is not None:
            result['author'] = safeunicode(name.text, encoding='utf-8')
        birth = creator.find('.//{%(pg)s}birthdate' % NS)
        if birth is not None:
            result['authoryearofbirth'] = int(birth.text)
        death = creator.find('.//{%(pg)s}deathdate' % NS)
        if death is not None:
            result['authoryearofdeath'] = int(death.text)
    else:
        result['author'] = 'null'
    # title
    title = ebook.find('.//{%(dc)s}title' % NS)
    if title is not None:
        result['title'] = fixsubtitles(
                safeunicode(title.text, encoding='utf-8'))
    else:
        result['title'] = 'null'
    # subject lists
    result['subjects'], result['LCC'] = set(), set()
    for subject in ebook.findall('.//{%(dc)s}subject' % NS):
        res = subject.find('.//{%(dcam)s}memberOf' % NS)
        if res is None:
            continue
        res = res.get('{%(rdf)s}resource' % NS)
        value = subject.find('.//{%(rdf)s}value' % NS).text
        if res == ('%(dc)sLCSH' % NS):
            result['subjects'].add(value)
        elif res == ('%(dc)sLCC' % NS):
            result['LCC'].add(value)
    # formats
    result['formats'] = {file.find('{%(dc)s}format//{%(rdf)s}value' % NS).text:
            file.get('{%(rdf)s}about' % NS)
            for file in ebook.findall('.//{%(pg)s}file' % NS)}
    # type
    booktype = ebook.find('.//{%(dc)s}type//{%(rdf)s}value' % NS)
    if booktype is not None:
        result['type'] = booktype.text
    # languages
    lang = ebook.findall('.//{%(dc)s}language//{%(rdf)s}value' % NS)
    if lang is not None:
        result['language'] = [a.text for a in lang] or None
    else:
        result['language'] = 'null'
    # download count
    downloads = ebook.find('.//{%(pg)s}downloads' % NS)
    if downloads is not None:
        result['downloads'] = int(downloads.text)
    else:
        result['downloads'] = 0
    return result

def fixsubtitles(title):
	"""Introduce any subtitle with (semi)colons instead of newlines.
	The first subtitle is introduced with a colon, the rest with semicolons.
	>>> fixsubtitles(u'First Across ...\r\nThe Story of ... \r\n'
	... 'Being an investigation into ...')
	u'First Across ...: The Story of ...; Being an investigation into ...'"""
	tmp = LINEBREAKRE.sub(': ', title, 1)
	return LINEBREAKRE.sub('; ', tmp)

def safeunicode(arg, *args, **kwargs):
	"""Coerce argument to str, if it's not already."""
	return arg if isinstance(arg, str) else str(arg, *args, **kwargs)

# Upload metadata to rds
def uploadDataToRDS(metadata):
    for book in metadata:
        if book['id'] != 0:
            cur.execute("INSERT INTO booksmain (id, title, author, languages, listens) VALUES (%s, %s, %s, %s, %s)", (book['id'], book['title'], book['author'], book['language'], book['downloads']))
__all__ = ['readmetadata']
data = readmetadata()

print('done')
