#!/usr/bin/env python3
import hashlib
import json
import urllib.request
from email.header import Header
from email.mime.text import MIMEText
from smtplib import SMTP
from typing import Any


def is_modified(blob: bytes, checksum: str) -> bool:
    """
    Compare a byte string to a hash to check if it was modified since
    the hash was generated.
    """
    return generate_hash(blob) != checksum


def fetch_page(url: str) -> bytes:
    """
    Download webpage from the specified URL.
    """
    with urllib.request.urlopen(url) as response:
        contents = response.read()
    return contents


def generate_hash(blob: bytes) -> str:
    """
    Generate the SHA-1 hash of a byte string.
    """
    h = hashlib.new("sha1")
    h.update(blob)
    return h.hexdigest()


def load_configuration(config_file: str) -> dict[str, Any] | None:
    """
    Load configuration settings from the given file.
    """
    try:
        with open(config_file, encoding="utf-8") as f:
            config = json.load(f)
    except OSError:
        return None

    return config


def notify(config: dict[str, Any], message: str, page: dict[str, Any]) -> None:
    """
    Trigger a notification that the given page has changed, including
    the specified diff between versions.
    """
    email_config = config["notifiers"]["email"]
    from_addr = email_config["from"]
    to_addr = email_config["to"]
    msg_subject = email_config["subject"]
    msg_body = email_config["body"]

    subject = msg_subject.format(page)
    body = msg_body.format(page)
    body += f"\n\n{message}"

    send_mail(from_addr, to_addr, subject, body)


def send_mail(from_addr: str, to_addr: str, subject: str, body: str) -> None:
    """
    Send an email message with the specified parameters via the STMP
    server at localhost.
    """
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_charset("utf-8")

    smtp = SMTP("localhost")
    smtp.send_message(msg)
    smtp.quit()
