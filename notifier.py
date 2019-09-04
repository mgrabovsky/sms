#!/usr/bin/env python3
import argparse
from email.mime.text import MIMEText
from email.header import Header
import hashlib
import logging
import smtplib
import sqlite3
import time

import anyconfig
import requests

from diff import diff_strings

# Configuration
config        = anyconfig.load('config.json')
from_addr     = config['from']
to_addr       = config['to']
msg_subject   = config['subject']
msg_body      = config['body']
watched_pages = config['pages']

def fetch_page(url):
    r = requests.get(url)
    return r.text

def generate_hash(blob):
    h = hashlib.new('sha256')
    h.update(blob.encode('utf8'))
    return h.hexdigest()

def check_hash(hash, blob):
    return hash == generate_hash(blob)

def send_mail(from_addr, to_addr, subject, body):
    msg            = MIMEText(body.encode('utf-8'), _charset='utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From']    = from_addr
    msg['To']      = to_addr
    msg.set_charset('utf-8')

    smtp = smtplib.SMTP('localhost')
    smtp.send_message(msg)
    smtp.quit()

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    # Optional diagnostic output to console
    if args.verbose:
        def debug(msg): print(msg)
    else:
        def debug(_): pass

    db = sqlite3.connect('sms.db')

    for page in watched_pages:
        debug('Downloading {} ...'.format(page['url']))
        contents = fetch_page(page['url'])
        new_hash = generate_hash(contents)

        cur = db.cursor()
        cur.execute('SELECT `hash`, `old_text` FROM `sms_hashes` WHERE `url`=?',
                (page['url'],))
        res = cur.fetchone()

        # Create a record for the page if it hasn't been scraped yet
        if not res or not res[0]:
            debug('    New page, saving...')
            cur.execute('INSERT INTO `sms_hashes` (`url`, `hash`, `old_text`) VALUES(?, ?, ?)',
                    (page['url'], new_hash, contents))
            db.commit()
            debug('    Done')
            continue

        # Check if the page has changed
        old_hash = res[0]
        if check_hash(old_hash, contents):
            debug('    Page not modified, done')
            continue

        # Update the database first
        cur.execute('UPDATE `sms_hashes` SET `hash`=?, `old_text`=? WHERE `url`=?',
                (new_hash, contents, page['url']))
        db.commit()

        # Compile and send the message
        debug('    Page modified, sending email...')
        subject  = msg_subject.format(page)
        body     = msg_body.format(page)
        body    += '\n\n'
        oldlines = '' if res[1] is None else res[1].splitlines()
        newlines = contents.splitlines()
        body    += '\n'.join(diff_strings(oldlines, newlines))
        send_mail(from_addr, to_addr, subject, body)

        debug('    Done')
        time.sleep(0.5)

    db.close()

