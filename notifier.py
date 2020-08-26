#!/usr/bin/env python3
import argparse
import difflib
from email.mime.text import MIMEText
from email.header import Header
import hashlib
import json
import logging
from smtplib import SMTP
import sqlite3
import sys
import time
from typing import Any, Iterator, List
import urllib.request


def is_modified(blob: bytes, checksum: str) -> bool:
    return generate_hash(blob) == checksum


def diff_bytes(old: List[bytes], new: List[bytes]) -> Iterator[bytes]:
    return difflib.diff_bytes(difflib.unified_diff, old, new, b'before',
                              b'after')


def fetch_page(url: str) -> bytes:
    return urllib.request.urlopen(url).read()


def generate_hash(blob: bytes) -> str:
    h = hashlib.new('sha1')
    h.update(blob)
    return h.hexdigest()


def load_configuration(config_file: str) -> Any:
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except OSError:
        return None

    return config


def send_mail(from_addr: str, to_addr: str, subject: str, body: str) -> None:
    msg            = MIMEText(body, _charset='utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From']    = from_addr
    msg['To']      = to_addr
    msg.set_charset('utf-8')

    smtp = SMTP('localhost')
    smtp.send_message(msg)
    smtp.quit()


def main():
    # Load user configuration
    # FIXME: Graceful error handling
    config = load_configuration('config.json')
    if config is None:
        print('Error: Could not load config file', file=sys.stderr)
        sys.exit(1)
    if not isinstance(config, dict):
        print('Error: Config file is not valid. The top-level structure'
              'must be a dictionary',
              file=sys.stderr)
        sys.exit(1)

    from_addr     = config['from']
    to_addr       = config['to']
    msg_subject   = config['subject']
    msg_body      = config['body']
    watched_pages = config['pages']

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(
        datefmt='%H:%M:%S',
        format='[%(asctime)s] %(levelname)s - %(message)s',
        level=logging.DEBUG if args.verbose else logging.INFO
    )
    logger = logging.getLogger()

    db = sqlite3.connect('sms.db')

    for page in watched_pages:
        logger.info('Downloading %s ...', page['url'])
        # FIXME: Handle errors gracefully
        contents = fetch_page(page['url'])
        new_hash = generate_hash(contents)

        cur = db.cursor()
        cur.execute('SELECT `hash`, `old_text` FROM `sms_hashes` WHERE '
                    '`url`=?',
                    (page['url'],))
        res = cur.fetchone()

        # Create a record for the page if it hasn't been scraped yet
        if not res or not res[0]:
            logger.debug('New page, saving...')
            cur.execute('INSERT INTO `sms_hashes` (`url`, `hash`, '
                        '`old_text`) VALUES(?, ?, ?)',
                        (page['url'], new_hash, contents))
            db.commit()
            logger.debug('Done')
            continue

        # Check if the page has changed
        old_hash = res[0]
        if is_modified(contents, old_hash):
            logger.debug('Page not modified, done')
            continue

        # Update the database first
        cur.execute('UPDATE `sms_hashes` SET `hash`=?, `old_text`=? '
                    'WHERE `url`=?',
                    (new_hash, contents, page['url']))
        db.commit()

        # Compile and send the message
        logger.debug('Page modified, sending email...')
        subject  = msg_subject.format(page)
        body     = msg_body.format(page)
        body    += '\n\n'
        oldlines = '' if res[1] is None else res[1].splitlines()
        newlines = contents.splitlines()

        body_lines = diff_bytes(oldlines, newlines)
        body      += b'\n'.join(body_lines).decode('utf8')

        #send_mail(from_addr, to_addr, subject, body)

        logger.debug('Done')
        time.sleep(0.5)

    db.close()


if __name__ == '__main__':
    main()
else:
    raise NotImplementedError
