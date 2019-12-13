#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(format='%(asctime)s : %(filename)s : %(levelname)s : %(message)s')
logger = logging.getLogger()

import os
import re

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

from flask_cors import CORS
from flask import Flask, request
app = Flask(__name__)
CORS(app)

import json
import getopt
import sys
import traceback
from time import time as now
from urllib.parse import quote
import concurrent.futures
from copy import deepcopy

from bs4 import BeautifulSoup
from bs4.element import Comment, NavigableString, Tag

from diskcache import Cache
cache = Cache(BASE_DIR) if BASE_DIR != '/var/task' else Cache()

import requests
logging.getLogger('requests').setLevel(logging.INFO)

from rdflib import ConjunctiveGraph as Graph
from pyld import jsonld

SPARQL_DIR = os.path.join(BASE_DIR, 'sparql')

WB_SERVICE_ENDPOINT = 'https://lo7kh865s6.execute-api.us-east-1.amazonaws.com/prod'

DEFAULT_SITE = 'kg.jstor.org'

DEFAULT_STYLESHEET = '''
    .toc {
        display: none;
    }
    .entity {
        background-color:#B0E0E6;
        text-decoration: underline;
        text-decoration-color: gray;
    }
    .entity:hover {
        background-color:#B0E0E6;
        cursor: pointer;
    }
'''

class Entity(object):

    lists = ('aliases', 'images', 'coords')
    sets = ('part_of', 'apply_to')
    def __init__(self, **kwargs):
        self.aliases = kwargs.get('aliases')
        self.category = kwargs.get('category')
        if 'coords' in kwargs:
            coords = [float(x) for x in kwargs['coords'].replace('Point(','').replace(')','').split()]
            self.coords = [[coords[1], coords[0]]]
        else:
            self.coords = None
        self.description = kwargs.get('description')
        self.images = kwargs.get('images')
        self.label = kwargs.get('label')
        self.qid = kwargs.get('qid')
        self.part_of = kwargs.get('part_of', set())
        self.apply_to = kwargs.get('apply_to', set())
        self.title = kwargs.get('title')
        for fld in self.lists:
            if isinstance(self[fld], str):
                self[fld] = [self[fld]]
        for fld in self.sets:
            if isinstance(self[fld], str):
                self[fld] = set([self[fld]])   

    def __getitem__(self, key):
        return self.__dict__.get(key)

    def __setitem__(self, key, value):
        if key == 'coords':
            if not self.coords:
                self.coords = []
            if not isinstance(value, list):
                value = [value]
            for v in value:
                coords = [float(x) for x in v.replace('Point(','').replace(')','').split()]
                self.coords.append([coords[1], coords[0]])
        else:
            if key in self.__dict__:
                if key in self.lists and isinstance(value, str):
                    value = [value]
                elif key in self.sets and isinstance(value, str):
                    value = set([value])
                self.__dict__[key] = value

    def json(self):
        d = dict([(key, value) for key, value in vars(self).items() if value])
        for fld in self.sets:
            if fld in d:
                d[fld] = list(d[fld])
        return d

    def __repr__(self):
        return json.dumps(self.json(), sort_keys=True)

    def __str__(self):
        return self.__repr__()

class Map(object):

    default_zoom = 5
    lists = ('overlays')
    sets = ('part_of',)
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.center = kwargs.get('center')
        self.zoom = kwargs.get('zoom', self.default_zoom)
        self.overlays = kwargs.get('overlays')
        self.part_of = kwargs.get('part_of', set())
        for fld in self.lists:
            if isinstance(self[fld], str):
                self[fld] = [self[fld]]
        for fld in self.sets:
            if isinstance(self[fld], str):
                self[fld] = set([self[fld]])

    def __getitem__(self, key):
        return self.__dict__.get(key)

    def __setitem__(self, key, value):
        if key in self.__dict__:
            if key in self.lists and isinstance(value, str):
                value = [value]
            elif key in self.sets and isinstance(value, str):
                value = set([value])
            self.__dict__[key] = value

    def json(self):
        d = dict([(key, value) for key, value in vars(self).items() if value])
        for fld in self.sets:
            if fld in d:
                d[fld] = list(d[fld])
        return d

    def __repr__(self):
        return json.dumps(self.json(), sort_keys=True)

    def __str__(self):
        return self.__repr__()

