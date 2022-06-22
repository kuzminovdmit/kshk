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

    def get_comment_for_stream(self, stream: dict) -> dict:
        comment_author_id = 'UCQNehrkIUBjkRkgfmgzS2dw'

        try:
            response = self.client.commentThreads().list(
                part='snippet',
                videoId=stream['youtube_id']
            ).execute()

            for item in response['items']:
                if item['snippet']['topLevelComment']['snippet']['authorChannelId']['value'] == comment_author_id:
                    stream['comment'] = item['snippet']['topLevelComment']['snippet']['textDisplay']
                    logger.info(f'Timecodes for %s added', stream['stream_name'])
        except googleapiclient.errors.HttpError as e:
            stream['comment'] = ''

        return stream

    def get_streams_from_playlist(self, playlist_id: str) -> list[dict]:
        """
        Return list of streams from YouTube playlist by its id, assembled in
        dictionary with "youtube_id", "stream_name", "stream_date", "thumbnail_url"
        and "comment" fields.
        """
        processed_results = []

        response = self.client.playlistItems().list(
            part='snippet', maxResults=50, playlistId=playlist_id
        ).execute()
        logger.info('Make first playlistItems.list request')

        total_results = response['pageInfo']['totalResults']
        unprocessed_data_count = total_results
        logger.info('Get %s of total %s results', len(response['items'], unprocessed_data_count))

        processed_data = self.process_response(response['items'])
        processed_results += processed_data
        unprocessed_data_count -= len(processed_data)

        if unprocessed_data_count:
            next_page_token = response['nextPageToken']

        while unprocessed_data_count:
            response = self.client.playlistItems().list(
                part='snippet', maxResults=50,
                playlistId=playlist_id, pageToken=next_page_token
            ).execute()
            logger.info('Get next %s of %s results remaining', len(response['items'], unprocessed_data_count))

            processed_data = self.process_response(response['items'])
            processed_results += processed_data
            unprocessed_data_count -= len(processed_data)

            if unprocessed_data_count:
                next_page_token = response['nextPageToken']

        try:
            assert len(processed_results) == total_results
        except AssertionError:
            logger.warning('Some results were not processed')

        return processed_results
