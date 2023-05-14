import argparse
import logging
import sqlite3
import sys
import time
from urllib.error import URLError

from sms.notifier import (
    diff_bytes,
    fetch_page,
    generate_hash,
    is_modified,
    load_configuration,
    notify,
)


def main() -> None:
    """
    Main script entry point. Loads configuration from config.json in the
    current directory, checks the specified pages one by one and sends
    email notification for pages that have changes since the last check.
    """
    # Load user configuration
    config = load_configuration("config.json")
    if config is None:
        print("Error: Could not load config file", file=sys.stderr)
        sys.exit(1)
    if not isinstance(config, dict):
        print(
            "Error: Config file is not valid. The top-level structure"
            "must be a dictionary",
            file=sys.stderr,
        )
        sys.exit(1)

    watched_pages = config["pages"]

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        datefmt="%H:%M:%S",
        format="[%(asctime)s] %(levelname)s - %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )
    logger = logging.getLogger()

    db = sqlite3.connect("sms.db")

    for page in watched_pages:
        logger.info("Downloading %s ...", page["url"])
        try:
            contents = fetch_page(page["url"])
        except URLError as exc:
            logger.error("HTTP error occurred: %s", exc)
            continue

        new_hash = generate_hash(contents)

        cur = db.cursor()
        cur.execute(
            "SELECT `hash`, `old_text` FROM `sms_hashes` WHERE " "`url`=?",
            (page["url"],),
        )
        res = cur.fetchone()

        # Create a record for the page if it hasn't been scraped yet
        if not res or not res[0]:
            logger.debug("New page, saving...")
            cur.execute(
                "INSERT INTO `sms_hashes` (`url`, `hash`, "
                "`old_text`) VALUES(?, ?, ?)",
                (page["url"], new_hash, contents),
            )
            db.commit()
            logger.debug("Page saved")
            continue

        # Check if the page has changed
        old_hash = res[0]
        if is_modified(contents, old_hash):
            logger.info("Page not modified")
            continue

        # Update the database first
        cur.execute(
            "UPDATE `sms_hashes` SET `hash` = ?, `old_text` = ? WHERE `url` = ?",
            (new_hash, contents, page["url"]),
        )
        db.commit()

        # Compile and send the message
        oldlines = [b""] if res[1] is None else res[1].splitlines()
        newlines = contents.splitlines()

        logger.debug("Page modified, sending notification...")
        notify(config, diff_bytes(oldlines, newlines), page)

        logger.debug("Notification sent")
        time.sleep(0.5)

    db.close()
    logger.info("All pages checked")


if __name__ == "__main__":
    main()
