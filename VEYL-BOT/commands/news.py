import asyncio
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

import discord
from discord.ext import tasks


# ============================================================
# CONFIGURATION
# ============================================================

MARKET_NEWS_CHANNEL_ID = 1542846259130531930

# Vérification des sources toutes les 5 minutes
UPDATE_INTERVAL = 300

# Maximum de news publiées par jour
MAX_NEWS_PER_DAY = 5

# Score minimum pour publier une news
MIN_SCORE = 70

# Fichier contenant les articles déjà vus
SEEN_FILE = "news_seen.json"

# Fichier contenant le compteur quotidien
DAILY_FILE = "news_daily.json"

# Nombre maximum d'articles gardés en mémoire
MAX_SEEN = 500


# ============================================================
# SOURCES RSS
# ============================================================

RSS_FEEDS = {

    "CoinDesk": [
        "https://www.coindesk.com/arc/outboundfeeds/rss/"
    ],

    "Cointelegraph": [
        "https://cointelegraph.com/rss"
    ],

}


# ============================================================
# MOTS-CLES DE SCORE
# ============================================================

# Très grosse actualité
BREAKING_KEYWORDS = [

    "bitcoin etf",
    "ethereum etf",
    "solana etf",

    "sec approves",
    "sec approval",
    "sec rejects",

    "fed cuts",
    "fed raises",
    "interest rate",

    "hack",
    "exploit",
    "hacked",

    "bankruptcy",
    "bankrupt",

    "billion",
    "trillion",

    "acquisition",
    "merger",

    "major regulation",
    "new regulation",

]


# Régulation
REGULATION_KEYWORDS = [

    "sec",
    "securities and exchange commission",

    "regulation",
    "regulatory",

    "regulator",
    "regulators",

    "law",
    "laws",

    "legislation",

    "congress",

    "government",

    "ban",
    "banned",

    "legal",

    "illegal",

    "court",

    "lawsuit",

    "cftc",

    "fca",

    "esma",

]


# Marché
MARKET_KEYWORDS = [

    "bitcoin",

    "ethereum",

    "solana",

    "crypto market",

    "market cap",

    "trading volume",

    "price",

    "surges",

    "surge",

    "rally",

    "crash",

    "drops",

    "drop",

    "bull",

    "bear",

    "liquidation",

    "liquidations",

    "etf",

    "inflows",

    "outflows",

]


# Crypto / industrie
CRYPTO_KEYWORDS = [

    "crypto",

    "cryptocurrency",

    "blockchain",

    "web3",

    "defi",

    "stablecoin",

    "token",

    "wallet",

    "exchange",

    "binance",

    "coinbase",

    "ethereum",

    "bitcoin",

    "solana",

]


# Mots qui réduisent fortement la qualité
LOW_VALUE_KEYWORDS = [

    "price prediction",

    "could reach",

    "technical analysis",

    "weekly outlook",

    "daily outlook",

    "analyst says",

    "here's why",

    "top 10",

    "best crypto",

    "altcoin to buy",

    "should you buy",

    "how to buy",

    "tutorial",

]


# Publicité / contenu sponsorisé
BLOCKED_KEYWORDS = [

    "sponsored",

    "advertisement",

    "press release",

    "promoted",

    "partner content",

]


# ============================================================
# UTILITAIRES
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def truncate(text, length):

    if len(text) <= length:
        return text

    return text[:length - 3] + "..."


# ============================================================
# HISTORIQUE
# ============================================================

