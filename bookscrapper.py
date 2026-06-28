import requests
from bs4 import BeautifulSoup
import json
import time
import random
import re
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

start_page = 1
end_page = 52
output_filename = "all_books_database.json"

MAX_WORKERS = 12  

all_books_data = []
data_lock = Lock() 
counter = 0

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clean_price(price_text):
    if not price_text:
        return ""
    match = re.search(r'[\d\.]+', price_text)
    if match:
        return f"£{match.group(0)}" 
    return price_text.strip()

def scrape_single_page(page_id):
    global counter
    page_url = f"https://books.toscrape.com/catalogue/page-{page_id}.html"
    
    print(f"[-] Thread checking page: {page_id}")
    
    try:
        time.sleep(random.uniform(0.1, 0.3))
        res = requests.get(page_url, headers=headers, timeout=10)
        
        if res.status_code != 200:
            return
            
        soup = BeautifulSoup(res.text, 'lxml')
        books = soup.find_all('article', class_='product_pod')
        
        for book in books:
            title = book.h3.a['title'].strip()
            raw_price = book.find('p', class_='price_color').text
            
            clean_book_price = clean_price(raw_price)
            
            book_object = {
                'page_number': page_id,
                'book_title': title,
                'price': clean_book_price
            }
            
            with data_lock:
                all_books_data.append(book_object)
                counter += 1
                print(f"   [SUCCESS] Caught Book #{counter}: {title} | {clean_book_price}")
                
                if counter % 20 == 0:
                    with open(output_filename, "w", encoding="utf-8") as json_file:
                        json.dump(all_books_data, json_file, ensure_ascii=False, indent=4)
                    print(f"\n======> AUTO-SAVE TRIGGERED! {len(all_books_data)} books secured on disk! <======\n")

    except Exception as e:
        return

if __name__ == "__main__":
    print(f"Launching Multi-Threaded Books Scraper with {MAX_WORKERS} threads...")
    page_ids_to_scrape = range(start_page, end_page + 1)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(scrape_single_page, page_ids_to_scrape)

    print("\nExecuting final database save...")
    with open(output_filename, "w", encoding="utf-8") as json_file:
        json.dump(all_books_data, json_file, ensure_ascii=False, indent=4)
    print(f" DONE! 50 pages processed. Clean books database is ready.")