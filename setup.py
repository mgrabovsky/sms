import sqlite3

if __name__ == '__main__':
    db = sqlite3.connect('sms.db')
    cur = db.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS `sms_hashes` (
        `url` TEXT NOT NULL,
        `hashes` BLOB NULL
    )''')
    db.commit()
    db.close()

