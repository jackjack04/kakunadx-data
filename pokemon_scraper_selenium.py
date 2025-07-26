# Pokemon Scraper con Selenium - VERA AUTOMAZIONE
# File: pokemon_scraper_selenium.py

import os
import json
import time
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from googletrans import Translator
from github import Github

class SeleniumPokemonScraper:
    def __init__(self, github_token, github_repo):
        self.translator = Translator()
        self.github = Github(github_token)
        self.repo = self.github.get_repo(github_repo)
        self.driver = None
        
    def setup_driver(self):
        """Configura Chrome headless per GitHub Actions"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver
        
    def scrape_pokemon_news_selenium(self):
        """Scraping con browser reale"""
        try:
            print("🚀 Starting Selenium scraper...")
            self.setup_driver()
            
            news_items = []
            
            # Carica la pagina principale
            print("📥 Loading Pokemon Card website...")
            self.driver.get("https://www.pokemon-card.com/info/")
            
            # Aspetta che la pagina carichi
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print("✅ Page loaded, waiting for content...")
            time.sleep(3)  # Aspetta JavaScript
            
            # Cerca tutti gli elementi che potrebbero essere news
            selectors_to_try = [
                "article",
                "[class*='news']",
                "[class*='info']", 
                "[class*='item']",
                "[class*='card']",
                "li",
                ".entry"
            ]
            
            all_elements = []
            for selector in selectors_to_try:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"🔍 Found {len(elements)} elements with selector: {selector}")
                    all_elements.extend(elements)
                except:
                    continue
            
            # Rimuovi duplicati
            unique_elements = list(set(all_elements))
            print(f"📊 Total unique elements: {len(unique_elements)}")
            
            # Categorie giapponesi
            categories = {
                "商品": "set_release",      # Prodotti
                "イベント": "tournament",    # Eventi  
                "キャンペーン": "promo"      # Campagne
            }
            
            for i, element in enumerate(unique_elements[:30]):  # Analizza primi 30
                try:
                    text = element.text.strip()
                    if len(text) < 10:  # Skip elementi troppo piccoli
                        continue
                        
                    # Determina categoria
                    category = "news"
                    category_emoji = "📰"
                    for jp_term, cat in categories.items():
                        if jp_term in text:
                            category = cat
                            category_emoji = {"set_release": "📦", "tournament": "🏆", "promo": "🎁"}[cat]
                            break
                    
                    # Estrai titolo (prima riga significativa)
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    title_jp = lines[0] if lines else f"Pokémon更新情報 {i+1}"
                    
                    # Estrai descrizione
                    desc_jp = ' '.join(lines[1:3]) if len(lines) > 1 else title_jp
                    desc_jp = desc_jp[:200]  # Limita lunghezza
                    
                    # Traduci
                    title_it = self.translate_to_italian(title_jp)
                    desc_it = self.translate_to_italian(desc_jp)
                    
                    # Skip se traduzione fallita o troppo generica
                    if any(skip_word in title_it.lower() for skip_word in ['pokémon', 'aggiornamento', 'contenuto']):
                        if len(title_it.split()) < 3:
                            continue
                    
                    news_item = {
                        "id": f"selenium_{category}_{int(time.time())}_{i}",
                        "title": f"{category_emoji} {title_it}",
                        "subtitle": desc_it[:80] + "..." if len(desc_it) > 80 else desc_it,
                        "content": desc_it,
                        "imageUrl": None,
                        "publishDate": datetime.now().strftime('%Y-%m-%d'),
                        "category": category,
                        "isHighlighted": category == "promo" or i < 2
                    }
                    
                    news_items.append(news_item)
                    print(f"✅ Added: {title_it[:40]}...")
                    
                    if len(news_items) >= 6:  # Max 6 news per run
                        break
                        
                except Exception as e:
                    print(f"❌ Error processing element: {e}")
                    continue
            
            print(f"📊 Selenium scraped: {len(news_items)} items")
            return news_items
            
        except Exception as e:
            print(f"❌ Selenium error: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
    def scrape_promo_cards_selenium(self):
        """Cerca carte promo con Selenium"""
        try:
            if not self.driver:
                self.setup_driver()
                
            promo_cards = []
            
            # Cerca specificamente campagne/promo
            self.driver.get("https://www.pokemon-card.com/info/")
            time.sleep(3)
            
            # Cerca elementi con termini promo
            promo_terms = ["キャンペーン", "プロモ", "特典", "配布", "限定"]
            
            for term in promo_terms:
                try:
                    elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{term}')]")
                    
                    for i, element in enumerate(elements[:3]):
                        parent = element.find_element(By.XPATH, "./..")
                        text = parent.text.strip()
                        
                        if len(text) < 20:
                            continue
                            
                        # Estrai nome carta
                        pokemon_names = ["ピカチュウ", "リザードン", "ミュウ", "セレビィ", "ビクティニ"]
                        name_jp = "プロモカード"
                        
                        for pokemon in pokemon_names:
                            if pokemon in text:
                                name_jp = pokemon
                                break
                        
                        name_it = self.translate_to_italian(name_jp)
                        
                        # Genera codice
                        code = f"AUTO-{term[:2]}{i+1:02d}"
                        
                        # Descrizione
                        desc_jp = text[:150]
                        desc_it = self.translate_to_italian(desc_jp)
                        
                        promo_card = {
                            "id": f"selenium_promo_{int(time.time())}_{i}",
                            "name": name_it,
                            "code": code,
                            "series": "Selenium Auto-Discovered Promos",
                            "releaseDate": (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                            "rarity": "Auto Promo",
                            "imageUrl": f"auto-promo-{len(promo_cards)+1}",
                            "description": desc_it,
                            "availability": "store"
                        }
                        
                        promo_cards.append(promo_card)
                        print(f"🎴 Found promo: {name_it}")
                        
                        if len(promo_cards) >= 3:
                            break
                except:
                    continue
                    
            return promo_cards
            
        except Exception as e:
            print(f"❌ Promo scraping error: {e}")
            return []
    
    def translate_to_italian(self, japanese_text):
        """Traduzione migliorata"""
        try:
            if not japanese_text or len(japanese_text.strip()) == 0:
                return "Aggiornamento Pokémon"
            
            # Pulisci testo
            clean_text = re.sub(r'\s+', ' ', japanese_text).strip()
            if len(clean_text) > 300:
                clean_text = clean_text[:300]
            
            # Traduci
            translation = self.translator.translate(clean_text, src='ja', dest='it')
            result = translation.text
            
            # Fix termini Pokémon
            fixes = {
                "pokemon": "Pokémon", "Pokemon": "Pokémon",
                "carte commerciali": "carte collezionabili",
                "gioco di carte": "TCG", "pikachu": "Pikachu",
                "charizard": "Charizard", "mew": "Mew"
            }
            
            for wrong, correct in fixes.items():
                result = re.sub(wrong, correct, result, flags=re.IGNORECASE)
            
            return result
            
        except Exception as e:
            print(f"❌ Translation error: {e}")
            return f"Contenuto Pokémon (traduzione fallita)"
    
    def update_github_content(self, news_items, promo_cards):
        """Aggiorna GitHub con nuovi contenuti"""
        try:
            # Carica contenuto esistente
            try:
                file = self.repo.get_contents("content.json")
                current_content = json.loads(file.decoded_content.decode())
            except:
                current_content = {"news": [], "promoCards": [], "lastUpdated": ""}
            
            # Rimuovi vecchi contenuti auto
            existing_news = [n for n in current_content.get("news", []) 
                           if not n["id"].startswith("selenium_")]
            existing_promos = [p for p in current_content.get("promoCards", []) 
                             if not p["id"].startswith("selenium_")]
            
            # Combina contenuti
            all_news = existing_news + news_items
            all_promos = existing_promos + promo_cards
            
            # Limita quantità
            final_news = all_news[:20]
            final_promos = all_promos[:10]
            
            # Ordina per data
            final_news.sort(key=lambda x: x.get("publishDate", ""), reverse=True)
            final_promos.sort(key=lambda x: x.get("releaseDate", ""), reverse=True)
            
            # Nuovo contenuto
            new_content = {
                "news": final_news,
                "promoCards": final_promos,
                "lastUpdated": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 🤖 Selenium: {len(news_items)} news, {len(promo_cards)} promo"
            }
            
            # Aggiorna GitHub
            content_json = json.dumps(new_content, ensure_ascii=False, indent=2)
            
            try:
                self.repo.update_file(
                    "content.json",
                    f"🤖 Selenium auto-update: +{len(news_items)} news, +{len(promo_cards)} promo",
                    content_json,
                    file.sha
                )
                print("✅ GitHub updated with Selenium results!")
                return True
            except Exception as e:
                print(f"❌ GitHub update failed: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Content update error: {e}")
            return False
    
    def run_selenium_automation(self):
        """Esegue automazione completa con Selenium"""
        print("🤖 Starting Selenium-based automation...")
        
        try:
            # 1. Scrapi news
            news_items = self.scrape_pokemon_news_selenium()
            
            # 2. Scrapi promo (opzionale, usa stesso driver)
            promo_cards = self.scrape_promo_cards_selenium()
            
            # 3. Aggiorna GitHub
            success = self.update_github_content(news_items, promo_cards)
            
            if success:
                print(f"🎉 Selenium automation completed! {len(news_items)} news, {len(promo_cards)} promos")
            else:
                print("❌ Selenium automation partially failed!")
                
            return success
            
        except Exception as e:
            print(f"❌ Selenium automation error: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()

# MAIN EXECUTION
if __name__ == "__main__":
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
    GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY', 'jackjack04/kakunadx-data')
    
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not found!")
        exit(1)
    
    print(f"🚀 Starting Selenium automation for {GITHUB_REPO}...")
    
    scraper = SeleniumPokemonScraper(GITHUB_TOKEN, GITHUB_REPO)
    success = scraper.run_selenium_automation()
    
    if not success:
        exit(1)