def mw_to_html5(html):
    '''Transforms mediawiki generated HTML to semantic HTML'''
    _input = BeautifulSoup(html, 'html5lib')
    for elem in _input.find_all('span', {'class': 'mw-editsection'}):
        elem.decompose()
    for elem in _input.find_all(id='toc'):
        elem.decompose()
    base_html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title></title></head><body></body></html>'
    html5 = BeautifulSoup(base_html, 'html5lib')

    article = html5.new_tag('article', id='essay')
    article.attrs['data-app'] = 'true'
    html5.html.body.append(article)

    sections = []
    root = _input.find('div', {'class': 'mw-parser-output'})
    for elem in root.find_all(recursive=False):
        if isinstance(elem, Tag):
            if elem.name[0] == 'h' and elem.name[1:].isdigit():
                headline = elem.find('span', {'class': 'mw-headline'})
                if not headline:
                    continue
                level = int(elem.name[1:])
                title = headline.string
                tag = html5.new_tag('section', id=headline.attrs['id'])
                head = html5.new_tag(f'h{level}')
                head.string = title
                tag.append(head)
                section = {
                    'id': headline.attrs['id'],
                    'level': level,
                    'parent': None,
                    'tag': tag
                }
                for s in sections[::-1]:
                    if s['level'] < section['level']:
                        section['parent'] = s['id']
                        break
                sections.append(section)
            else:
                parent = sections[-1]['tag'] if sections else article
                parent.append(elem)

    sections = dict([(s['id'], s) for s in sections])

    for section in sections.values():
        parent = sections[section['parent']]['tag'] if section['parent'] else article
        parent.append(section['tag'])
    
    return str(html5)

def _remove_empty_tags(soup):
    for elem in soup.findAll(lambda tag: tag.name in ('p',)):
        contents = [t for t in elem.contents if t and (isinstance(t, str) and t.strip()) or t.name not in ('br',) and t.string and t.string.strip()]
        if not contents:
                elem.extract()
    return soup

