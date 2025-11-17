import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import ssl
import re
import json
import time
import sys
import os
import random
from datetime import datetime

class AdvancedAmazonScraper:
    def __init__(self):
        self.session = self._create_session()
        self.retry_count = 3
        self.delay_between_requests = 2
        
    def _create_session(self):
        # Create SSL context to bypass certificate verification
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create cookie jar and opener
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar),
            urllib.request.HTTPSHandler(context=ssl_context)
        )
        
        return opener

    def _get_headers(self):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0"
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        return headers

    def _make_request(self, url, retry=0):
        try:
            headers = self._get_headers()
            request = urllib.request.Request(url, headers=headers)
            
            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))
            
            response = self.session.open(request, timeout=10)
            content = response.read()
            
            # Try to decode content
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return content.decode('latin-1')
                except:
                    return content.decode('utf-8', errors='ignore')
                    
        except urllib.error.HTTPError as e:
            if e.code == 503 and retry < self.retry_count:
                print(f"\033[93mServer busy, retrying... ({retry + 1}/{self.retry_count})\033[0m")
                time.sleep(self.delay_between_requests * (retry + 1))
                return self._make_request(url, retry + 1)
            else:
                raise e
        except Exception as e:
            if retry < self.retry_count:
                print(f"\033[93mRequest failed, retrying... ({retry + 1}/{self.retry_count})\033[0m")
                time.sleep(self.delay_between_requests * (retry + 1))
                return self._make_request(url, retry + 1)
            else:
                raise e

    def extract_product_info(self, html_content):
        product_info = {
            'title': 'N/A',
            'price': 'N/A',
            'original_price': 'N/A',
            'rating': 'N/A',
            'reviews': 'N/A',
            'availability': 'N/A',
            'description': 'N/A',
            'brand': 'N/A',
            'images': [],
            'features': [],
            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            # Method 1: Extract from JSON-LD structured data
            json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
            json_ld_matches = re.findall(json_ld_pattern, html_content, re.DOTALL)
            
            for json_ld in json_ld_matches:
                try:
                    data = json.loads(json_ld)
                    if isinstance(data, list):
                        data = data[0]
                    
                    if '@type' in data and data['@type'] in ['Product', 'Offer']:
                        if 'name' in data and product_info['title'] == 'N/A':
                            product_info['title'] = data['name'].strip()
                        if 'brand' in data and product_info['brand'] == 'N/A':
                            brand_data = data['brand']
                            if isinstance(brand_data, dict) and 'name' in brand_data:
                                product_info['brand'] = brand_data['name'].strip()
                            else:
                                product_info['brand'] = str(brand_data).strip()
                        if 'offers' in data and 'price' in data['offers']:
                            product_info['price'] = data['offers']['price']
                        if 'aggregateRating' in data and 'ratingValue' in data['aggregateRating']:
                            product_info['rating'] = data['aggregateRating']['ratingValue']
                        if 'aggregateRating' in data and 'reviewCount' in data['aggregateRating']:
                            product_info['reviews'] = data['aggregateRating']['reviewCount']
                except:
                    continue

            # Method 2: Direct HTML extraction as fallback
            # Title extraction
            if product_info['title'] == 'N/A':
                title_patterns = [
                    r'<span id="productTitle"[^>]*>(.*?)</span>',
                    r'<h1.*?class=".*?title.*?"[^>]*>(.*?)</h1>',
                    r'<meta[^>]*name="title"[^>]*content="([^"]*)"',
                ]
                for pattern in title_patterns:
                    match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
                    if match:
                        product_info['title'] = re.sub(r'<[^>]*>', '', match.group(1)).strip()
                        break

            # Price extraction
            if product_info['price'] == 'N/A':
                price_patterns = [
                    r'<span class="a-price-whole">[^<]*</span><span class="a-price-decimal">\.</span><span class="a-price-fraction">([^<]*)</span>',
                    r'<span[^>]*class="a-price"[^>]*><span[^>]*class="a-offscreen">[^>]*>([^<]*)</span>',
                    r'<span id="priceblock_dealprice"[^>]*>([^<]*)</span>',
                    r'<span id="priceblock_ourprice"[^>]*>([^<]*)</span>',
                    r'<span class="a-price"[^>]*data-a-size="xl"[^>]*><span[^>]*class="a-offscreen">([^<]*)</span>',
                ]
                for pattern in price_patterns:
                    match = re.search(pattern, html_content, re.IGNORECASE)
                    if match:
                        price_text = match.group(1)
                        # Clean price text
                        price_text = re.sub(r'[^\d.,]', '', price_text)
                        product_info['price'] = price_text
                        break

            # Rating extraction
            if product_info['rating'] == 'N/A':
                rating_patterns = [
                    r'<span[^>]*class="a-icon-alt"[^>]*>([\d.]+) out of 5 stars</span>',
                    r'<i[^>]*class="a-icon a-icon-star[^>]*>([\d.]+) out of 5 stars</i>',
                    r'data-hook="rating-out-of-text"[^>]*>([\d.]+) out of 5 stars</span>',
                ]
                for pattern in rating_patterns:
                    match = re.search(pattern, html_content, re.IGNORECASE)
                    if match:
                        product_info['rating'] = match.group(1)
                        break

            # Review count extraction
            if product_info['reviews'] == 'N/A':
                review_patterns = [
                    r'<span[^>]*id="acrCustomerReviewText"[^>]*>([\d,]+) ratings</span>',
                    r'<span[^>]*data-hook="total-review-count"[^>]*>([\d,]+)</span>',
                    r'<a[^>]*href="[^"]*customerReviews"[^>]*>([\d,]+) ratings</a>',
                ]
                for pattern in review_patterns:
                    match = re.search(pattern, html_content, re.IGNORECASE)
                    if match:
                        product_info['reviews'] = match.group(1)
                        break

            # Availability extraction
            availability_patterns = [
                r'<span[^>]*class="a-size-medium a-color-success"[^>]*>([^<]*)</span>',
                r'<div[^>]*id="availability"[^>]*>.*?<span[^>]*>([^<]*)</span>',
                r'<span[^>]*class="a-color-price"[^>]*>([^<]*)</span>',
            ]
            for pattern in availability_patterns:
                match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
                if match:
                    availability_text = re.sub(r'<[^>]*>', '', match.group(1)).strip()
                    if availability_text and 'stock' in availability_text.lower():
                        product_info['availability'] = availability_text
                        break

            # Description extraction
            desc_patterns = [
                r'<div[^>]*id="productDescription"[^>]*>.*?<p>(.*?)</p>',
                r'<div[^>]*id="feature-bullets"[^>]*>(.*?)</div>',
                r'<div[^>]*class="product-description"[^>]*>(.*?)</div>',
            ]
            for pattern in desc_patterns:
                match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
                if match:
                    desc_text = re.sub(r'<[^>]*>', '', match.group(1)).strip()
                    if desc_text:
                        product_info['description'] = desc_text[:300] + "..." if len(desc_text) > 300 else desc_text
                        break

            # Features extraction
            features_pattern = r'<span class="a-list-item">(.*?)</span>'
            features_matches = re.findall(features_pattern, html_content, re.DOTALL)
            for feature in features_matches[:5]:  # Get first 5 features
                feature_text = re.sub(r'<[^>]*>', '', feature).strip()
                if feature_text and len(feature_text) > 10:
                    product_info['features'].append(feature_text)

        except Exception as e:
            print(f"\033[91mError parsing product info: {str(e)}\033[0m")

        return product_info

    def scrape_product(self, url):
        try:
            if not url.startswith('https://'):
                url = 'https://' + url
            
            print(f"\033[94mScraping: {url}\033[0m")
            html_content = self._make_request(url)
            
            if html_content:
                return self.extract_product_info(html_content)
            else:
                return None
                
        except Exception as e:
            print(f"\033[91mScraping failed: {str(e)}\033[0m")
            return None

def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = """
    \033[92m
    ██████╗ ██████╗ ██╗  ██╗███████╗██╗    ██╗██████╗ ██████╗ ██╗   ██╗██████╗  █████╗ ██╗
    ██╔════╝██╔═══██╗██║  ██║██╔════╝██║    ██║██╔══██╗██╔══██╗██║   ██║██╔══██╗██╔══██╗██║
    ██║     ██║   ██║███████║█████╗  ██║ █╗ ██║██████╔╝██████╔╝██║   ██║██████╔╝███████║██║
    ██║     ██║   ██║██╔══██║██╔══╝  ██║███╗██║██╔══██╗██╔══██╗██║   ██║██╔══██╗██╔══██║██║
    ╚██████╗╚██████╔╝██║  ██║███████╗╚███╔███╔╝██║  ██║██║  ██║╚██████╔╝██████╔╝██║  ██║███████╗
     ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
    
    \033[96m
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                         AMAZON PRODUCT SCRAPER PRO                          ║
    ║                    Advanced Professional Scraping Tool                     ║
    ║                         Developed by: chowdhuryvai                          ║
    ║                     © 2024 ChowdhuryVai Technologies                       ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    \033[0m
    """
    print(banner)

def print_contact_info():
    info = """
    \033[93m
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                          CONTACT & RESOURCES                                ║
    ╠══════════════════════════════════════════════════════════════════════════════╣
    ║ 🔗 Telegram ID: https://t.me/darkvaiadmin                                   ║
    ║ 📢 Telegram Channel: https://t.me/windowspremiumkey                         ║
    ║ 🌐 Hacking/Cracking Website: https://crackyworld.com/                       ║
    ║ 💼 Professional Tools & Software Solutions                                 ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    \033[0m
    """
    print(info)

def print_menu():
    menu = """
    \033[95m
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                            MAIN MENU                                        ║
    ╠══════════════════════════════════════════════════════════════════════════════╣
    ║  1. 🎯 Scrape Single Product                                                ║
    ║  2. 📊 Scrape Multiple Products                                             ║
    ║  3. 📁 Scrape from URLs File                                                ║
    ║  4. 💾 Save Results to JSON/CSV                                             ║
    ║  5. 📋 View Current Results                                                 ║
    ║  6. 🛠️  Settings & Configuration                                            ║
    ║  7. ❌ Exit                                                                 ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    \033[0m
    """
    print(menu)

def animate_text(text, delay=0.03):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def loading_animation(message, duration=2):
    animation = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    start_time = time.time()
    i = 0
    
    while time.time() - start_time < duration:
        sys.stdout.write(f"\r\033[94m{message} {animation[i % len(animation)]}\033[0m")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    
    sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")
    sys.stdout.flush()

def display_product_info(product, index=None):
    if index:
        print(f"\n\033[95m{'═' * 80}\033[0m")
        print(f"\033[95m📦 PRODUCT {index}\033[0m")
        print(f"\033[95m{'═' * 80}\033[0m")
    
    colors = ['96', '93', '92', '91', '94', '95']
    color_idx = 0
    
    for key, value in product.items():
        if key == 'features' and value:
            print(f"\033[9{colors[color_idx % len(colors)]}m📋 Features:\033[0m")
            for feature in value:
                print(f"   • \033[97m{feature}\033[0m")
        elif key != 'scraped_at':
            icon = "📛" if key == 'title' else "💰" if key == 'price' else "⭐" if key == 'rating' else "👥" if key == 'reviews' else "📦" if key == 'availability' else "📝" if key == 'description' else "🏷️" if key == 'brand' else "🔧"
            print(f"{icon} \033[9{colors[color_idx % len(colors)]}m{key.capitalize()}:\033[0m \033[97m{value}\033[0m")
        color_idx += 1
    
    if 'scraped_at' in product:
        print(f"⏰ \033[90mScraped at: {product['scraped_at']}\033[0m")

def save_results(results, format_type='json'):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format_type == 'json':
        filename = f"amazon_products_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    else:  # CSV
        filename = f"amazon_products_{timestamp}.csv"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Title,Price,Rating,Reviews,Availability,Brand,Scraped_At\n")
            for product in results:
                title = product.get('title', 'N/A').replace(',', ';')
                price = product.get('price', 'N/A')
                rating = product.get('rating', 'N/A')
                reviews = product.get('reviews', 'N/A')
                availability = product.get('availability', 'N/A').replace(',', ';')
                brand = product.get('brand', 'N/A').replace(',', ';')
                scraped_at = product.get('scraped_at', 'N/A')
                f.write(f'"{title}","{price}","{rating}","{reviews}","{availability}","{brand}","{scraped_at}"\n')
    
    return filename

def main():
    scraper = AdvancedAmazonScraper()
    results = []
    
    while True:
        print_banner()
        print_contact_info()
        print_menu()
        
        choice = input("\n\033[96m🎯 Enter your choice (1-7): \033[0m").strip()
        
        if choice == '1':
            url = input("\n\033[93m🔗 Enter Amazon product URL: \033[0m").strip()
            if url:
                loading_animation("Scraping product information", 3)
                product = scraper.scrape_product(url)
                
                if product:
                    results.append(product)
                    print("\n\033[92m✅ PRODUCT SCRAPED SUCCESSFULLY!\033[0m")
                    display_product_info(product)
                else:
                    print("\n\033[91m❌ Failed to scrape product. Please check the URL and try again.\033[0m")
            
            input("\n\033[90mPress Enter to continue...\033[0m")
        
        elif choice == '2':
            urls = []
            print("\n\033[93m🔗 Enter Amazon product URLs (one per line, type 'done' when finished):\033[0m")
            while True:
                url = input().strip()
                if url.lower() == 'done':
                    break
                if url:
                    urls.append(url)
            
            successful_scrapes = 0
            for i, url in enumerate(urls, 1):
                loading_animation(f"Scraping product {i}/{len(urls)}", 2)
                product = scraper.scrape_product(url)
                
                if product:
                    product['url'] = url
                    results.append(product)
                    successful_scrapes += 1
                    print(f"\n\033[92m✅ Product {i} scraped successfully! ({successful_scrapes}/{len(urls)})\033[0m")
                else:
                    print(f"\n\033[91m❌ Failed to scrape product {i}\033[0m")
            
            print(f"\n\033[94m📊 Summary: {successful_scrapes}/{len(urls)} products scraped successfully\033[0m")
            input("\n\033[90mPress Enter to continue...\033[0m")
        
        elif choice == '3':
            filename = input("\n\033[93m📁 Enter filename with URLs (one per line): \033[0m").strip()
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                successful_scrapes = 0
                for i, url in enumerate(urls, 1):
                    loading_animation(f"Scraping product {i}/{len(urls)}", 2)
                    product = scraper.scrape_product(url)
                    
                    if product:
                        product['url'] = url
                        results.append(product)
                        successful_scrapes += 1
                        print(f"\n\033[92m✅ Product {i} scraped successfully! ({successful_scrapes}/{len(urls)})\033[0m")
                    else:
                        print(f"\n\033[91m❌ Failed to scrape product {i}\033[0m")
                
                print(f"\n\033[94m📊 Summary: {successful_scrapes}/{len(urls)} products scraped successfully\033[0m")
            else:
                print("\n\033[91m❌ File not found!\033[0m")
            
            input("\n\033[90mPress Enter to continue...\033[0m")
        
        elif choice == '4':
            if not results:
                print("\n\033[91m❌ No results to save. Please scrape some products first.\033[0m")
            else:
                print("\n\033[93m📁 Choose format:\033[0m")
                print("1. JSON (Recommended)")
                print("2. CSV")
                format_choice = input("\n\033[96mEnter choice (1-2): \033[0m").strip()
                
                format_type = 'json' if format_choice == '1' else 'csv'
                filename = save_results(results, format_type)
                print(f"\n\033[92m✅ Results saved to: {filename}\033[0m")
                print(f"\033[94m📊 Total products saved: {len(results)}\033[0m")
            
            input("\n\033[90mPress Enter to continue...\033[0m")
        
        elif choice == '5':
            if not results:
                print("\n\033[91m❌ No results to display. Please scrape some products first.\033[0m")
            else:
                print(f"\n\033[95m📋 CURRENT RESULTS ({len(results)} products)\033[0m")
                print("\033[95m" + "═" * 80 + "\033[0m")
                
                for i, product in enumerate(results, 1):
                    display_product_info(product, i)
                    if i < len(results):
                        print("\n" + "─" * 40)
            
            input("\n\033[90mPress Enter to continue...\033[0m")
        
        elif choice == '6':
            print("\n\033[93m⚙️  SETTINGS & CONFIGURATION\033[0m")
            print(f"Retry count: {scraper.retry_count}")
            print(f"Delay between requests: {scraper.delay_between_requests}s")
            print(f"Total products scraped: {len(results)}")
            
            # Option to clear results
            clear_choice = input("\nClear all results? (y/n): ").strip().lower()
            if clear_choice == 'y':
                results.clear()
                print("\033[92m✅ Results cleared!\033[0m")
            
            input("\n\033[90mPress Enter to continue...\033[0m")
        
        elif choice == '7':
            print("\n\033[92m" + "═" * 80 + "\033[0m")
            animate_text("🎉 Thank you for using Amazon Product Scraper Pro!", 0.05)
            animate_text("👨‍💻 Developed by: chowdhuryvai", 0.05)
            animate_text("🌐 Visit: https://crackyworld.com/", 0.05)
            animate_text("📢 Telegram: https://t.me/windowspremiumkey", 0.05)
            print("\033[92m" + "═" * 80 + "\033[0m")
            break
        
        else:
            print("\n\033[91m❌ Invalid choice. Please try again.\033[0m")
            input("\n\033[90mPress Enter to continue...\033[0m")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n\033[91m❌ Program interrupted by user. Exiting...\033[0m")
    except Exception as e:
        print(f"\n\033[91m💥 An unexpected error occurred: {str(e)}\033[0m")