def load_seen():

    if not os.path.exists(SEEN_FILE):
        return []

    try:

        with open(
            SEEN_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return data

    except Exception:

        pass

    return []


def save_seen(seen):

    with open(
        SEEN_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            seen[-MAX_SEEN:],
            file,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# COMPTEUR QUOTIDIEN
# ============================================================

def load_daily():

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    if not os.path.exists(DAILY_FILE):

        return {
            "date": today,
            "count": 0
        }

    try:

        with open(
            DAILY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if data.get("date") != today:

            return {
                "date": today,
                "count": 0
            }

        return data

    except Exception:

        return {
            "date": today,
            "count": 0
        }


def save_daily(data):

    with open(
        DAILY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )


# ============================================================
# RSS
# ============================================================

def fetch_rss(url):

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 VEYL Market News Bot"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=15
    ) as response:

        return response.read()


def parse_rss(xml_data, source):

    articles = []

    try:

        root = ET.fromstring(
            xml_data
        )

    except ET.ParseError:

        return []

    # --------------------------------------------------------
    # RSS
    # --------------------------------------------------------

    for item in root.findall(
        ".//item"
    ):

        title = item.findtext(
            "title"
        )

        link = item.findtext(
            "link"
        )

        description = item.findtext(
            "description"
        )

        guid = item.findtext(
            "guid"
        )

        pub_date = item.findtext(
            "pubDate"
        )

        if not title or not link:
            continue

        title = clean_text(
            title
        )

        description = clean_text(
            description
        )

        identifier = (
            guid
            or link
            or title
        )

        articles.append(
            {
                "id": identifier,
                "title": title,
                "description": description,
                "link": link.strip(),
                "date": pub_date or "",
                "source": source
            }
        )

    # --------------------------------------------------------
    # ATOM
    # --------------------------------------------------------

    if not articles:

        namespace = {
            "atom":
                "http://www.w3.org/2005/Atom"
        }

        for entry in root.findall(
            "atom:entry",
            namespace
        ):

            title_element = entry.find(
                "atom:title",
                namespace
            )

            link_element = entry.find(
                "atom:link",
                namespace
            )

            summary_element = entry.find(
                "atom:summary",
                namespace
            )

            id_element = entry.find(
                "atom:id",
                namespace
            )

            if title_element is None:
                continue

            title = clean_text(
                title_element.text or ""
            )

            link = ""

            if link_element is not None:

                link = link_element.attrib.get(
                    "href",
                    ""
                )

            description = ""

            if summary_element is not None:

                description = clean_text(
                    summary_element.text or ""
                )

            identifier = (
                (
                    id_element.text
                    if id_element is not None
                    else None
                )
                or link
                or title
            )

            if not link:
                continue

            articles.append(
                {
                    "id": identifier,
                    "title": title,
                    "description": description,
                    "link": link,
                    "date": "",
                    "source": source
                }
            )

    return articles


# ============================================================
# CLASSIFICATION
# ============================================================

def get_category(article):

    content = (
        article["title"]
        + " "
        + article["description"]
    ).lower()

    # Breaking en priorité
    for keyword in BREAKING_KEYWORDS:

        if keyword in content:

            return "BREAKING"

    # Regulation
    for keyword in REGULATION_KEYWORDS:

        if keyword in content:

            return "REGULATION"

    # Market
    for keyword in MARKET_KEYWORDS:

        if keyword in content:

            return "MARKET"

    # Crypto
    for keyword in CRYPTO_KEYWORDS:

        if keyword in content:

            return "CRYPTO"

    return "CRYPTO"


def calculate_score(article):

    content = (
        article["title"]
        + " "
        + article["description"]
    ).lower()

    score = 50

    # --------------------------------------------------------
    # BREAKING
    # --------------------------------------------------------

    for keyword in BREAKING_KEYWORDS:

        if keyword in content:

            score += 25

    # --------------------------------------------------------
    # REGULATION
    # --------------------------------------------------------

    for keyword in REGULATION_KEYWORDS:

        if keyword in content:

            score += 10

    # --------------------------------------------------------
    # MARKET
    # --------------------------------------------------------

    for keyword in MARKET_KEYWORDS:

        if keyword in content:

            score += 6

    # --------------------------------------------------------
    # CRYPTO
    # --------------------------------------------------------

    for keyword in CRYPTO_KEYWORDS:

        if keyword in content:

            score += 3

    # --------------------------------------------------------
    # LOW VALUE
    # --------------------------------------------------------

    for keyword in LOW_VALUE_KEYWORDS:

        if keyword in content:

            score -= 20

    # --------------------------------------------------------
    # BLOCKED
    # --------------------------------------------------------

    for keyword in BLOCKED_KEYWORDS:

        if keyword in content:

            score = 0

    # Limite
    score = max(
        0,
        min(
            score,
            100
        )
    )

    return score


def is_blocked(article):

    content = (
        article["title"]
        + " "
        + article["description"]
    ).lower()

    for keyword in BLOCKED_KEYWORDS:

        if keyword in content:

            return True

    return False


# ============================================================
# NEWS MANAGER
# ============================================================

class MarketNews:

    def __init__(self, bot):

        self.bot = bot

        self.seen = load_seen()

        self.update_news.start()

    def cog_unload(self):

        self.update_news.cancel()

    async def fetch_all_news(self):

        all_articles = []

        for source, feeds in RSS_FEEDS.items():

            for feed_url in feeds:

                try:

                    xml_data = await asyncio.to_thread(
                        fetch_rss,
                        feed_url
                    )

                    articles = await asyncio.to_thread(
                        parse_rss,
                        xml_data,
                        source
                    )

                    all_articles.extend(
                        articles
                    )

                except Exception as error:

                    print(
                        f"⚠️ {source} RSS error : "
                        f"{error}"
                    )

        return all_articles

    async def publish_article(
        self,
        channel,
        article
    ):

        score = calculate_score(
            article
        )

        category = get_category(
            article
        )

        # ----------------------------------------------------
        # EMOJIS
        # ----------------------------------------------------

        category_data = {

            "BREAKING": (
                "🔥",
                discord.Color.red()
            ),

            "MARKET": (
                "📈",
                discord.Color.green()
            ),

            "REGULATION": (
                "🏛️",
                discord.Color.orange()
            ),

            "CRYPTO": (
                "🪙",
                discord.Color.blurple()
            ),

        }

        emoji, color = category_data.get(
            category,
            ("🪙", discord.Color.blurple())
        )

        title = truncate(
            article["title"],
            256
        )

        description = article[
            "description"
        ]

        if not description:

            description = (
                "New crypto market news."
            )

        description = truncate(
            description,
            700
        )

        embed = discord.Embed(
            title=f"{emoji} {category}",
            description=(
                f"**{title}**\n\n"
                f"{description}"
            ),
            url=article["link"],
            color=color
        )

        embed.add_field(
            name="SOURCE",
            value=f"**{article['source']}**",
            inline=True
        )

        embed.add_field(
            name="IMPORTANCE",
            value=f"**{score}/100**",
            inline=True
        )

        if article["date"]:

            embed.add_field(
                name="PUBLISHED",
                value=article["date"],
                inline=False
            )

        embed.set_footer(
            text="VEYL • Market News"
        )

        await channel.send(
            embed=embed
        )

    # ========================================================
    # MAIN LOOP
    # ========================================================

    @tasks.loop(seconds=UPDATE_INTERVAL)
    async def update_news(self):

        try:

            channel = await self.bot.fetch_channel(
                MARKET_NEWS_CHANNEL_ID
            )

            if not isinstance(
                channel,
                discord.TextChannel
            ):

                print(
                    "❌ MARKET_NEWS_CHANNEL_ID "
                    "n'est pas un salon texte."
                )

                return

            daily = load_daily()

            # ------------------------------------------------
            # LIMITE QUOTIDIENNE
            # ------------------------------------------------

            if daily["count"] >= MAX_NEWS_PER_DAY:

                print(
                    f"📰 Limite quotidienne atteinte "
                    f"({MAX_NEWS_PER_DAY}/{MAX_NEWS_PER_DAY})."
                )

                return

            # ------------------------------------------------
            # RECUPERATION
            # ------------------------------------------------

            articles = await self.fetch_all_news()

            if not articles:

                print(
                    "ℹ️ Aucune news trouvée."
                )

                return

            candidates = []

            # ------------------------------------------------
            # FILTRAGE
            # ------------------------------------------------

            for article in articles:

                article_id = article["id"]

                if article_id in self.seen:
                    continue

                if is_blocked(article):
                    continue

                score = calculate_score(
                    article
                )

                if score < MIN_SCORE:
                    continue

                article["score"] = score

                candidates.append(
                    article
                )

            if not candidates:

                print(
                    "ℹ️ Aucune news suffisamment importante."
                )

                return

            # ------------------------------------------------
            # MEILLEURES NEWS EN PREMIER
            # ------------------------------------------------

            candidates.sort(
                key=lambda article:
                    article["score"],
                reverse=True
            )

            remaining = (
                MAX_NEWS_PER_DAY
                - daily["count"]
            )

            selected = candidates[
                :remaining
            ]

            # ------------------------------------------------
            # PUBLICATION
            # ------------------------------------------------

            for article in selected:

                try:

                    await self.publish_article(
                        channel,
                        article
                    )

                    self.seen.append(
                        article["id"]
                    )

                    daily["count"] += 1

                    print(
                        f"📰 News publiée "
                        f"[{article['score']}/100] "
                        f"[{get_category(article)}] : "
                        f"{article['title']}"
                    )

                    save_daily(
                        daily
                    )

                    await asyncio.sleep(
                        3
                    )

                except Exception as error:

                    print(
                        f"❌ Publication impossible : "
                        f"{error}"
                    )

            # ------------------------------------------------
            # SAUVEGARDE
            # ------------------------------------------------

            self.seen = self.seen[
                -MAX_SEEN:
            ]

            save_seen(
                self.seen
            )

        except discord.NotFound:

            print(
                "❌ Salon Market News introuvable."
            )

        except discord.Forbidden:

            print(
                "❌ VEYL n'a pas la permission "
                "d'envoyer des messages."
            )

        except Exception as error:

            print(
                f"❌ Erreur Market News : "
                f"{error}"
            )

    @update_news.before_loop
    async def before_update(self):

        await self.bot.wait_until_ready()

        await asyncio.sleep(
            5
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    if MARKET_NEWS_CHANNEL_ID == 0:

        print(
            "⚠️ Configure "
            "MARKET_NEWS_CHANNEL_ID "
            "dans commands/news.py"
        )

        return

    bot.market_news = MarketNews(
        bot
    )

    print(
        "📰 Market News activé."
    )