class Essay(object):

    def __init__(self, html, **kwargs):
        self._soup = BeautifulSoup(html, 'html5lib')
        self.entities = self._find_entities()
        self.custom_components = self._find_custom_components()
        self._update_entities()
        self._tag_entities()
        self.maps = self._find_maps()
        #self._add_stylesheet(**kwargs)
        self._add_data()

    def _parent_section_id(self, elem, default=None):
        parent_section = None
        while elem.parent and parent_section is None:
            if elem.name == 'section':
                parent_section = elem
            elem = elem.parent
        return parent_section.attrs['id'] if parent_section and 'id' in parent_section.attrs else default

    def _find_entities(self):
        entities = {}
        for de in self._soup.html.body.article.find_all('span'):
            if 'data-entity' in de.attrs or 'entity' in de.attrs.get('class', []):
                attrs = dict([k.replace('data-',''),v] for k,v in de.attrs.items() if k not in ('data-entity', 'class'))
                if 'qid' in attrs:
                    if attrs['qid'] in entities:
                        entity = entities[attrs['qid']]
                    else:
                        entity = Entity(**attrs)
                        entities[attrs['qid']] = entity

                    parent_section_id = self._parent_section_id(de, self._soup.html.body.article.attrs['id'])
                    entity.part_of.add(parent_section_id)
                    if de.text:
                        de.attrs['class'] = 'entity'
                    else:
                        entity.apply_to.add(parent_section_id)
                if not de.text:
                    de.decompose()
        return entities

    def _update_entities(self):
        for attrs in self._get_entity_data([qid for qid in self.entities])['@graph']:
            entity = next((self.entities[qid] for qid in self.entities if qid == attrs['qid']), None)
            if entity:
                for k, v in attrs.items():
                    entity[k] = v

    def _find_maps(self):
        maps = {}
        for de in self._soup.find_all('div'):
            if 'data-map' in de.attrs or 'map' in de.attrs.get('class', []):
                attrs = dict([k.replace('data-',''),v] for k,v in de.attrs.items() if k not in ('data-map', 'class'))
                if 'center' in attrs:
                    mapid = f'map-{len(maps)+1}'
                    de.attrs['id'] = mapid
                    de.attrs['class'] = 'map'
                    _map = Map(id=mapid, **attrs)
                    parent_section_id = self._parent_section_id(de, self._soup.html.body.article.attrs['id'])
                    _map.part_of.add(parent_section_id)
                    maps[mapid] = _map
                    de.name = 'figure'
        return maps

    def _find_custom_components(self):
        components = {}
        for de in self._soup.html.body.article.find_all('span'):
            if 'data-component' in de.attrs or 'component' in de.attrs.get('class', []):
                attrs = dict([k.replace('data-',''),v] for k,v in de.attrs.items() if k not in ('data-component', 'class'))
                if 'name' in attrs and 'src' in attrs:
                    components[attrs['name']] = attrs['src']
                de.decompose()
        return components

    def _add_stylesheet(self, **kwargs):
        if 'style' in kwargs:
            if not self._soup.html.head.style:
                self._soup.html.head.append(self._soup.new_tag('style'))
            self._soup.html.head.style.string = kwargs.pop('style')

    def _add_data(self):
        data = self._soup.new_tag('script')
        data.append('\nwindow.data = ' + json.dumps({
            'entities': dict([(qid, entity.json()) for qid, entity in self.entities.items()]),
            'maps': dict([(mapid, _map.json()) for mapid, _map in self.maps.items()]),
            'customComponents': self.custom_components
        }, indent=2) + '\n')
        self._soup.html.body.article.append(data)

    def _section_ids_for_elem(self, elem):
        section_ids = set()
        while elem:
            if elem.name in('section', 'article') and 'id' in elem.attrs:
                section_ids.add(elem.attrs['id'])
            elem = elem.parent
        return section_ids

    def _tag_entities(self):
        def tag_visible(element):
            '''Returns true if text element is visible and not a comment.'''
            if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
                return False
            if isinstance(element, Comment):
                return False
            return True

        to_match = {}
        for entity in self.entities.values():
            to_match[entity.label.lower()] = entity
            if entity.aliases:
                for alias in entity.aliases:
                    to_match[alias.lower()] = entity

        for e in [e for e in filter(tag_visible, self._soup.findAll(text=True)) if e.strip() != '']:
            context = self._section_ids_for_elem(e)
            snorm = e.string.lower()
            matches = []
            for tm in to_match:
                try:
                    for m in [m.start() for m in re.finditer(tm, snorm)]:
                        start = m
                        end = start + len(tm)
                        overlaps = False
                        for match in matches:
                            mstart = match['idx']
                            mend = mstart + len(match['matched'])
                            if (start >= mstart and start <= mend) or (end >= mstart and end <= mend):
                                overlaps = True
                                break
                        if not overlaps:
                            matches.append({'idx': m, 'matched': e.string[m:m+len(tm)], 'entity': to_match[tm]})
                except:
                    pass
            matches.sort(key=lambda x: x['idx'], reverse=False)
            if matches:
                p = e.parent
                s = e.string
                for idx, child in enumerate(p.children):
                    if child == e:
                        break

                cursor = 0
                replaced = []
                for rec in matches:
                    m = rec['idx']
                    entity = rec['entity']
                    if m > cursor:
                        seg = s[cursor:m]
                        if replaced:
                            p.insert(idx+len(replaced), seg)
                        else:
                            e.replace_with(seg)
                        replaced.append(seg)
                        cursor = m

                    if entity.apply_to.intersection(context):
                        # make tag for matched item
                        seg = self._soup.new_tag('span')
                        seg.string = rec['matched']
                        seg.attrs['title'] = entity.label
                        seg.attrs['class'] = 'entity'
                        seg.attrs['data-qid'] = entity.qid
                    else:
                        seg = s[cursor:cursor+len(rec['matched'])]
                    if replaced:
                        p.insert(idx+len(replaced), seg)
                    else:
                        e.replace_with(seg)
                    replaced.append(rec['matched'])
                    cursor += len(rec['matched'])

                if cursor < len(s):
                    seg = s[cursor:]
                    p.insert(idx+len(replaced), seg)
                    replaced.append(seg)
        _remove_empty_tags(self._soup)
    
    def _get_entity_data(self, qids):
        sparql = open(os.path.join(SPARQL_DIR, 'entities.rq'), 'r').read()
        sparql = sparql.replace('VALUES (?item) {}', f'VALUES (?item) {{ (wd:{") (wd:".join(qids)}) }}')
        context = json.loads(open(os.path.join(SPARQL_DIR, 'entities_context.json'), 'r').read())
        resp = requests.post(
            'https://query.wikidata.org/sparql',
            headers={
                'Accept': 'text/plain',
                'Content-type': 'application/x-www-form-urlencoded'},
            data='query=%s' % quote(sparql)
        )
        if resp.status_code == 200:
            # Convert N-Triples to json-ld using json-ld context
            graph = Graph()
            graph.parse(data=resp.text, format='nt')
            _jsonld = json.loads(str(graph.serialize(format='json-ld', context=context, indent=None), 'utf-8'))
            if '@graph' not in _jsonld:
                _context = _jsonld.pop('@context')
                _jsonld = {'@context': _context, '@graph': [_jsonld]}
            return _jsonld

    def _add_leaflet(self):
        '''Add Leaflet CSS and JS links'''
        self._soup.html.head.append(BeautifulSoup('<link rel="stylesheet" href="https://unpkg.com/leaflet@1.6.0/dist/leaflet.css" integrity="sha512-xwE/Az9zrjBIphAcBb3F6JVqxf46+CDLwfLMHloNu6KEQCAWi6HcDUbeOfBIptF7tcCzusKFjFw2yuvEpDL9wQ==" crossorigin=""/>', 'html5lib'))
        self._soup.html.body.append(BeautifulSoup('<script src="https://unpkg.com/leaflet@1.6.0/dist/leaflet.js" integrity="sha512-gZwIG9x3wUXg2hdXF6+rVkLF/0Vi9U8D2Ntg4Ga5I5BZpVkVxlJWbSQtXPSiUTtC0TjtGOmxa1AJPuV0CPthew==" crossorigin=""></script>', 'html5lib'))

    def _add_maps(self):
        base = self._soup.find('div', {'class': 'mw-parser-output'}).parent
        if self.maps:
            self._add_leaflet()
            for _map in self.maps:
                map_loc = self._soup.find(id=list(_map.scope)[0])
                map_loc.append(BeautifulSoup(f'<div id="{_map.id}" style="height:400px; width:400px;"></div>', 'html5lib'))
                tag = self._soup.new_tag('div')
                tag.string = 'test'
                base.append(tag)
                coords = [[38.9139, -77.0635]]
                markers = [f'L.marker({c}).addTo(mymap);' for c in coords]
                map_script = '''
<script>
    var mymap = L.map('%s').setView([%s], %s);
	L.tileLayer('https://{s}.tile.osm.org/{z}/{x}/{y}.png').addTo(mymap);
	%s
</script>''' % (_map.id, _map.center, _map.zoom, '\n	'.join(markers))
                base.append(BeautifulSoup(map_script, 'html5lib'))

    @property
    def json(self):
        return {
            'html': str(self._soup),
            'entities': [entity.json() for entity in self.entities.values()]
        }

    def __repr__(self):
        return json.dumps(self.json, sort_keys=True)

    @property
    def html(self):
        #return self._soup.prettify()
        return str(self._soup)

    def __str__(self):
        return self.html

