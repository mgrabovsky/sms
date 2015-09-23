#!/usr/bin/env python3
'''
Database layout:

    CREATE TABLE IF NOT EXISTS `sms_hashes` (
        `url` TEXT NOT NULL,
        `hashes` BLOB NULL
    )

Usage:

1.  Add `@daily ~/sms-notifier.py` to your crontab.
    Customize to your needs.
'''
import hashlib, json, smtplib, sqlite3, time
import anyconfig, requests
from email.mime.text import MIMEText

# Configuration
config        = anyconfig.load('sms-config.json')
from_addr     = config['from']
to_addr       = config['to']
msg_subject   = config['subject']
msg_body      = config['body']
watched_pages = config['pages']
hash_algos    = config['hash_algos']

def fetch_page(url):
    r = requests.get(url)
    return r.text

def generate_hashes(hash_algos, blob):
    hashes = {}
    for algo in hash_algos:
        h = hashlib.new(algo)
        h.update(blob.encode('utf8'))
        hashes[algo] = h.hexdigest()
    return hashes

def check_hashes(hashes, blob):
    for algo, digest in hashes.items():
        h = hashlib.new(algo)
        h.update(blob.encode('utf8'))
        if h.hexdigest() != digest:
            return False
    return True

def send_mail(from_addr, to_addr, subject, body):
    msg            = MIMEText(body)
    msg['Subject'] = subject
    msg['From']    = from_addr
    msg['To']      = to_addr

    smtp = smtplib.SMTP('localhost')
    smtp.sendmail(msg['From'], [msg['To']], msg.as_string())
    smtp.quit()

if __name__ == '__main__':
    db = sqlite3.connect('sms.db')

    for page in watched_pages:
        contents = fetch_page(page['url'])
        new_hashes = generate_hashes(hash_algos, contents)

        cur = db.cursor()
        cur.execute('SELECT `hashes` FROM `sms_hashes` WHERE `url`=?',
                (page['url'],))
        res = cur.fetchone()

        # Create a record for the page if it hasn't been scraped yet
        if not res or not res[0]:
            print('New page')
            cur.execute('INSERT INTO `sms_hashes` (`url`, `hashes`) VALUES(?, ?)',
                    (page['url'], json.dumps(new_hashes)))
            db.commit()
            continue

        # Check if the page has changed
        old_hashes = json.loads(res[0])
        if check_hashes(old_hashes, contents):
            print('Page hasn\'t changed')
            continue

        # Update the database first
        cur.execute('UPDATE `sms_hashes` SET `hashes`=? WHERE `url`=?',
                (json.dumps(new_hashes), page['url']))
        db.commit()

        # Send the message
        subject = msg_subject.format(page)
        body    = msg_body.format(page)
        send_mail(from_addr, to_addr, subject, body)
        print('Sent email')

        time.sleep(0.5)

    db.close()

