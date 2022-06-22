import datetime
import json
import logging

import googleapiclient.discovery
import googleapiclient.errors
from oauth2client import client, tools
from oauth2client.file import Storage


logger = logging.getLogger(__name__)


class Parser:
    def __init__(self):
        self.client = self.auth()

    @staticmethod
    def auth() -> googleapiclient.discovery.Resource:
        store = Storage('credentials.json')
        credentials = store.get()

        if not credentials or credentials.invalid:
            logger.info('credentials.json doesn\'t exist, trying to authenticate in browser')
            flow = client.flow_from_clientsecrets(
                'client_secret_file.json',
                [
                    'https://www.googleapis.com/auth/youtube.readonly',
                    'https://www.googleapis.com/auth/youtube.force-ssl'
                ]
            )
            credentials = tools.run_flow(flow, store)

        logger.info('Successfully retrieved credentials')

        return googleapiclient.discovery.build(
            'youtube', 'v3', credentials=credentials
        )

    @staticmethod
    def to_json(data: list[dict], filename: str = ''):
        if not filename:
            logger.warning('No filename was provided, using datestamp as filename')
            filename = f'{datetime.datetime.today().date()}.json'

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        logger.info('Successfully wrote data to %s', filename)

    @staticmethod
    def read_json(filename: str) -> list[dict]:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except IOError as e:
            logger.error(e)
            data = []

        logger.info('Successfully read data from %s', filename)

        return data

    @staticmethod
    def process_response(items: list[dict]) -> list[dict]:
        processed_results = []

        for item in items:
            result = {
                'youtube_id': item['snippet']['resourceId']['videoId'],
                'stream_name': item['snippet']['title'],
                'stream_date': item['snippet']['title'][-8:],
                'thumbnail_url': item['snippet']['thumbnails']['high']['url']
            }
            logger.info('Processed %s', result['stream_name'])
            processed_results.append(result)

        return processed_results
