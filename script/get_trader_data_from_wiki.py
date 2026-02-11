"""
Fetch and parse trader data from ARC Raiders Wiki
Reads trader names from traders.txt and constructs detailed JSON database
"""

import html
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup


def sanitize_trader_name_for_url(trader_name: str) -> str:
    """Convert trader name to URL-safe format (spaces to underscores)."""
    return trader_name.replace(' ', '_')


def clean_text(text: str) -> str:
    """Clean text by decoding HTML entities and normalizing whitespace."""
    if not text:
        return text
    # Decode HTML entities like &nbsp;, &amp;, etc.
    text = html.unescape(text)
    # Remove MediaWiki bold (''') and italic ('') markup
    text = re.sub(r"'{2,}", '', text)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text.strip()


def extract_trader_image_from_source(source_text: str, trader_name: str) -> Optional[str]:
    """Extract trader image filename from MediaWiki source."""
    # Look for [[File:Trader ...png|...]] pattern (space or underscore after Trader)
    pattern = r'\[\[File:(Trader[ _][^\]|]+\.png)'
    match = re.search(pattern, source_text, re.IGNORECASE)
    
    if match:
        return match.group(1)
    
    return None


def extract_image_url_from_wiki_page(wiki_url: str, image_filename: str) -> Optional[Dict[str, str]]:
    """Fetch the wiki page and extract the actual image URL."""
    try:
        response = requests.get(wiki_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Normalize filename for matching (spaces to underscores)
        normalized_filename = image_filename.replace(' ', '_')
        
        # Find img tag with the specific filename in src or data-src
        img_tag = soup.find('img', src=lambda x: x and normalized_filename in x)
        
        if not img_tag:
            # Try searching in all img tags for Trader images
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if 'Trader' in src and trader_name_match(src, image_filename):
                    img_tag = img
                    break
        
        if not img_tag:
            return None
        
        # Get the src (webp thumb) and srcset (higher resolution)
        src = img_tag.get('src', '')
        srcset = img_tag.get('srcset', '')
        
        image_urls = {}
        
        # The src typically contains the webp thumb
        if src:
            if not src.startswith('http'):
                src = f"https://arcraiders.wiki{src}"
            image_urls['thumb'] = src
        
        # Parse srcset for higher resolution
        if srcset:
            srcset_parts = srcset.split()
            if srcset_parts:
                original_path = srcset_parts[0]
                if not original_path.startswith('http'):
                    original_path = f"https://arcraiders.wiki{original_path}"
                image_urls['original'] = original_path
        
        return image_urls if image_urls else None
        
    except Exception as e:
        print(f"    [WARNING] Could not fetch image from wiki page: {e}")
        return None


def trader_name_match(url: str, filename: str) -> bool:
    """Check if URL contains the trader image filename."""
    url_clean = url.replace('%20', '_').replace(' ', '_')
    filename_clean = filename.replace(' ', '_')
    return filename_clean in url_clean


def parse_item_grid(source_text: str) -> List[Dict[str, Any]]:
    """Parse the ItemGrid template containing shop inventory."""
    shop_items = []
    
    # Find {{ItemGrid ... }}
    itemgrid_match = re.search(r'\{\{ItemGrid\s*\n(.*?)\n\}\}', source_text, re.DOTALL)
    
    if not itemgrid_match:
        return shop_items
    
    content = itemgrid_match.group(1)
    
    # Parse parameters - items are numbered (name1, name2, etc.)
    lines = content.split('\n')
    
    # Dictionary to collect all properties for each item
    items_dict: Dict[int, Dict[str, Any]] = {}
    
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        
        line = line[1:].strip()
        if '=' not in line:
            continue
        
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        if not value:
            continue
        
        # Extract the property name and item number
        # Format: name1, image1, price1, etc.
        match = re.match(r'([a-zA-Z-]+)(\d+)', key)
        if not match:
            continue
        
        prop_name = match.group(1)
        item_num = int(match.group(2))
        
        # Initialize item dict if needed
        if item_num not in items_dict:
            items_dict[item_num] = {}
        
        # Process the value based on property type
        if prop_name == 'name':
            items_dict[item_num]['name'] = clean_text(value)
        
        elif prop_name == 'image':
            # Extract image filename from [[File:...png|...]]
            img_match = re.search(r'\[\[File:([^\]|]+\.(png|webp))', value, re.IGNORECASE)
            if img_match:
                items_dict[item_num]['image'] = img_match.group(1)
            
            # Also extract the link if present
            link_match = re.search(r'\|link=([^\]|]+)', value)
            if link_match:
                items_dict[item_num]['item_link'] = clean_text(link_match.group(1))
        
        elif prop_name == 'price':
            # Extract price from {{Price|value}} or {{Price|amount|currency}}
            price_match = re.search(r'\{\{Price\|([^}]+)\}\}', value)
            if price_match:
                price_content = price_match.group(1).strip()
                
                # Check if it's item-based currency (contains pipe)
                if '|' in price_content:
                    parts = price_content.split('|', 1)
                    if len(parts) == 2:
                        amount_str = parts[0].replace(',', '').strip()
                        currency_name = parts[1].strip()
                        try:
                            items_dict[item_num]['price'] = int(amount_str)
                            items_dict[item_num]['currency'] = currency_name
                        except ValueError:
                            items_dict[item_num]['price'] = price_content
                else:
                    # Coin-based currency
                    price_str = price_content.replace(',', '').strip()
                    try:
                        items_dict[item_num]['price'] = int(price_str)
                        items_dict[item_num]['currency'] = 'Coins'
                    except ValueError:
                        items_dict[item_num]['price'] = price_str
            else:
                # Fallback: no Price template, parse raw value
                if '|' in value:
                    parts = value.split('|', 1)
                    if len(parts) == 2:
                        amount_str = parts[0].strip()
                        currency_name = parts[1].strip()
                        try:
                            items_dict[item_num]['price'] = int(amount_str)
                            items_dict[item_num]['currency'] = currency_name
                        except ValueError:
                            items_dict[item_num]['price'] = value
                else:
                    items_dict[item_num]['price'] = value
        
        elif prop_name == 'rarity':
            items_dict[item_num]['rarity'] = clean_text(value)
        
        elif prop_name == 'isLimited':
            items_dict[item_num]['is_limited'] = value.lower() == 'true'
        
        elif prop_name == 'category-icon':
            # Extract category icon and count
            # Format: [[File:Ammo Heavy.png|link=|22px]]x10
            icon_match = re.search(r'\[\[File:([^\]|]+\.(png|webp))', value, re.IGNORECASE)
            if icon_match:
                items_dict[item_num]['category_icon'] = icon_match.group(1)
            
            # Check for count multiplier (e.g., x10, x25)
            count_match = re.search(r'x(\d+)', value)
            if count_match:
                items_dict[item_num]['ammo_count'] = int(count_match.group(1))
            
            # Check for fraction format (e.g., 1/1, 3/3)
            fraction_match = re.search(r'(\d+)/(\d+)', value)
            if fraction_match:
                items_dict[item_num]['stock'] = f"{fraction_match.group(1)}/{fraction_match.group(2)}"
    
    # Convert dictionary to sorted list and clean up data
    for item_num in sorted(items_dict.keys()):
        item = items_dict[item_num]
        if 'name' not in item:  # Skip items without a name
            continue
        
        # Create cleaned item with only essential fields
        cleaned_item = {}
        
        # Use item_link as name (cleaner than uppercase display name)
        if 'item_link' in item:
            cleaned_item['name'] = item['item_link']
        else:
            cleaned_item['name'] = item['name']
        
        # Add price and currency
        if 'price' in item:
            cleaned_item['price'] = item['price']
        if 'currency' in item:
            cleaned_item['currency'] = item['currency']
        
        # Add optional fields only if present
        if 'stock' in item:
            cleaned_item['stock'] = item['stock']
        if 'is_limited' in item:
            cleaned_item['is_limited'] = item['is_limited']
        if 'ammo_count' in item:
            cleaned_item['ammo_count'] = item['ammo_count']
        
        shop_items.append(cleaned_item)
    
    return shop_items


def parse_trader_from_wiki(trader_name: str, delay: float = 0.5) -> Optional[Dict[str, Any]]:
    """Fetch and parse a single trader from the wiki."""
    print(f"Processing: {trader_name}")
    
    url_name = sanitize_trader_name_for_url(trader_name)
    source_url = f"https://arcraiders.wiki/w/index.php?title={quote(url_name)}&action=edit"
    wiki_url = f"https://arcraiders.wiki/wiki/{quote(url_name)}"
    
    try:
        # Fetch the edit page to get source
        response = requests.get(source_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the textarea with source code
        textarea = soup.find('textarea', {'id': 'wpTextbox1'})
        
        if not textarea:
            print(f"  [!] Could not find source for {trader_name}")
            return None
        
        source_text = textarea.get_text()
        
        # Parse the data
        trader_data = {
            "name": trader_name,
            "wiki_url": wiki_url,
            "source_url": source_url,
        }
        
        # Extract trader image filename
        image_filename = extract_trader_image_from_source(source_text, trader_name)
        if image_filename:
            trader_data["image_filename"] = image_filename
            
            # Fetch actual image URLs from the wiki page
            print(f"  -> Fetching image URL from wiki page...")
            time.sleep(0.2)
            image_urls = extract_image_url_from_wiki_page(wiki_url, image_filename)
            if image_urls:
                trader_data["image_urls"] = image_urls
        
        # Parse shop inventory
        shop_items = parse_item_grid(source_text)
        if shop_items:
            trader_data["shop"] = shop_items
            print(f"  -> Found {len(shop_items)} items in shop")
        
        print(f"  [OK] Successfully parsed {trader_name}")
        
        # Be respectful to the server
        time.sleep(delay)
        
        return trader_data
        
    except requests.RequestException as e:
        print(f"  [ERROR] Error fetching {trader_name}: {e}")
        return None
    except Exception as e:
        print(f"  [ERROR] Error parsing {trader_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function to process traders from traders.txt file."""
    data_dir = Path(__file__).parent.parent / "data"
    traders_file = data_dir / "traders.txt"
    output_file = data_dir / "traders_database.json"
    
    # Check if traders file exists
    if not traders_file.exists():
        print(f"Error: {traders_file} not found!")
        print("Please create a traders.txt file with one trader name per line.")
        return
    
    # Read trader names
    with open(traders_file, 'r', encoding='utf-8') as f:
        trader_names = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(trader_names)} traders to process\n")
    print("="*60)
    
    # Process each trader
    traders_database = []
    failed_traders = []
    
    for i, trader_name in enumerate(trader_names, 1):
        print(f"\n[{i}/{len(trader_names)}] ", end='')
        
        trader_data = parse_trader_from_wiki(trader_name)
        
        if trader_data:
            traders_database.append(trader_data)
        else:
            failed_traders.append(trader_name)
    
    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(traders_database, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"[OK] Successfully processed: {len(traders_database)} traders")
    
    if failed_traders:
        print(f"[FAILED] Failed: {len(failed_traders)} traders")
        print("\nFailed traders:")
        for trader in failed_traders:
            print(f"  - {trader}")
    
    print(f"\n[OK] Database saved to: {output_file}")
    print(f"  Total size: {output_file.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()

