from bs4 import BeautifulSoup
import boto3
import json
import os
import urllib3

S3_BUCKET = os.getenv('S3_BUCKET', None)
S3_CACHE_FILE = os.getenv('S3_CACHE_FILE', None)
SES_REGION = os.getenv('SES_REGION', None)
SES_EMAIL_FROM = os.getenv('SES_EMAIL_FROM', None)
SES_EMAIL_TO = os.getenv('SES_EMAIL_TO', None)
QUERIES = os.getenv('QUERIES', None)

URL_ROOT = 'https://vend.se/'

def search_and_email(seen_ads, query, ses):
    query_parameters = {
        'q' : query,
        'order' : 'dated',
        'type' : 'sell'
    }

    http = urllib3.PoolManager()
    response = http.request('GET', URL_ROOT, fields=query_parameters)
    soup = BeautifulSoup(response.data, 'html.parser')

    ads = soup.find_all('li', class_='t')
    new_ads = []
    for ad in ads:
        url = URL_ROOT + ad.a['href']
        if url not in seen_ads:
            title = ad.a.contents[0]
            ses.send_email(
                Source=SES_EMAIL_FROM,
                Destination={'ToAddresses': [SES_EMAIL_TO]},
                Message={
                    'Subject': {'Data': title},
                    'Body': {'Text': {'Data': url}}
                }
            )

            new_ads.append(url)
    return new_ads

def search(event, context):
    ses = boto3.client('ses', region_name=SES_REGION)
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_BUCKET)
    objects = list(bucket.objects.filter(Prefix=S3_CACHE_FILE))

    seen_ads = []
    if len(objects) > 0 and objects[0].key == S3_CACHE_FILE:
        seen_ads = json.loads(objects[0].get()['Body'].read().decode('utf-8'))
    previously_seen_ads = len(seen_ads)

    for query in QUERIES.split(','):
        seen_ads.extend(search_and_email(seen_ads, query, ses))

    if len(seen_ads) > previously_seen_ads:
        bucket.put_object(Key=S3_CACHE_FILE, Body=json.dumps(seen_ads).encode('utf-8'))

    return { 
        'new_ads' : len(seen_ads) - previously_seen_ads
    }