class EssayUtils(object):

    def __init__(self, site=False, **kwargs):
        self.default_site = site if site else DEFAULT_SITE

    def page(self, title, site=None, wikitext=False, **kwargs):
        site = site if site else self.default_site
        logger.info(f'page: title={title} site={site} wikitext={wikitext}')
        try:
            if wikitext:
                url = f'https://{site}/w/api.php?action=query&prop=revisions&rvprop=content&format=json&formatversion=2&titles={quote(title)}'
                resp = requests.get(url, headers={'Accept': 'application/json'}).json()
                return resp['query']['pages'][0]['revisions'][0]['content']
            else:
                url = f'https://{site}/w/api.php?action=parse&format=json&page={quote(title)}'
                resp = requests.get(url, headers={'Accept': 'application/json'}).json()
                resp ['html'] = f'<!doctype html><html lang="en">\n<head>\n<meta charset="utf-8">\n<title>{title}</title>\n</head>\n<body>\n' + resp.pop('parse')['text']['*'] + '\n</body>\n</html>'
                return resp
        except:
            return None

def add_vue_app(arg):
    soup = arg if isinstance(arg, BeautifulSoup) else BeautifulSoup(arg, 'html5lib')

    # http_vue_loader = soup.new_tag('script')
    # http_vue_loader.attrs['src'] = 'https://unpkg.com/http-vue-loader'
    # soup.html.body.append(http_vue_loader)

    for url in [
        'https://unpkg.com/leaflet@1.6.0/dist/leaflet.css',
        'https://cdnjs.cloudflare.com/ajax/libs/vuetify/2.1.12/vuetify.min.css'
        ]:
        style = soup.new_tag('link')
        style.attrs['rel'] = 'stylesheet'
        style.attrs['href'] = url
        soup.html.head.append(style)

    for url in [
        'https://unpkg.com/leaflet@1.6.0/dist/leaflet.js',
        'https://rsnyder.github.io/essay-utils/essay-utils-0.1.6.min.js'
        #'http://localhost:8081/js/index.js'
        ]:
        lib = soup.new_tag('script')
        lib.attrs['src'] = url
        soup.html.body.append(lib)

    return str(soup)

