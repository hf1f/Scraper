import requests
from bs4 import BeautifulSoup
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import os

BASE_URL = "http://books.toscrape.com/catalogue/"
JSON_FILE = "books_detailed_data.json"
lock = threading.Lock()

def parse_rating(rating_classes):
    """Convert text rating to integer."""
    rating_dict = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
    for r_class in rating_classes:
        if r_class in rating_dict:
            return rating_dict[r_class]
    return 0

def save_to_json(book_data):
    """Thread-safe function to append data to JSON file."""
    with lock:
        data_list = []
        # If file exists and not empty, load current data
        if os.path.exists(JSON_FILE) and os.path.getsize(JSON_FILE) > 0:
            try:
                with open(JSON_FILE, 'r', encoding='utf-8') as f:
                    data_list = json.load(f)
            except json.JSONDecodeError:
                data_list = []
        
        # Append new book data
        data_list.append(book_data)
        
        # Save back to file
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=4)

def scrape_book_details(book_url):
    """Scrape detailed info from a single book page."""
    try:
        response = requests.get(book_url, timeout=10)
        if response.status_code != 200:
            return
        
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Scrape Title
        main_div = soup.find('div', class_='product_main')
        title = main_div.find('h1').text.strip()
        
        # Scrape Price (Clean currency symbols)
        price_text = main_div.find('p', class_='price_color').text.strip()
        price = ''.join(c for c in price_text if c.isdigit() or c == '.')
        
        # Scrape Rating
        rating_p = main_div.find('p', class_='star-rating')
        rating = parse_rating(rating_p['class']) if rating_p else 0
        
        # Scrape Category
        breadcrumb = soup.find('ul', class_='breadcrumb')
        category = breadcrumb.find_all('li')[2].find('a').text.strip() if breadcrumb else "Unknown"
        
        # Scrape Description
        desc_p = soup.find('div', id='product_description')
        description = desc_p.find_next_sibling('p').text.strip() if desc_p else ""
        
        # Scrape Specifications Table (ISBN, Stock, Reviews)
        table = soup.find('table', class_='table table-striped')
        table_data = {}
        if table:
            for row in table.find_all('tr'):
                header = row.find('th').text.strip()
                value = row.find('td').text.strip()
                table_data[header] = value
                
        isbn = table_data.get("UPC", "")
        
        # Clean Stock values
        stock_text = table_data.get("Availability", "")
        stock = ''.join(c for c in stock_text if c.isdigit())
        stock = int(stock) if stock else 0
        
        reviews = table_data.get("Number of reviews", "0")
        
        # Prepare book dictionary
        book_data = {
            "title": title,
            "price": price,
            "rating": rating,
            "category": category,
            "stock": stock,
            "reviews": int(reviews) if reviews.isdigit() else 0,
            "isbn": isbn,
            "description": description
        }
        
        # Save to JSON
        save_to_json(book_data)
        print(f"Scraped: {title[:30]}...")
                
    except Exception as e:
        print(f"Error scraping book {book_url}: {e}")

def scrape_page(page_number):
    """Get all book links from a list page."""
    page_url = f"http://books.toscrape.com/catalogue/page-{page_number}.html"
    print(f"\n--- Checking Page {page_number} ---")
    
    try:
        response = requests.get(page_url, timeout=10)
        if response.status_code != 200:
            return False
            
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('article', class_='product_pod')
        
        if not articles:
            return False
            
        book_urls = []
        for article in articles:
            href = article.find('h3').find('a')['href']
            full_url = "http://books.toscrape.com/" + href.replace("../", "") if "catalogue/" in href else BASE_URL + href.replace("../", "")
            book_urls.append(full_url)
            
        # Multi-threading for fast processing
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(scrape_book_details, book_urls)
            
        return True
    except Exception as e:
        print(f"Error on page {page_number}: {e}")
        return False

if __name__ == "__main__":
    print("Starting deep web scraper...")
    
    # Reset file if it exists from previous runs
    if os.path.exists(JSON_FILE):
        os.remove(JSON_FILE)
        
    current_page = 1
    while True:
        has_next = scrape_page(current_page)
        if not has_next or current_page > 50:
            break
        current_page += 1
        
    print(f"\nDone! Data saved to: {JSON_FILE}")