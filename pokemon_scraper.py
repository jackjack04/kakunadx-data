# KakunaDex Automation System - VERSIONE GIAPPONESE
# File: pokemon_scraper.py

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
import time
from googletrans import Translator
import base64
from github import Github

class PokemonNewsScraper:
    def __init__(self, github_token, github_repo):
        self.session = requests.Session()
        self.translator = Translator()
        self.github = Github(github_token)
        self.repo = self.github.get_repo(github_repo)  # "jackjack04/kakunadx-data"
        
        # Headers per sembrare un browser giapponese
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def scrape_pokemon_news(self):
        """Scrapi news dal sito Pokémon giapponese - NOMI GIAPPONESI"""
        try:
            news_items = []
            
            # URL e selettori per categorie GIAPPONESI
            categories = {
                "🔴 商品": {
                    "url": "https://www.pokemon-card.com/info/",
                    "category": "set_release",
                    "japanese_name": "商品",
                    "search_terms": ["商品", "製品", "パック", "ボックス", "シングル"]
                },
                "🔵 イベント": {
                    "url": "https://www.pokemon-card.com/info/",
                    "category": "tournament", 
                    "japanese_name": "イベント",
                    "search_terms": ["イベント", "大会", "トーナメント", "バトル", "チャンピオンシップ"]
                },
                "🟢 キャンペーン": {
                    "url": "https://www.pokemon-card.com/info/",
                    "category": "promo",
                    "japanese_name": "キャンペーン", 
                    "search_terms": ["キャンペーン", "プロモ", "特典", "配布", "限定"]
                }
            }
            
            # Data limite: 7 giorni fa
            seven_days_ago = datetime.now() - timedelta(days=7)
            
            # Carica la pagina principale
            main_url = "https://www.pokemon-card.com/info/"
            print(f"🔍 Loading main page: {main_url}")
            
            try:
                response = self.session.get(main_url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                print(f"✅ Main page loaded successfully")
                
                # Debug: Stampa alcune classi trovate
                all_divs = soup.find_all('div', class_=True)[:10]
                print(f"🔍 Sample classes found: {[div.get('class') for div in all_divs[:5]]}")
                
            except Exception as e:
                print(f"❌ Error loading main page: {e}")
                return []
            
            for cat_name, cat_info in categories.items():
                print(f"🔍 Processing {cat_name} ({cat_info['japanese_name']})...")
                
                try:
                    # STRATEGIA 1: Cerca per testo giapponese
                    japanese_sections = soup.find_all(text=re.compile(cat_info['japanese_name']))
                    print(f"📝 Found {len(japanese_sections)} text matches for {cat_info['japanese_name']}")
                    
                    # STRATEGIA 2: Cerca articoli generici e filtra per contenuto
                    all_articles = soup.find_all(['article', 'div', 'li'], class_=re.compile(r'(item|news|info|article|card|entry)'))
                    print(f"📄 Found {len(all_articles)} total articles to filter")
                    
                    # Filtra articoli per categoria
                    relevant_articles = []
                    for article in all_articles[:20]:  # Analizza i primi 20
                        article_text = article.get_text().lower()
                        
                        # Cerca termini giapponesi della categoria
                        if any(term in article_text for term in cat_info['search_terms']):
                            relevant_articles.append(article)
                            print(f"✅ Found relevant article for {cat_info['japanese_name']}")
                    
                    if not relevant_articles:
                        print(f"❌ No relevant articles found for {cat_name}")
                        continue
                    
                    # Processa i primi 3 articoli per categoria
                    for i, article in enumerate(relevant_articles[:3]):
                        try:
                            # Estrai data
                            date_elem = article.find(['time', 'span'], string=re.compile(r'\d{4}[年/\-]\d{1,2}[月/\-]\d{1,2}'))
                            if not date_elem:
                                date_elem = article.find(['time', 'span'], class_=re.compile(r'date'))
                            
                            date_str = self.parse_japanese_date(
                                date_elem.get_text() if date_elem else ""
                            )
                            
                            # Estrai titolo
                            title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'a'])
                            title_jp = title_elem.get_text(strip=True) if title_elem else f"{cat_name} 更新情報"
                            
                            # Estrai descrizione (primi 200 caratteri del testo)
                            desc_jp = article.get_text(strip=True)[:200]
                            
                            # Pulisci titolo e descrizione
                            title_jp = re.sub(r'\s+', ' ', title_jp).strip()
                            desc_jp = re.sub(r'\s+', ' ', desc_jp).strip()
                            
                            # Traduci in italiano
                            title_it = self.translate_to_italian(title_jp)
                            desc_it = self.translate_to_italian(desc_jp)
                            
                            # Determina se mettere in evidenza
                            is_highlighted = (
                                cat_info["category"] == "promo" or  # Tutte le promo in evidenza
                                i == 0  # Prima news di ogni categoria
                            )
                            
                            news_item = {
                                "id": f"auto_{cat_info['category']}_{int(time.time())}_{i}",
                                "title": f"{self.get_emoji(cat_info['category'])} {title_it}",
                                "subtitle": desc_it[:80] + "..." if len(desc_it) > 80 else desc_it,
                                "content": desc_it,
                                "imageUrl": None,
                                "publishDate": date_str,
                                "category": cat_info["category"],
                                "isHighlighted": is_highlighted
                            }
                            
                            news_items.append(news_item)
                            print(f"✅ Added: {title_it[:40]}...")
                            
                        except Exception as e:
                            print(f"❌ Error parsing article in {cat_name}: {e}")
                            continue
                
                except Exception as e:
                    print(f"❌ Error processing {cat_name}: {e}")
                    continue
                
                # Delay tra categorie
                time.sleep(2)
            
            print(f"📊 Total scraped: {len(news_items)} items")
            return news_items
            
        except Exception as e:
            print(f"❌ Error scraping news: {e}")
            return []
    
    def scrape_promo_cards(self):
        """Scrapi carte promo dalle campagne giapponesi"""
        try:
            main_url = "https://www.pokemon-card.com/info/"
            print(f"🎴 Searching for campaign/promo cards...")
            
            response = self.session.get(main_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            promo_cards = []
            
            # Cerca articoli con termini relativi a campagne/promo
            campaign_terms = ["キャンペーン", "プロモ", "特典", "配布", "限定", "記念"]
            all_articles = soup.find_all(['article', 'div', 'li'], class_=re.compile(r'(item|news|info|article|card|entry)'))
            
            campaign_articles = []
            for article in all_articles[:15]:
                article_text = article.get_text()
                if any(term in article_text for term in campaign_terms):
                    campaign_articles.append(article)
            
            print(f"🎴 Found {len(campaign_articles)} potential promo articles")
            
            for i, article in enumerate(campaign_articles[:4]):
                try:
                    # Estrai nome carta (cerca pattern comuni)
                    article_text = article.get_text()
                    
                    # Pattern per nomi Pokémon comuni
                    pokemon_patterns = [
                        r'ピカチュウ', r'リザードン', r'フシギダネ', r'ゼニガメ',
                        r'ビクティニ', r'ミュウ', r'セレビィ', r'ジラーチ'
                    ]
                    
                    name_jp = "プロモカード"  # Default
                    for pattern in pokemon_patterns:
                        if re.search(pattern, article_text):
                            name_jp = re.search(pattern, article_text).group()
                            break
                    
                    name_it = self.translate_to_italian(name_jp)
                    
                    # Estrai/genera codice carta
                    code_match = re.search(r'[A-Z0-9]+-[A-Z0-9]+|\d+/[A-Z0-9]+|No\.\s*\d+', article_text)
                    code = code_match.group() if code_match else f"PROMO-{i+1:03d}"
                    
                    # Data
                    date_str = self.parse_japanese_date(article_text)
                    
                    # Descrizione
                    desc_jp = article_text[:200]
                    desc_it = self.translate_to_italian(desc_jp)
                    
                    promo_card = {
                        "id": f"auto_promo_{int(time.time())}_{i}",
                        "name": name_it,
                        "code": code,
                        "series": "Japanese Promotional Cards",
                        "releaseDate": date_str,
                        "rarity": "Japanese Promo",
                        "imageUrl": f"japanese-promo-{i+1}",
                        "description": desc_it,
                        "availability": "store"
                    }
                    
                    promo_cards.append(promo_card)
                    print(f"✅ Promo found: {name_it}")
                    
                except Exception as e:
                    print(f"❌ Error parsing promo: {e}")
                    continue
            
            print(f"🎴 Total promo cards: {len(promo_cards)}")
            return promo_cards
            
        except Exception as e:
            print(f"❌ Error scraping promo cards: {e}")
            return []
    
    def translate_to_italian(self, japanese_text):
        """Traduce testo giapponese in italiano"""
        try:
            if not japanese_text or len(japanese_text.strip()) == 0:
                return "Aggiornamento Pokémon"
            
            # Pulisci il testo
            clean_text = re.sub(r'\s+', ' ', japanese_text).strip()
            if len(clean_text) > 500:  # Limita lunghezza per traduzione
                clean_text = clean_text[:500]
            
            # Traduci da giapponese a italiano
            translation = self.translator.translate(clean_text, src='ja', dest='it')
            result = translation.text
            
            # Post-processing per termini Pokémon
            result = self.fix_pokemon_terms(result)
            
            return result
            
        except Exception as e:
            print(f"❌ Translation error for '{japanese_text[:50]}...': {e}")
            return f"Contenuto Pokémon"  # Fallback generico
    
    def fix_pokemon_terms(self, text):
        """Corregge termini Pokémon mal tradotti"""
        fixes = {
            "pokemon": "Pokémon",
            "Pokemon": "Pokémon", 
            "pokémon": "Pokémon",
            "carte commerciali": "carte collezionabili",
            "gioco di carte": "TCG",
            "carte di trading": "carte collezionabili",
            "pikachu": "Pikachu",
            "charizard": "Charizard",
            "mew": "Mew",
            "celebi": "Celebi",
            "victini": "Victini",
            "promozione": "promozionale",
            "campagna": "campagna",
            "evento": "evento",
            "torneo": "torneo"
        }
        
        for wrong, correct in fixes.items():
            text = re.sub(wrong, correct, text, flags=re.IGNORECASE)
        
        return text
    
    def parse_japanese_date(self, date_text):
        """Converte date giapponesi in formato ISO"""
        try:
            # Pattern giapponesi comuni
            patterns = [
                (r'(\d{4})年(\d{1,2})月(\d{1,2})日', '%Y-%m-%d'),
                (r'(\d{4})/(\d{1,2})/(\d{1,2})', '%Y-%m-%d'),
                (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d'),
                (r'(\d{1,2})月(\d{1,2})日', '2025-%m-%d'),  # Anno corrente
            ]
            
            for pattern, format_str in patterns:
                match = re.search(pattern, date_text)
                if match:
                    if len(match.groups()) == 3:
                        year, month, day = match.groups()
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    elif len(match.groups()) == 2:
                        month, day = match.groups()
                        return f"2025-{month.zfill(2)}-{day.zfill(2)}"
            
            # Fallback alla data corrente
            return datetime.now().strftime('%Y-%m-%d')
            
        except:
            return datetime.now().strftime('%Y-%m-%d')
    
    def get_emoji(self, category):
        """Emoji per categoria"""
        emojis = {
            "set_release": "📦",
            "tournament": "🏆", 
            "promo": "🎁"
        }
        return emojis.get(category, "📰")
    
    def update_github_content(self, news_items, promo_cards):
        """Aggiorna GitHub mantenendo contenuti esistenti"""
        try:
            # Carica contenuto attuale
            try:
                file = self.repo.get_contents("content.json")
                current_content = json.loads(file.decoded_content.decode())
            except:
                current_content = {"news": [], "promoCards": [], "lastUpdated": ""}
            
            # Data limite: 7 giorni fa
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Mantieni contenuti recenti (auto + manuali)
            def is_recent_or_manual(item):
                try:
                    item_date = item.get("publishDate", "") or item.get("releaseDate", "")
                    return (not item["id"].startswith("auto_") or  # Manuale
                           item_date >= seven_days_ago)  # O recente
                except:
                    return True  # In caso di dubbio, mantieni
            
            existing_news = [n for n in current_content.get("news", []) if is_recent_or_manual(n)]
            existing_promos = [p for p in current_content.get("promoCards", []) if is_recent_or_manual(p)]
            
            # Combina con nuovi contenuti
            all_news = existing_news + news_items
            all_promos = existing_promos + promo_cards
            
            # Rimuovi duplicati per ID
            unique_news = []
            seen_ids = set()
            for news in all_news:
                if news["id"] not in seen_ids:
                    seen_ids.add(news["id"])
                    unique_news.append(news)
            
            unique_promos = []
            seen_ids = set()
            for promo in all_promos:
                if promo["id"] not in seen_ids:
                    seen_ids.add(promo["id"])
                    unique_promos.append(promo)
            
            # Ordina per data
            unique_news.sort(key=lambda x: x.get("publishDate", ""), reverse=True)
            unique_promos.sort(key=lambda x: x.get("releaseDate", ""), reverse=True)
            
            # Limita quantità
            final_news = unique_news[:20]
            final_promos = unique_promos[:10]
            
            # Statistiche
            auto_news = len([n for n in final_news if n["id"].startswith("auto_")])
            auto_promos = len([p for p in final_promos if p["id"].startswith("auto_")])
            
            # Nuovo contenuto
            new_content = {
                "news": final_news,
                "promoCards": final_promos,
                "lastUpdated": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 🤖 Auto JP: {auto_news} news, {auto_promos} promo"
            }
            
            # Aggiorna GitHub
            content_json = json.dumps(new_content, ensure_ascii=False, indent=2)
            
            try:
                self.repo.update_file(
                    "content.json",
                    f"🤖 Japanese scrape: +{len(news_items)} news, +{len(promo_cards)} promo",
                    content_json,
                    file.sha
                )
                print(f"✅ GitHub updated!")
            except:
                self.repo.create_file(
                    "content.json",
                    f"🤖 Japanese content: {len(news_items)} news, {len(promo_cards)} promo",
                    content_json
                )
                print(f"✅ GitHub file created!")
            
            return True
            
        except Exception as e:
            print(f"❌ GitHub update error: {e}")
            return False
    
    def run_full_automation(self):
        """Esegue automazione completa giapponese"""
        print("🤖 Starting KakunaDex Japanese automation...")
        
        # 1. Scrapi news giapponesi
        print("📰 Scraping Japanese news...")
        news_items = self.scrape_pokemon_news()
        
        # 2. Scrapi carte promo giapponesi
        print("🎴 Scraping Japanese promo cards...")
        promo_cards = self.scrape_promo_cards()
        
        # 3. Aggiorna GitHub
        print("📦 Updating GitHub...")
        success = self.update_github_content(news_items, promo_cards)
        
        if success:
            print(f"🎉 Japanese automation completed! {len(news_items)} news, {len(promo_cards)} promos")
        else:
            print("❌ Japanese automation failed!")
        
        return success

# MAIN EXECUTION
if __name__ == "__main__":
    import os
    
    # Prendi token dalle environment variables
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
    GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY', 'jackjack04/kakunadx-data')
    
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not found!")
        exit(1)
    
    print(f"🚀 Using GitHub native token for {GITHUB_REPO}...")
    print("🇯🇵 Configured for Japanese Pokemon Card website...")
    
    # Crea scraper ed esegui
    scraper = PokemonNewsScraper(GITHUB_TOKEN, GITHUB_REPO)
    success = scraper.run_full_automation()
    
    if not success:
        exit(1)
