import anki
import argparse
import os
import shutil 
import simplejson as json
import sys
import tempfile
import urllib2

from anki.exporting import AnkiPackageExporter

# Process arguments
parser = argparse.ArgumentParser(description='Wikity to anki processor')
parser.add_argument('outfile', metavar='destination_file')
parser.add_argument('--anki-libs-dir', default='/usr/share/anki',
        help='Directory with anki libraries (default: %(default)s)')
parser.add_argument('--deck', default='wikity', help='Location of your wikity installation')
parser.add_argument('--wikity-url', required=True, help='Location of your wikity installation')
args = parser.parse_args()
sys.path.insert(0, args.anki_libs_dir)
if not args.outfile.endswith('.apkg'):
    args.outfile += '.apkg'
# Looks like anki libs change working directory to media directory of current deck
# Therefore absolute path should be stored before creating temporary deck
args.outfile = os.path.abspath(args.outfile)


# Get posts from WP API as json
wordpress_api_url = '%s/wp-json/wp/v2/' % args.wikity_url

page = 1 
cards = []

print 'Accessing posts at %s...' % wordpress_api_url

while True:
    print 'Parsing page %d' % page
    json_content = urllib2.urlopen(wordpress_api_url + 'posts?page=%d' % page)
    json_parsed = json.load(json_content)
    if len(json_parsed) == 0:
        break;
    cards = cards + json_parsed
    page = page + 1


# Build deck from retrieved json
print "Building deck '%s'..." % args.deck
temp_dir = tempfile.mkdtemp(prefix='anki_deck_generator.')

collection = anki.Collection(os.path.join(temp_dir, 'collection.anki2'))

deck_id = collection.decks.id(args.deck)
deck = collection.decks.get(deck_id)

model = collection.models.new("wikity_model")
model['tags'].append("wikity_tag")
model['did'] = deck_id

collection.models.addField(model, collection.models.newField('Title'))
collection.models.addField(model, collection.models.newField('Content'))

tmpl = collection.models.newTemplate('wikity')
tmpl['qfmt'] = '<div class="from">{{Title}}</div>'
tmpl['afmt'] = '{{FrontSide}}\n\n<hr id=answer>\n\n{{Content}}'
collection.models.addTemplate(model, tmpl)


model['id'] = 12345678  # essential for upgrade detection
collection.models.update(model)
collection.models.setCurrent(model)
collection.models.save(model)


for card in cards:
    note = anki.notes.Note(collection, model)
    note.guid = card['guid']['rendered']
    note['Title'] = card['title']['rendered']
    note['Content'] = card['content']['rendered']

    collection.addNote(note)

# Export deck
print 'Exporting deck...'
e = AnkiPackageExporter(collection)
e.exportInto(args.outfile)

print 'Done.'