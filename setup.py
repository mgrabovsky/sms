import sqlite3


def main():
    '''
    Main script entry point. Creates a SQLite3 database sms.db in the current
    directory and prepares the database structure.
    '''
    db = sqlite3.connect('sms.db')
    cur = db.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS `sms_hashes` (
        `url` TEXT NOT NULL,
        `hash` BLOB NULL,
        `old_text` BLOB NULL
    )''')
    db.commit()
    db.close()


if __name__ == '__main__':
    main()
else:
    raise NotImplementedError
