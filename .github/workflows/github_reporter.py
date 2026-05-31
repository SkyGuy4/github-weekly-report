import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime

# ==================== CONFIG ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ===============================================

def get_trending(since="weekly"):
    url = f"https://github.com/trending?since={since}"
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    repos = []

    for article in soup.select('article.Box-row')[:12]:
        try:
            h1 = article.select_one('h2 a')
            full_name = h1.get('href')[1:]
            desc_tag = article.select_one('p')
            description = desc_tag.get_text(strip=True) if desc_tag else "Aucune description"
            
            stars_tag = article.select_one('a[href$="/stargazers"]')
            stars_str = stars_tag.get_text(strip=True).replace(',', '') if stars_tag else "0"
            stars = int(stars_str) if stars_str.isdigit() else 0

            lang_tag = article.select_one('span[itemprop="programmingLanguage"]')
            language = lang_tag.get_text(strip=True) if lang_tag else "N/A"

            repos.append({
                "full_name": full_name,
                "description": description,
                "stars": stars,
                "language": language,
                "url": f"https://github.com/{full_name}"
            })
        except:
            continue
    return repos


def get_petites():
    query = "stars:<5000 pushed:>2026-05-01"
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=15"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print("Erreur API:", resp.text)
        return []
    return resp.json().get('items', [])


def create_markdown_report(trending, petites):
    date_str = datetime.now().strftime("%d %B %Y à %H:%M")
    
    md = f"# GitHub Weekly Report - {date_str}\n\n"
    md += "## 🔥 Trending cette semaine\n\n"
    
    for i, r in enumerate(trending, 1):
        md += f"**{i}. [{r['full_name']}]({r['url']})**\n"
        md += f"⭐ {r['stars']:,} • {r['language']}\n"
        md += f"{r['description']}\n\n"
    
    md += "## 💎 Pépites (< 5000 stars)\n\n"
    for i, r in enumerate(petites[:10], 1):
        stars = r.get('stargazers_count', 0)
        md += f"**{i}. [{r['full_name']}]({r['html_url']})**\n"
        md += f"⭐ {stars:,} • {r.get('language', 'N/A')}\n"
        md += f"{r.get('description', 'Pas de description')}\n\n"
    
    md += f"\n*Rapport généré le {date_str}*"
    return md


def send_telegram(summary, report_md):
    # Message résumé
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": summary,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

    # Envoi du fichier Markdown
    url_file = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    files = {'document': ('github_report.md', report_md.encode('utf-8'))}
    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": "📎 Rapport complet"}
    requests.post(url_file, data=data, files=files)


# ==================== MAIN ====================
if __name__ == "__main__":
    print("🚀 Lancement du rapport...")

    trending = get_trending("weekly")
    petites = get_petites()

    report_md = create_markdown_report(trending, petites)

    summary = "📊 **GitHub Weekly Report** prêt !\n\n" \
              "• Trending repos\n" \
              "• Pépites détectées\n\n" \
              "Rapport détaillé en pièce jointe."

    send_telegram(summary, report_md)

    # Sauvegarde dans le repo
    with open("github_report.md", "w", encoding="utf-8") as f:
        f.write(report_md)

    print("✅ Rapport généré et envoyé sur Telegram")
