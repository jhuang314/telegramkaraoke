from PIL import Image, ImageDraw, ImageFont

import boto3
from dotenv import load_dotenv

import json
import io
import os
import textwrap
import time

load_dotenv()

FILEBASE_ACCESS_KEY = os.getenv('FILEBASE_ACCESS_KEY') or ''
FILEBASE_SECRET_ACCESS_KEY = os.getenv('FILEBASE_SECRET_ACCESS_KEY') or ''
BASE_IMAGE = 'karaokebackgroundnft.jpg'
FILEBASE_ENDPOINT = 'https://s3.filebase.com'
BUCKET_NAME='telegram-karaoke'

s3 = boto3.client('s3',
	endpoint_url=FILEBASE_ENDPOINT,
	aws_access_key_id=FILEBASE_ACCESS_KEY,
	aws_secret_access_key=FILEBASE_SECRET_ACCESS_KEY)

font = ImageFont.truetype('FreeMono.ttf', 200)
TEXT_COLOR=(255, 153, 18)


IMG_MAP = {
    'Joy to the world': 'joytotheworld.jpg',
    'Silent Night': 'silentnight.jpg',
    'Jingle Bells': 'jinglebells.jpg',
    'Jingle Bells (chorus)': 'jinglebells.jpg',
    'I want it that way': 'iwantitthatway.jpg',
}


def generate_nft_image(score, song_title, save_to_disk=False):
    base_image = IMG_MAP.get(song_title, BASE_IMAGE)
    img = Image.open(base_image)

    draw = ImageDraw.Draw(img)

    # text wrap the image so title can overflow
    offset = 212
    for line in textwrap.wrap(song_title, width=13):
        draw.text((212, offset), line, font=font, fill=TEXT_COLOR, stroke_width=7)

        left, top, right, bottom = font.getbbox(line)
        width = right - left
        height = bottom - top

        offset += height + 100


    draw.text(
        (212, 1812),
        f"Score: {score}",
        font=font,
        fill=TEXT_COLOR,
        stroke_width=7,
    )

    if save_to_disk:
        timestamp = time.strftime("%Y%m%d%H%M%S")
        filename = f'images/nft_{timestamp}.jpg'
        img.save(filename)

    in_mem_file = io.BytesIO()
    img.save(in_mem_file, format=img.format)
    in_mem_file.seek(0)

    return in_mem_file

def create_upload_nft(score, song_id):
    """
    Returns the json metadata CID after uploading image and metadata to Filebase.
    """
    data = generate_nft_image(score, song_id)
    timestamp = time.strftime("%Y%m%d%H%M%S")
    filename = f'images/nft_{timestamp}.jpg'

    response = s3.put_object(Body=data, Bucket=BUCKET_NAME, Key=filename)

    headers = response['ResponseMetadata']['HTTPHeaders']
    image_cid = headers['x-amz-meta-cid']
    image_url = f'ipfs://{image_cid}'

    nft_json = {
        'name': 'Karaoke Token NFT',
        'description': 'Telegram Karaoke Game NFT Collection',
        'image': image_url,
        'type': 'image/jpg',
        'attributes': [
            {
                'trait_type': 'Score',
                'value': score,
            },
            {
                'trait_type': 'Song',
                'value': song_id,
            },
            {
                'trait_type': 'Timestamp',
                'value': timestamp,
            },
        ]
    }

    nft_json_filename = f'json/nft_{timestamp}.json'


    nft_json_str = json.dumps(nft_json)
    response = s3.put_object(Body=nft_json_str.encode('utf-8'), Bucket=BUCKET_NAME, Key=nft_json_filename)



    headers = response['ResponseMetadata']['HTTPHeaders']
    json_cid = headers['x-amz-meta-cid']

    return json_cid

#create_upload_nft(12345, 'song title')
#generate_nft_image(123456, 'I want it that way', save_to_disk=True)
