import os
import sys
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ==================== CONFIG ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# L'API de recherche GitHub peut bloquer sans un bon User-Agent
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_trending(since="weekly"):
    url = f"https://github.com/trending?since={since}"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"❌ Échec de la récupération des trending: HTTP {resp.status_code}")
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        repos = []

        for article in soup.select("article.Box-row")[:12]:
            try:
                h1 = article.select_one("h2 a")
                full_name = h1.get("href")[1:]
                desc_tag = article.select_one("p")
                description = (
                    desc_tag.get_text(strip=True)
                    if desc_tag
                    else "Aucune description"
                )

                stars_tag = article.select_one('a[href$="/stargazers"]')
                stars_str = (
                    stars_tag.get_text(strip=True).replace(",", "")
                    if stars_tag
                    else "0"
                )
                stars = int(stars_str) if stars_str.isdigit() else 0

                lang_tag = article.select_one(
                    'span[itemprop="programmingLanguage"]'
                )
                language = lang_tag.get_text(strip=True) if lang_tag else "N/A"

                repos.append(
                    {
                        "full_name": full_name,
                        "description": description,
                        "stars": stars,
                        "language": language,
                        "url": f"https://github.com/{full_name}",
                    }
                )
            except Exception as e:
                print(f"⚠️ Erreur lors du parsing d'un item trending: {e}")
                continue
        return repos
    except Exception as e:
        print(f"❌ Erreur durant le scraping des trending: {e}")
        return []


def get_petites():
    # Recherche des repos mis à jour récemment avec moins de 5000 stars
    query = "stars:<5000 pushed:>2026-03-01"
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=15"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"❌ Erreur API GitHub: HTTP {resp.status_code} - {resp.text}")
            return []
        return resp.json().get("items", [])
    except Exception as e:
        print(f"❌ Erreur durant la recherche API: {e}")
        return []


def create_markdown_report(trending, petites):
    date_str = datetime.now().strftime("%d %B %Y à %H:%M")

    md = f"# GitHub Weekly Report - {date_str}\n\n"
    md += "## 🔥 Trending cette semaine\n\n"

    if not trending:
        md += "_Aucun repo trending trouvé cette semaine ou blocage temporaire._\n\n"
    for i, r in enumerate(trending, 1):
        md += f"**{i}. [{r['full_name']}]({r['url']})**\n"
        md += f"⭐ {r['stars']:,} • {r['language']}\n"
        md += f"{r['description']}\n\n"

    md += "## 💎 Pépites (< 5000 stars)\n\n"
    if not petites:
        md += "_Aucune pépite trouvée (Vérifier les quotas d'API)._\n\n"
    for i, r in enumerate(petites[:10], 1):
        stars = r.get("stargazers_count", 0)
        md += f"**{i}. [{r['full_name']}]({r['html_url']})**\n"
        md += f"⭐ {stars:,} • {r.get('language', 'N/A')}\n"
        md += f"{r.get('description', 'Pas de description')}\n\n"

    md += f"\n*Rapport généré le {date_str}*"
    return md


def send_telegram(summary, report_md):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Les identifiants Telegram sont introuvables dans les variables d'environnement !")
        sys.exit(1)

    # 1. Envoi du résumé texte
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": summary,
        "parse_mode": "Markdown",
    }
    r1 = requests.post(url, json=payload, timeout=10)
    print(f"Réponse Telegram (Texte): {r1.status_code}")

    # 2. Envoi du document Markdown
    url_file = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    files = {"document": ("github_report.md", report_md.encode("utf-8"))}
    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": "📎 Rapport complet"}
    r2 = requests.post(url_file, data=data, files=files, timeout=10)
    print(f"Réponse Telegram (Document): {r2.status_code}")


# ==================== MAIN ====================
if __name__ == "__main__":
    print("🚀 Lancement du rapport...")

    trending_repos = get_trending("weekly")
    petites_repos = get_petites()

    report = create_markdown_report(trending_repos, petites_repos)

    summary_text = (
        "Automated Update:\n\n"
        "📊 *GitHub Weekly Report* prêt !\n"
        "• Trending repos collectés\n"
        "• Pépites filtrées\n\n"
        "Regarde le fichier joint pour le détail."
    )

    send_telegram(summary_text, report)

    with open("github_report.md", "w", encoding="utf-8") as f:
        f.write(report)

    print("✅ Processus complété avec succès !")
