#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(format='%(asctime)s : %(filename)s : %(levelname)s : %(message)s')
logger = logging.getLogger()

import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

import json
import getopt
import sys
import traceback
from time import time as now
from urllib.parse import quote
import concurrent.futures
from copy import deepcopy

from diskcache import Cache
cache = Cache(BASE_DIR) if BASE_DIR != '/var/task' else Cache()

import requests
logging.getLogger('requests').setLevel(logging.INFO)

from rdflib import ConjunctiveGraph as Graph
from pyld import jsonld

SPARQL_DIR = os.path.join(BASE_DIR, 'sparql')

WB_SERVICE_ENDPOINT = 'https://lo7kh865s6.execute-api.us-east-1.amazonaws.com/prod'

GRAPHS = {
    'jstor': {
        'prefix': '<http://kg.jstor.org/entity/>',
        'sparql_endpoint': 'https://kg-query.jstor.org/proxy/wdqs/bigdata/namespace/wdq/sparql',
        'types': {
            'entity': 'Q13'
        }
    },
    'wd': {
        'prefix': '<http://www.wikidata.org/entity/>',
        'sparql_endpoint': 'https://query.wikidata.org/sparql',
        'types': {
            'entity': 'Q35120'
        }
    }
}
default_ns = 'jstor'
default_language = 'en'
default_entity_type = 'entity'

