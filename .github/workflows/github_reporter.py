import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import telegram
import asyncio

# ==================== CONFIG ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Authorization": f"token {GITHUB_TOKEN}" if GITHUB_TOKEN else None
}

# ===============================================

def get_trending(since="weekly"):
    """Récupère les trending repos"""
    url = f"https://github.com/trending?since={since}"
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    repos = []

    for article in soup.select('article.Box-row')[:12]:
        try:
            h1 = article.select_one('h2 a')
            full_name = h1.get('href')[1:]
            description_tag = article.select_one('p')
            description = description_tag.get_text(strip=True) if description_tag else "Aucune description"

            stars_tag = article.select_one('a[href$="/stargazers"]')
            stars = stars_tag.get_text(strip=True).replace(',', '').strip() if stars_tag else "0"

            language_tag = article.select_one('span[itemprop="programmingLanguage"]')
            language = language_tag.get_text(strip=True) if language_tag else "N/A"

            repos.append({
                "full_name": full_name,
                "description": description,
                "stars": int(stars) if stars.isdigit() else 0,
                "language": language,
                "url": f"https://github.com/{full_name}"
            })
        except:
            continue
    return repos


def get_petites():
    """Récupère les pépites : < 5000 stars + activité récente"""
    query = "stars:<5000 pushed:>2026-05-01"   # Modifiable selon la date
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=20"
    
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print("Erreur API GitHub:", resp.text)
        return []
    
    data = resp.json()
    return data.get('items', [])


def create_markdown_report(trending, petites):
    date = datetime.now().strftime("%d %B %Y")
    
    md = f"# GitHub Weekly Report - {date}\n\n"
    md += "## 🔥 Trending cette semaine\n\n"
    
    for i, repo in enumerate(trending, 1):
        md += f"**{i}. [{repo['full_name']}]({repo['url']})**  \n"
        md += f"⭐ {repo['stars']:,} stars • {repo['language']}  \n"
        md += f"{repo['description']}\n\n"
    
    md += "## 💎 Pépites (moins de 5000 stars mais qui montent fort)\n\n"
    
    for i, repo in enumerate(petites[:10], 1):
        stars = repo.get('stargazers_count', 0)
        md += f"**{i}. [{repo['full_name']}]({repo['html_url']})**  \n"
        md += f"⭐ {stars:,} stars • {repo.get('language', 'N/A')}  \n"
        md += f"{repo.get('description', 'Aucune description')}\n\n"
    
    md += f"\n*Rapport généré le {date}*"
    return md


async def send_to_telegram(report_md):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Résumé court
    summary = "📊 **GitHub Weekly Report** généré !\n\n"
    summary += "• Trending repos envoyés\n"
    summary += "• Pépites (hidden gems) détectées\n\n"
    summary += "Le rapport complet est en pièce jointe 📎"
    
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=summary, parse_mode='Markdown')
    
    # Envoi du fichier Markdown
    with open("github_report.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    
    await bot.send_document(
        chat_id=TELEGRAM_CHAT_ID,
        document=open("github_report.md", "rb"),
        filename=f"github_report_{datetime.now().strftime('%Y-%m-%d')}.md"
    )


# ==================== MAIN ====================
if __name__ == "__main__":
    print("🚀 Lancement du GitHub Weekly Report...")
    
    trending = get_trending("weekly")
    petites = get_petites()
    
    report = create_markdown_report(trending, petites)
    
    # Sauvegarde locale
    with open("github_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    # Envoi Telegram
    asyncio.run(send_to_telegram(report))
    
    print("✅ Rapport généré et envoyé sur Telegram !")
