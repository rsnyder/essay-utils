import logging
logger = logging.getLogger()
logger.setLevel(logging.WARNING)

import json
import os

from entity import KnowledgeGraph
from essay_utils import EssayUtils, Essay, mw_to_html5, add_vue_app

cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Credentials': True
}

def _lambda_args(event, body_key=None, multiValue_qargs=False, normalize_keys=True):
    args = event['multiValueQueryStringParameters'] if multiValue_qargs else event['queryStringParameters']
    if args is None:
        args = {}
    body = json.loads(event['body']) if event['body'] else {}
    if body_key:
        args[body_key] = body
    else:
        args.update(body)
    if normalize_keys:
        args = dict([(k.lower(),v) for k,v in args.items()])
    if 'log' in args:
        level = args.pop('log')[0].lower() if multiValue_qargs else args.pop('log').lower()
        if level == 'debug':
            logger.setLevel(logging.DEBUG)
        elif level == 'info':
            logger.setLevel(logging.INFO)
    return args

def get_entity(event, context):
    args = _lambda_args(event)
    qid = event['pathParameters'].get('qid')
    logger.info('get_entity: qid=%s args=%s', qid, args)
    entity = KnowledgeGraph(**args).entity(qid, **args)
    return {'statusCode': 200, 'headers': cors_headers, 'body': json.dumps(entity)}

def get_essay(event, context):
    args = _lambda_args(event)
    title = event['pathParameters'].get('title')
    logger.info(f'get_essay: title="{title}" args={args}')
    client = EssayUtils(**args)
    page_data = client.page(title, **args)
    page_data['html'] = mw_to_html5(page_data['html'])
    essay = Essay(**page_data)
    essay = add_vue_app(essay.html)
    logger.error(essay)
    headers = {'Content-Type': 'text/html'}
    headers.update(cors_headers)
    return {'statusCode': 200, 'headers': headers, 'body': essay}