@app.route('/healthcheck')
def healthcheck():
    return 'OK'        

@app.route('/page', methods=['GET', 'POST'])
def page():
    kwargs = dict([(k, request.args.get(k)) for k in request.args])
    accept = request.headers.get('Accept', 'application/json').split(',')
    content_type = ([ct for ct in accept if ct in ('text/html', 'application/json', 'text/csv', 'text/tsv')] + ['application/json'])[0]
    as_json = kwargs.pop('format', None) == 'json' or content_type == 'application/json'

    page_data = client.page(**kwargs)
    page_data['style'] = DEFAULT_STYLESHEET
    page_data['html'] = mw_to_html5(page_data['html'])
    essay = Essay(**page_data)

    if as_json:
        essay = json.dumps(essay.json)
        if content_type == 'text/html':
            essay = open('viewer.html', 'r').read().replace("'{{DATA}}'", essay)
    else:
        essay = add_vue_app(essay.html)
    return app.response_class(essay, status=200, mimetype=content_type)

def usage():
    print(f'{sys.argv[0]} [hl:s:e:f:w] title')
    print(f'   -h --help          Print help message')
    print(f'   -l --loglevel      Logging level (default=warning)')
    print(f'   -s --site          Baseurl for source text (default="{DEFAULT_SITE}")')
    print(f'   -e --language      Language (default="en")')
    print(f'   -f --format        Format (json, html) (default=json)')
    print(f'   -w --wikitext      Return wikitext')

if __name__ == '__main__':
    logger.setLevel(logging.WARNING)
    kwargs = {}
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], 'hl:s:e:f:w', ['help', 'loglevel', 'site', 'language', 'format', 'wikitext'])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err))  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ('-l', '--loglevel'):
            loglevel = a.lower()
            if loglevel in ('error',): logger.setLevel(logging.ERROR)
            elif loglevel in ('warn','warning'): logger.setLevel(logging.INFO)
            elif loglevel in ('info',): logger.setLevel(logging.INFO)
            elif loglevel in ('debug',): logger.setLevel(logging.DEBUG)
        elif o in ('-s', '--site'):
            kwargs['site'] = a
        elif o in ('-e', '--language'):
            kwargs['language'] = a
        elif o in ('-w', '--wikitext'):
            kwargs['wikitext'] = True
        elif o in ('-f', '--format'):
            kwargs['content_type'] = 'text/html' if a == 'html' else 'application/json'
        elif o in ('-h', '--help'):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    client = EssayUtils(**kwargs)

    if args:
        title = args[0]
        page_data = client.page(title, **kwargs)
        mw_html = page_data['text']['*']
        essay = Essay(mw_to_html5(mw_html))
        #print(json.dumps([entity.json() for entity in essay.entities.values()]))
        print(essay.html)
    else:
        app.run(debug=True, host='0.0.0.0')