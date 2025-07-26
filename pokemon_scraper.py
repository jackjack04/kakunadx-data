# KakunaDex Automation System
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
        
        # Headers per sembrare un browser normale
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def scrape_pokemon_news(self):
        """Scrapi news dal sito ufficiale Pokémon - ULTIME 7 GIORNI"""
        try:
            news_items = []
            
            # URL corretti per le 3 categorie principali
            categories = {
                "🔴 MERCE": {
                    "url": "https://www.pokemon-card.com/info/#products",
                    "category": "set_release",
                    "section_id": "products"
                },
                "🔵 EVENTO": {
                    "url": "https://www.pokemon-card.com/info/#event", 
                    "category": "tournament",
                    "section_id": "event"
                },
                "🟢 CAMPAGNA": {
                    "url": "https://www.pokemon-card.com/info/#campaign",
                    "category": "promo", 
                    "section_id": "campaign"
                }
            }
            
            # Data limite: 7 giorni fa
            seven_days_ago = datetime.now() - timedelta(days=7)
            
            # Carica la pagina principale delle info
            main_url = "https://www.pokemon-card.com/info/"
            print(f"🔍 Loading main page: {main_url}")
            
            try:
                response = self.session.get(main_url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                print(f"✅ Main page loaded successfully")
            except Exception as e:
                print(f"❌ Error loading main page: {e}")
                return []
            
            for cat_name, cat_info in categories.items():
                print(f"🔍 Processing {cat_name}...")
                
                try:
                    # Cerca sezione specifica per categoria
                    section_selectors = [
                        f'#{cat_info["section_id"]}',
                        f'.{cat_info["section_id"]}',
                        f'[data-section="{cat_info["section_id"]}"]',
                        f'.section-{cat_info["section_id"]}',
                        f'div[id*="{cat_info["section_id"]}"]'
                    ]
                    
                    section = None
                    for selector in section_selectors:
                        section = soup.select_one(selector)
                        if section:
                            print(f"✅ Found section with selector: {selector}")
                            break
                    
                    if not section:
                        print(f"❌ Section not found for {cat_name}")
                        continue
                    
                    # Cerca articoli/news nella sezione
                    article_selectors = [
                        'article',
                        '.article',
                        '.news-item',
                        '.info-item', 
                        '.card',
                        '.item',
                        'li',
                        '.entry'
                    ]
                    
                    articles = []
                    for selector in article_selectors:
                        articles = section.select(selector)
                        if articles:
                            print(f"✅ Found {len(articles)} articles with selector: {selector}")
                            break
                    
                    if not articles:
                        print(f"❌ No articles found in {cat_name} section")
                        continue
                    
                    # Processa massimo 5 articoli per categoria
                    for i, article in enumerate(articles[:5]):
                        try:
                            # Estrai data e verifica se è negli ultimi 7 giorni
                            date_selectors = [
                                'time', '.date', '.published', '.time',
                                '[datetime]', '.post-date', '.entry-date'
                            ]
                            
                            date_elem = None
                            for date_sel in date_selectors:
                                date_elem = article.select_one(date_sel)
                                if date_elem:
                                    break
                            
                            date_str = self.parse_japanese_date(
                                date_elem.get('datetime') or 
                                date_elem.get_text() if date_elem else ""
                            )
                            
                            # Controlla se la news è recente
                            try:
                                news_date = datetime.strptime(date_str, '%Y-%m-%d')
                                if news_date < seven_days_ago:
                                    print(f"⏭️ Skipping old news: {date_str}")
                                    continue
                            except:
                                pass  # Se data non parsabile, includi comunque
                            
                            # Estrai titolo
                            title_selectors = [
                                'h1', 'h2', 'h3', 'h4', '.title', '.headline',
                                '.entry-title', 'a', '.name'
                            ]
                            
                            title_elem = None
                            for title_sel in title_selectors:
                                title_elem = article.select_one(title_sel)
                                if title_elem and title_elem.get_text(strip=True):
                                    break
                            
                            title_jp = title_elem.get_text(strip=True) if title_elem else f"{cat_name} Update {i+1}"
                            
                            # Estrai descrizione
                            desc_selectors = [
                                'p', '.summary', '.excerpt', '.description',
                                '.content', '.text', '.body'
                            ]
                            
                            desc_elem = None
                            for desc_sel in desc_selectors:
                                desc_elem = article.select_one(desc_sel)
                                if desc_elem and desc_elem.get_text(strip=True):
                                    break
                            
                            desc_jp = desc_elem.get_text(strip=True)[:300] if desc_elem else title_jp
                            
                            # Traduci
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
                
                # Delay tra categorie per essere gentili
                time.sleep(2)
            
            print(f"📊 Total scraped: {len(news_items)} items from last 7 days")
            return news_items
            
        except Exception as e:
            print(f"❌ Error scraping news: {e}")
            return []
    
    def scrape_promo_cards(self):
        """Scrapi SOLO dalle CAMPAGNE per le carte promo"""
        try:
            # URL corretto per campagne
            campaign_url = "https://www.pokemon-card.com/info/#campaign"
            main_url = "https://www.pokemon-card.com/info/"
            
            print(f"🎴 Loading campaigns from: {main_url}")
            response = self.session.get(main_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            promo_cards = []
            
            # Cerca sezione campagne
            campaign_section = None
            campaign_selectors = [
                '#campaign', '.campaign', '[data-section="campaign"]',
                '.section-campaign', 'div[id*="campaign"]'
            ]
            
            for selector in campaign_selectors:
                campaign_section = soup.select_one(selector)
                if campaign_section:
                    print(f"✅ Found campaign section with: {selector}")
                    break
            
            if not campaign_section:
                print(f"❌ Campaign section not found")
                return []
            
            # Cerca campagne attive/future
            campaign_items = campaign_section.select('article, .article, .item, .card, li, .entry')[:8]
            print(f"🔍 Found {len(campaign_items)} campaign items")
            
            seven_days_ago = datetime.now() - timedelta(days=7)
            
            for i, item in enumerate(campaign_items):
                try:
                    # Verifica se è una campagna recente o futura
                    date_elem = item.select_one('time, .date, .period, .until, [datetime]')
                    date_str = self.parse_japanese_date(
                        date_elem.get('datetime') or 
                        date_elem.get_text() if date_elem else ""
                    )
                    
                    # Per le promo, includiamo anche quelle future
                    try:
                        promo_date = datetime.strptime(date_str, '%Y-%m-%d')
                        if promo_date < seven_days_ago:
                            continue  # Skip vecchie campagne
                    except:
                        pass
                    
                    # Estrai info carta promo
                    name_elem = item.select_one('h1, h2, h3, h4, .title, .name, a')
                    name_jp = name_elem.get_text(strip=True) if name_elem else f"Carta Promo Campagna {i+1}"
                    name_it = self.translate_to_italian(name_jp)
                    
                    # Cerca codice carta se presente
                    code_text = item.get_text()
                    code_match = re.search(r'[A-Z0-9]+-[A-Z0-9]+|No\.\s*\d+|\d+/\d+', code_text)
                    code = code_match.group() if code_match else f"CAMP-{i+1:03d}"
                    
                    desc_elem = item.select_one('p, .description, .summary, .content')
                    desc_jp = desc_elem.get_text(strip=True) if desc_elem else "Carta promozionale da campagna speciale"
                    desc_it = self.translate_to_italian(desc_jp)
                    
                    promo_card = {
                        "id": f"auto_campaign_{int(time.time())}_{i}",
                        "name": name_it,
                        "code": code,
                        "series": "Campaign Promotional Cards",
                        "releaseDate": date_str,
                        "rarity": "Campaign Promo",
                        "imageUrl": f"campaign-promo-{i+1}",
                        "description": desc_it,
                        "availability": "store"  # Campagne di solito nei negozi
                    }
                    
                    promo_cards.append(promo_card)
                    print(f"✅ Promo campaign: {name_it}")
                    
                except Exception as e:
                    print(f"❌ Error parsing promo campaign: {e}")
                    continue
            
            print(f"🎴 Total promo cards found: {len(promo_cards)}")
            return promo_cards
            
        except Exception as e:
            print(f"❌ Error scraping promo campaigns: {e}")
            return []
    
    def translate_to_italian(self, japanese_text):
        """Traduce testo giapponese in italiano"""
        try:
            if not japanese_text or len(japanese_text.strip()) == 0:
                return "Aggiornamento Pokémon"
            
            # Traduci da giapponese a italiano
            translation = self.translator.translate(japanese_text, src='ja', dest='it')
            result = translation.text
            
            # Post-processing per termini Pokémon
            result = self.fix_pokemon_terms(result)
            
            return result
            
        except Exception as e:
            print(f"❌ Translation error: {e}")
            return japanese_text  # Fallback al testo originale
    
    def fix_pokemon_terms(self, text):
        """Corregge termini Pokémon mal tradotti"""
        fixes = {
            "pokemon": "Pokémon",
            "Pokemon": "Pokémon", 
            "carte commerciali": "carte collezionabili",
            "gioco di carte": "gioco di carte collezionabili",
            "mazzo": "deck",
            "torneo": "tournament",
            "campionato": "championship",
            "promozione": "promozionale",
            "raccolta": "collezione",
        }
        
        for wrong, correct in fixes.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def parse_japanese_date(self, date_text):
        """Converte date giapponesi in formato ISO"""
        try:
            # Rimuovi caratteri giapponesi e converti
            date_clean = re.sub(r'[年月日]', '-', date_text).strip('-')
            
            # Prova vari formati
            formats = ['%Y-%m-%d', '%m-%d', '%Y/%m/%d']
            
            for fmt in formats:
                try:
                    parsed = datetime.strptime(date_clean, fmt)
                    if parsed.year < 2000:  # Se anno mancante, usa 2025
                        parsed = parsed.replace(year=2025)
                    return parsed.strftime('%Y-%m-%d')
                except:
                    continue
            
            # Fallback alla data corrente
            return datetime.now().strftime('%Y-%m-%d')
            
        except:
            return datetime.now().strftime('%Y-%m-%d')
    
    def categorize_news(self, title, content):
        """Categorizza automaticamente le news"""
        text = (title + " " + content).lower()
        
        if any(word in text for word in ['promo', 'special', 'limited', 'exclusive']):
            return "promo"
        elif any(word in text for word in ['tournament', 'championship', 'worlds', 'battle']):
            return "tournament"
        elif any(word in text for word in ['release', 'new set', 'expansion', 'booster']):
            return "set_release"
        else:
            return "news"
    
    def determine_availability(self, description):
        """Determina la disponibilità della carta promo"""
        desc_lower = description.lower()
        
        if any(word in desc_lower for word in ['tournament', 'championship', 'battle']):
            return "tournament"
        elif any(word in desc_lower for word in ['store', 'center', 'shop']):
            return "store"
        elif any(word in desc_lower for word in ['online', 'digital']):
            return "online"
        else:
            return "store"  # Default
    
    def update_github_content(self, news_items, promo_cards):
        """Aggiorna automaticamente il file GitHub - SOLO ULTIMI 7 GIORNI"""
        try:
            # Carica contenuto attuale
            try:
                file = self.repo.get_contents("content.json")
                current_content = json.loads(file.decoded_content.decode())
            except:
                current_content = {"news": [], "promoCards": [], "lastUpdated": ""}
            
            # Data limite: 7 giorni fa
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # PULIZIA AUTOMATICA: rimuovi contenuti vecchi di 7+ giorni
            def is_recent(item):
                try:
                    item_date = item.get("publishDate", "") or item.get("releaseDate", "")
                    return item_date >= seven_days_ago
                except:
                    return False  # Rimuovi se data non valida
            
            # Filtra contenuti esistenti (mantieni solo recenti + manuali)
            existing_news = [
                n for n in current_content.get("news", []) 
                if (not n["id"].startswith("auto_") or is_recent(n))  # Mantieni manuali O recenti
            ]
            
            existing_promos = [
                p for p in current_content.get("promoCards", [])
                if (not p["id"].startswith("auto_") or is_recent(p))
            ]
            
            # Combina con nuovi contenuti
            all_news = existing_news + news_items
            all_promos = existing_promos + promo_cards
            
            # Rimuovi duplicati per ID
            seen_news = set()
            unique_news = []
            for news in all_news:
                if news["id"] not in seen_news:
                    seen_news.add(news["id"])
                    unique_news.append(news)
            
            seen_promos = set()
            unique_promos = []
            for promo in all_promos:
                if promo["id"] not in seen_promos:
                    seen_promos.add(promo["id"])
                    unique_promos.append(promo)
            
            # Ordina per data (più recenti primi)
            unique_news.sort(key=lambda x: x.get("publishDate", ""), reverse=True)
            unique_promos.sort(key=lambda x: x.get("releaseDate", ""), reverse=True)
            
            # Limita quantità per performance
            final_news = unique_news[:20]  # Max 20 news totali
            final_promos = unique_promos[:10]  # Max 10 promo totali
            
            # Statistiche
            auto_news_count = len([n for n in final_news if n["id"].startswith("auto_")])
            auto_promos_count = len([p for p in final_promos if p["id"].startswith("auto_")])
            
            # Crea nuovo contenuto
            new_content = {
                "news": final_news,
                "promoCards": final_promos,
                "lastUpdated": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 🤖 Auto: {auto_news_count} news, {auto_promos_count} promo (7 giorni)"
            }
            
            # Aggiorna su GitHub
            content_json = json.dumps(new_content, ensure_ascii=False, indent=2)
            
            try:
                # Aggiorna file esistente
                self.repo.update_file(
                    "content.json",
                    f"🤖 Auto-update ultimi 7gg: +{len(news_items)} news, +{len(promo_cards)} promo",
                    content_json,
                    file.sha
                )
                print(f"✅ GitHub updated! Auto-cleanup applied (7 days limit)")
            except:
                # Crea nuovo file se non esiste
                self.repo.create_file(
                    "content.json",
                    f"🤖 Auto-create: {len(news_items)} news, {len(promo_cards)} promo",
                    content_json
                )
                print(f"✅ GitHub file created!")
            
            print(f"📊 Final content: {len(final_news)} news, {len(final_promos)} promo cards")
            return True
            
        except Exception as e:
            print(f"❌ GitHub update error: {e}")
            return False
    
    def run_full_automation(self):
        """Esegue il ciclo completo di automazione"""
        print("🤖 Starting KakunaDex automation...")
        
        # 1. Scrapi news
        print("📰 Scraping news...")
        news_items = self.scrape_pokemon_news()
        
        # 2. Scrapi carte promo
        print("🎴 Scraping promo cards...")
        promo_cards = self.scrape_promo_cards()
        
        # 3. Aggiorna GitHub
        print("📦 Updating GitHub...")
        success = self.update_github_content(news_items, promo_cards)
        
        if success:
            print(f"🎉 Automation completed! {len(news_items)} news, {len(promo_cards)} promos")
        else:
            print("❌ Automation failed!")
        
        return success

# MAIN EXECUTION
if __name__ == "__main__":
    # Configurazione (da mettere come environment variables)
    GITHUB_TOKEN = "your_github_token_here"
    GITHUB_REPO = "jackjack04/kakunadx-data"
    
    # Crea scraper ed esegui
    scraper = PokemonNewsScraper(GITHUB_TOKEN, GITHUB_REPO)
    scraper.run_full_automation()