class KnowledgeGraph(object):

    def __init__(self, **kwargs):
        self.ns = kwargs.get('ns', default_ns)
        self.language = kwargs.get('language', default_language)
        self.entity_type = kwargs.get('entity_type', default_entity_type)

    @cache.memoize()
    def _get_context(self, ns, language):
        _context_template = open(os.path.join(SPARQL_DIR, f'{GRAPHS[ns]["prefix"].split("/")[2].replace(".","_")}_context.json'), 'r').read()
        return json.loads(_context_template.replace('"en"', f'"{language}"').replace('"wd"', f'"{ns}"').replace('wd:', f'{ns}:'))

    @cache.memoize()
    def entity(self, qid, language=None, entity_type=None):
        logger.info(f'entity: qid={qid} language={language} entity_type={entity_type}')
        language = language if language else self.language
        entity_type = entity_type if entity_type else self.entity_type
        ns, qid = qid.split(':') if ':' in qid else (self.ns, qid)
        primary = f'{ns}:{qid}'
        secondary = self._secondary_qid(primary)
        logger.info(f'entity: primary={primary} secondary={secondary}')

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            by_qid = {}
            futures = {}
            for qid in [_qid for _qid in (secondary, primary) if _qid]:
                futures[executor.submit(self._entity, qid, language, entity_type)] = qid

            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    by_qid[futures[future]] = future.result()
        
        entity = self._merge(by_qid.get(primary), by_qid.get(secondary))
        entity['language'] = language
        self._add_summary_text(entity)
        return entity

    @cache.memoize()
    def _entity(self, qid, language='en', entity_type='entity'):
        ns, qid = qid.split(':') if ':' in qid else (self.ns, qid)
        sparql = '''
        CONSTRUCT {
            wd:%s a "%s" .
            wd:%s ?p ?o .
             wd:%s schema:isPartOf ?wikipedia_page .
        } WHERE {
            wd:%s ?p ?o .
            OPTIONAL {
                ?wikipedia_page schema:about wd:%s .
                FILTER(STRSTARTS(STR(?wikipedia_page), 'https://%s.wikipedia.org'))
            }
        }''' % (qid, entity_type, qid, qid, qid, qid, language)
        context = self._get_context(ns, language)
        _jsonld = self._do_jsonld_sparql_query(sparql, context, GRAPHS[ns]['sparql_endpoint'])
        # post process returned jsonld
        for func in (self._frame, self._filter_props, self._link_values, self._add_id_labels):
            _jsonld = func(_jsonld, context=context, entity_type=entity_type, ns=ns)
        return _jsonld
    
    '''
        Methods for post-processing jsonld returned in sparql query
    '''
    def _frame(self, _jsonld, context, entity_type='entity', **kwargs):
        CONTEXT_EXCLUDE_IN_FRAME = ['wd', 'wds', 'wdv', 'wdt', 'wdtn', 'p', 'ps', 'pq', 'prov', 'rdfs', 'schema', 'skos', 'wikibase', 'xsd']
        _frame = {
            '@explicit': True,
            '@requireAll': False,
            '@context': context,
            '@type': entity_type
        }
        for prop in [p for p in context if p not in CONTEXT_EXCLUDE_IN_FRAME]:
            _frame[prop] = {}
        # print(json.dumps(_jsonld))
        # print(json.dumps(_frame))
        framed = jsonld.frame(_jsonld, frame=_frame)
        return framed['@graph'][0] if '@graph' in framed and framed['@graph'] else {}

    def _add_id_labels(self, d, **kwargs):
        if not isinstance(d, (dict, list, str)):
            return d
        if isinstance(d, str):
            if self._is_entity_id(d):
                self._label(d, language=kwargs.get('language', 'en'))
                d = {'id': d, 'value': self._label(d, language=kwargs.get('language', 'en'))}
                if self._is_entity_id(d['id']):
                    d['url'] = d['id'].replace(f'{self.ns}:', f'https://{GRAPHS[self.ns]["prefix"].split("/")[2]}/entity/').replace('wd:', 'https://www.wikidata.org/entity/')
            return d
        elif isinstance(d, list):
            return [v for v in (self._add_id_labels(v, **kwargs) for v in d) if v]
        return {k: v for k, v in ((k, self._add_id_labels(v, **kwargs)) for k, v in d.items()) if v}

    def _link_values(self, d, **kwargs):
        def to_url(k, v):
            formatters = self._formatter_urls(k, ns=kwargs.get('ns', self.ns), language=kwargs.get('language', 'en')) if k not in ('id', 'label', 'type', 'description', 'date modified', 'coordinate location') else None                
            if formatters:
                if isinstance(v, list):
                    v = [{'value': val, 'url': f.replace('$1', val)} for f in formatters for val in v]
                elif isinstance(v, str):
                    vals = [{'value': v, 'url': f.replace('$1', v)} for f in formatters]
                    v = vals if len(vals) > 1 else vals[0]
            return v
        if not isinstance(d, (dict, list)):
            return d
        elif isinstance(d, list):
            return [v for v in (self._link_values(v, **kwargs) for v in d) if v]
        return {k: to_url(k,v) for k, v in ((k, self._link_values(v, **kwargs)) for k, v in d.items())}

    def _filter_props(self, d, **kwargs):
        def exclude(prop):
            if prop.startswith('p:P'): return True
            if prop.startswith('wikibase:'): return True
            if prop in ('rdfs:label', 'schema:description', 'schema:version', 'skos:altLabel'): return True
            return False
        if not isinstance(d, (dict, list)):
            return d
        elif isinstance(d, list):
            return [v for v in (self._filter_props(v, **kwargs) for v in d) if v]
        return {k: v for k, v in ((k, self._filter_props(v, **kwargs)) for k, v in d.items() if v and not exclude(k))}


    '''
        Various helper methods
    '''
    
    def _do_jsonld_sparql_query(self, sparql, context, endpoint):
        # Perform SPARQL CONSTRUCT query and request results returned in N-Triples format
        resp = requests.post(
            endpoint,
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

    def _is_entity_id(self, s, **kwargs):
        if not s or not isinstance(s, str): return False
        eid = s.split(':', 1)[1] if ':' in s else s
        return len(s) > 1 and eid[0] in ('Q', 'P') and eid[1:].isdecimal()

    @cache.memoize()
    def _eid_from_label(self, label, ns=None, language=None):
        ns = ns if ns else self.ns
        language = language if language else self.language
        try:
            eid = requests.post(
                f'{WB_SERVICE_ENDPOINT}/find',
                json = {'ns': ns, 'text': label, 'type': 'property', 'language': language}
            ).json()['id']
        except:
            eid = None
        logger.debug(f'eid_from_label: ns={ns} text="{label}" language={language} eid={eid}')
        return eid

    @cache.memoize()
    def _formatter_urls(self, eid, ns=None, language=None):
        ns = ns if ns else self.ns
        language = language if language else self.language
        formatter_urls = []
        _eid = eid if self._is_entity_id(eid) else self._eid_from_label(eid, ns, language)
        if _eid and _eid[0] == 'P':
            endpoint = GRAPHS[ns]['sparql_endpoint']
            prefix = GRAPHS[ns]['prefix'].split('/')[2]
            if ns == 'wd':
                query = '''
                SELECT ?formatterUrl WHERE {
                    <http://%s/entity/%s> <http://%s/prop/direct/P1630> ?formatterUrl .
                }''' % (prefix, _eid, prefix)
            else:
                query = '''
                SELECT ?formatterUrl WHERE {
                    <http://%s/entity/%s> <http://%s/prop/direct/P4> ?wdItem .
                    SERVICE <https://query.wikidata.org/sparql> {
                        ?wdItem <http://www.wikidata.org/prop/direct/P1630> ?formatterUrl .
                    }
                }''' % (prefix, _eid, prefix)
            resp = requests.get(
                    '{}?query={}'.format(endpoint, quote(query)),
                    headers={'Accept': 'application/sparql-results+json'},
                ).json()
            formatter_urls = [item['formatterUrl']['value'] for item in resp['results']['bindings']]
            logger.debug('formatter_urls: ns=%s eid="%s" _eid=%s formatter_urls=%s', ns, eid, _eid, formatter_urls)
        return formatter_urls

    @cache.memoize()
    def _label(self, eid, language=None):
        language = language if language else self.language
        ns, eid = eid.split(':') if ':' in eid else (self.ns, eid)
        url = f'{WB_SERVICE_ENDPOINT}/label/{ns}:{eid}?language={language}'
        label = requests.get(f'{WB_SERVICE_ENDPOINT}/label/{ns}:{eid}?language={language}').text
        logger.debug(f'_label: eid={eid} ns={ns} label="{label}"')
        return label

    def _secondary_qid(self, primary):
        primary_ns, primary_qid = primary.split(':')
        if primary_ns == self.ns:
            secondary_ns = 'wd'
            jstorqid = f'wd:{primary_qid}'
            wdqid = '?qid'
        else:
            secondary_ns = self.ns
            jstorqid = '?qid'
            wdqid = f'<http://www.wikidata.org/entity/{primary_qid}>'
        resp = requests.post(
            GRAPHS[self.ns]['sparql_endpoint'],
            headers={
                'Accept': 'application/sparql-results+json;charset=UTF-8',
                'Content-type': 'application/x-www-form-urlencoded'},
            data='query=%s' % quote(f'SELECT ?qid WHERE {{{jstorqid} wdt:P4 {wdqid}}}')
        ).json()
        secondary_qid = resp['results']['bindings'][0]['qid']['value'].split('/')[-1] if resp['results']['bindings'] else None
        return f'{secondary_ns}:{secondary_qid}' if secondary_qid else None

    def _merge(self, primary, secondary=None):
        def _norm(v):
            return set([json.dumps(d, sort_keys=True) for d in v]) if isinstance(v, list) else json.dumps(v, sort_keys=True)

        merged = deepcopy(primary)
        if secondary:
            for k, v in secondary.items():
                if k in merged:
                    if isinstance(merged[k], list):
                        mv = _norm(merged[k])
                        for sv in v:
                            if not _norm(sv) in mv:
                                merged[k].append(sv)
                else:
                    merged[k] = deepcopy(v)
            merged['id']['alt'] = secondary['id']['id']
        if '@type' in merged:
            merged['type'] = merged.pop('@type')
        if 'described at URL' in merged:
            del merged['described at URL']
        if 'coords' in merged:
            coords = []
            for cs in merged['coords']:
                coords.append([float(c) for c in cs.replace('Point(','').replace(')','').split()])
            merged['coords'] = coords

        return merged

    def _add_summary_text(self, entity):
        if 'wikipedia_page' in entity:
            resp = requests.get(f'https://en.wikipedia.org/api/rest_v1/page/summary/{entity["wikipedia_page"].split("/")[-1]}')
            entity['wikipedia_summary'] = resp.json()
        return entity

def as_html(entity):
    return open('viewer.html', 'r').read().replace("'{{DATA}}'", json.dumps(entity))

def usage():
    print('%s [hl:e:s:f:] eid' % sys.argv[0])
    print('   -h --help          Print help message')
    print('   -l --loglevel      Logging level (default=warning)')
    print('   -e --language      Language (default="en")')
    print('   -f --format        Format (json, html) (default=json)')

if __name__ == '__main__':
    logger.setLevel(logging.WARNING)
    kwargs = {}
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], 'hl:e:f:r', ['help', 'loglevel', 'language', 'format'])
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
        elif o in ('-e', '--language'):
            kwargs['language'] = a
        elif o in ('-f', '--format'):
            kwargs['content_type'] = 'text/html' if a == 'html' else 'application/json'
        elif o in ('-h', '--help'):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    kg = KnowledgeGraph(**kwargs)

    if args:
        out = kg.entity(args[0], **kwargs)
    else:
        usage()
        sys.exit()

    fmt = kwargs.get('content_type', 'application/json') 
    print(as_html(out) if 'html' in fmt else json.dumps(out))
