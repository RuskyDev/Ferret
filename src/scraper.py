import requests
import re
import phonenumbers
import json
import threading
import queue
import argparse
import time
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from pathlib import Path
from fake_useragent import UserAgent

ua = UserAgent()

def load_data(file_path):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return {
        "phone_numbers": [],
        "emails": [],
        "page_urls": [],
        "social_media": [],
        "stats": {
            "TOTAL_PAGES_SCRAPED": 0,
            "EXTRACTED_EMAILS": 0,
            "EXTRACTED_PHONE_NUMBERS": 0,
            "TOTAL_SOCIAL_MEDIA_LINKS": 0,
            "TIME_TAKEN_TO_SCRAPE": 0
        }
    }

def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def extract_emails(text, domain):
    pattern = rf"[a-zA-Z0-9._%+-]+@{re.escape(domain)}"
    return set(re.findall(pattern, text))

def extract_phone_numbers(text):
    return {
        phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)
        for match in phonenumbers.PhoneNumberMatcher(text, "US")
        if phonenumbers.is_valid_number(match.number)
    }

def is_valid_internal_link(link, base_domain):
    parsed_link = urlparse(link)
    link_domain = parsed_link.netloc.replace("www.", "")
    return (
        link_domain == base_domain
        and not parsed_link.path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.pdf', '.docx', '.zip', '.mp4', '.mp3', '.webp', '.webm'))
        and not any(char in link for char in ['#', '?', '&'])
    )

def clean_url(url):
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

def extract_social_links(soup, existing_links):
    valid_social_links = {
        "instagram": r"^https://www\.instagram\.com/([a-z0-9._%+-]+)/?$",
        "linkedin": r"^https://www\.linkedin\.com/(company|in)/([a-z0-9._%+-]+)/?$",
        "pinterest": r"^https://www\.pinterest\.com/([a-z0-9._%+-]+)/?$",
        "youtube_c": r"^https://www\.youtube\.com/c/([a-zA-Z0-9._%+-]+)/?$",
        "youtube_at": r"^https://www\.youtube\.com/@([a-zA-Z0-9._%+-]+)/?$",
        "twitter": r"^https://(www\.)?twitter\.com/([a-zA-Z0-9._%+-]+)/?$",
        "facebook": r"^https://www\.facebook\.com/([a-zA-Z0-9._%+-]+)/?$"
    }

    social_links = {}

    for link in soup.find_all("a", href=True):
        url = clean_url(link["href"].strip())
        for platform, pattern in valid_social_links.items():
            if re.match(pattern, url) and url not in existing_links:
                if platform.startswith("youtube_"):
                    social_links["youtube"] = url
                else:
                    social_links[platform] = url

    ordered_links = [
        social_links.get("instagram"),
        social_links.get("linkedin"),
        social_links.get("pinterest"),
        social_links.get("youtube"),
        social_links.get("twitter"),
        social_links.get("facebook")
    ]

    return [link for link in ordered_links if link and link not in existing_links]

def crawl_page(url, base_domain, data, file_path, lock, url_queue):
    headers = {"User-Agent": ua.random}
    
    try:
        response = requests.get(url, timeout=5, headers=headers)
        if response.status_code != 200:
            return
        
        soup = BeautifulSoup(response.text, "html.parser")
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

        new_emails = extract_emails(response.text, base_domain) - set(data["emails"])
        new_phones = extract_phone_numbers(response.text) - set(data["phone_numbers"])
        new_social_links = extract_social_links(soup, data["social_media"])

        with lock:
            if url not in data["page_urls"] and is_valid_internal_link(url, base_domain):
                data["page_urls"].append(url)
                data["stats"]["TOTAL_PAGES_SCRAPED"] += 1
                save_data(file_path, data)

            if new_emails:
                data["emails"].extend(new_emails)
                data["stats"]["EXTRACTED_EMAILS"] += len(new_emails)
                save_data(file_path, data)

            if new_phones:
                data["phone_numbers"].extend(new_phones)
                data["stats"]["EXTRACTED_PHONE_NUMBERS"] += len(new_phones)
                save_data(file_path, data)

            if new_social_links:
                data["social_media"].extend(new_social_links)
                data["stats"]["TOTAL_SOCIAL_MEDIA_LINKS"] += len(new_social_links)
                save_data(file_path, data)

        for link in soup.find_all("a", href=True):
            full_link = urljoin(base_url, link["href"])
            if is_valid_internal_link(full_link, base_domain):
                url_queue.put(full_link)

    except requests.RequestException:
        return

def scan_website(url):
    start_time = time.time()
    
    parsed_url = urlparse(url)
    base_domain = parsed_url.netloc.replace("www.", "")
    file_path = Path(f"{base_domain}.json")
    data = load_data(file_path)

    visited_urls = set()
    lock = threading.Lock()
    url_queue = queue.Queue()
    url_queue.put(url)

    def worker():
        while True:
            try:
                current_url = url_queue.get(timeout=5)
            except queue.Empty:
                break

            with lock:
                if current_url in visited_urls:
                    url_queue.task_done()
                    continue
                visited_urls.add(current_url)

            crawl_page(current_url, base_domain, data, file_path, lock, url_queue)
            url_queue.task_done()

    with ThreadPoolExecutor(10) as executor:
        for _ in range(10):
            executor.submit(worker)

        url_queue.join()
    
    data["stats"]["TIME_TAKEN_TO_SCRAPE"] = round(time.time() - start_time, 2)
    save_data(file_path, data)

def main():
    parser = argparse.ArgumentParser(description="Web scraper for emails, phone numbers, and social media links.")
    parser.add_argument("--website-url", required=True, help="The website URL to scrape.")

    args = parser.parse_args()
    scan_website(args.website_url)

if __name__ == "__main__":
    main()
