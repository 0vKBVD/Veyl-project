# ============================================================
# VEYL CHART ENGINE
# Binance-first / CoinGecko fallback
# Centralized chart generation + cache + request deduplication
# ============================================================

import asyncio
import io
import time
import datetime
from typing import Optional

from services.providers.binance import get_chart as binance_get_chart

try:
    from services.providers.coingecko import get_chart as coingecko_get_chart
except Exception:
    coingecko_get_chart = None


# ============================================================
# CONFIG
# ============================================================

CHART_CACHE_TTL = 90
MAX_POINTS = 350

_chart_cache = {}
_chart_tasks = {}

_chart_lock = asyncio.Lock()


# ============================================================
# MATPLOTLIB
# ============================================================

try:
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True

except Exception:
    MATPLOTLIB_AVAILABLE = False

    print(
        "⚠️ VEYL Charts : matplotlib unavailable."
    )


# ============================================================
# CACHE
# ============================================================

def _cache_key(coin_id, days):
    return (
        str(coin_id).lower(),
        str(days),
    )


def clear_chart_cache():
    _chart_cache.clear()

    print(
        "⌘ VEYL Charts cache cleared."
    )


# ============================================================
# PROVIDER FETCH
# ============================================================

async def _fetch_chart(
    coin_id: str,
    days: int = 1,
):
    """
    Binance first.
    CoinGecko only if Binance fails.
    """

    # --------------------------------------------------------
    # BINANCE
    # --------------------------------------------------------

    try:

        data = await binance_get_chart(
            coin_id,
            days,
        )

        if data and data.get("prices"):

            data["provider"] = "binance"

            return data

    except Exception as error:

        print(
            f"⚠️ VEYL Charts Binance error: {error}"
        )

    # --------------------------------------------------------
    # COINGECKO FALLBACK
    # --------------------------------------------------------

    if coingecko_get_chart:

        try:

            data = await coingecko_get_chart(
                coin_id,
                days,
            )

            if data and data.get("prices"):

                data["provider"] = "coingecko"

                return data

        except Exception as error:

            print(
                f"⚠️ VEYL Charts CoinGecko error: {error}"
            )

    return None


# ============================================================
# CENTRAL CHART DATA
# ============================================================

async def get_chart_data(
    coin_id: str,
    days: int = 1,
    force: bool = False,
):
    """
    Central chart data function.

    Features:
    - cache
    - request deduplication
    - Binance first
    - CoinGecko fallback
    """

    key = _cache_key(
        coin_id,
        days,
    )

    now = time.monotonic()

    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    if not force:

        cached = _chart_cache.get(key)

        if cached:

            data, created = cached

            if (
                now - created
                < CHART_CACHE_TTL
            ):

                return data

    # --------------------------------------------------------
    # REQUEST DEDUPLICATION
    # --------------------------------------------------------

    async with _chart_lock:

        # Recheck cache after lock

        if not force:

            cached = _chart_cache.get(key)

            if cached:

                data, created = cached

                if (
                    time.monotonic()
                    - created
                    < CHART_CACHE_TTL
                ):

                    return data

        # Existing request

        task = _chart_tasks.get(key)

        if task is None:

            task = asyncio.create_task(
                _fetch_chart(
                    coin_id,
                    days,
                )
            )

            _chart_tasks[key] = task

    # --------------------------------------------------------
    # WAIT
    # --------------------------------------------------------

    try:

        data = await task

        if data:

            _chart_cache[key] = (
                data,
                time.monotonic(),
            )

        return data

    finally:

        async with _chart_lock:

            if _chart_tasks.get(key) is task:

                _chart_tasks.pop(
                    key,
                    None,
                )


# ============================================================
# NORMALIZE POINTS
# ============================================================

def _extract_points(chart_data):

    if not chart_data:
        return []

    prices = chart_data.get(
        "prices",
        [],
    )

    points = []

    for point in prices:

        if not isinstance(
            point,
            (list, tuple),
        ):
            continue

        if len(point) < 2:
            continue

        try:

            timestamp = float(
                point[0]
            )

            price = float(
                point[1]
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        if price <= 0:
            continue

        points.append(
            (
                timestamp,
                price,
            )
        )

    # --------------------------------------------------------
    # LIMIT POINT COUNT
    # --------------------------------------------------------

    if len(points) > MAX_POINTS:

        step = (
            len(points)
            / MAX_POINTS
        )

        sampled = []

        for i in range(MAX_POINTS):

            index = int(
                i * step
            )

            if index >= len(points):
                index = len(points) - 1

            sampled.append(
                points[index]
            )

        points = sampled

    return points


# ============================================================
# PRICE FORMAT
# ============================================================

def format_price(value):

    try:

        value = float(value)

    except (
        TypeError,
        ValueError,
    ):

        return "—"

    if value >= 1000:
        return f"${value:,.0f}"

    if value >= 1:
        return f"${value:,.2f}"

    if value >= 0.01:
        return f"${value:,.4f}"

    return f"${value:,.8f}"


# ============================================================
# GENERATE IMAGE
# ============================================================

def generate_chart_image(
    chart_data,
    symbol,
    name,
):

    if not MATPLOTLIB_AVAILABLE:
        return None

    points = _extract_points(
        chart_data
    )

    if len(points) < 2:
        return None

    timestamps = [
        p[0] / 1000
        for p in points
    ]

    prices = [
        p[1]
        for p in points
    ]

    try:

        dates = [
            datetime.datetime.fromtimestamp(
                timestamp
            )
            for timestamp in timestamps
        ]

        first_price = prices[0]
        last_price = prices[-1]

        if first_price:

            change = (
                (
                    last_price
                    - first_price
                )
                / first_price
            ) * 100

        else:

            change = 0

        # ----------------------------------------------------
        # FIGURE
        # ----------------------------------------------------

        fig, ax = plt.subplots(
            figsize=(14, 6),
            dpi=150,
        )

        fig.patch.set_facecolor("#080a0d")
        ax.set_facecolor("#080a0d")

        # Explicit light typography: Matplotlib defaults to black text,
        # which is unreadable on VEYL's dark chart background.
        text_color = "#e8e8e8"
        muted_color = "#9a9a9a"

        # ----------------------------------------------------
        # LINE
        # ----------------------------------------------------

        ax.plot(
            dates,
            prices,
            linewidth=2.4,
            color="#e8e8e8",
        )

        # ----------------------------------------------------
        # AREA
        # ----------------------------------------------------

        bottom = min(prices)

        ax.fill_between(
            dates,
            prices,
            bottom,
            alpha=0.08,
            color="#8a8a8a",
        )

        # ----------------------------------------------------
        # GRID
        # ----------------------------------------------------

        ax.grid(
            True,
            alpha=0.08,
            linewidth=0.6,
        )

        # ----------------------------------------------------
        # SPINES
        # ----------------------------------------------------

        ax.spines[
            "top"
        ].set_visible(False)

        ax.spines[
            "right"
        ].set_visible(False)

        ax.spines[
            "left"
        ].set_alpha(0.15)
        ax.spines["left"].set_color(muted_color)

        ax.spines[
            "bottom"
        ].set_alpha(0.15)
        ax.spines["bottom"].set_color(muted_color)

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        ax.set_title(
            f"VEYL // {name.upper()} ({symbol.upper()})",
            loc="left",
            fontsize=15,
            fontweight="bold",
            pad=18,
            color=text_color,
        )

        # ----------------------------------------------------
        # MARKET STATUS
        # ----------------------------------------------------

        provider = chart_data.get(
            "provider",
            "market",
        )

        ax.text(
            0,
            1.015,
            (
                f"{format_price(last_price)}"
                f"    {change:+.2f}%"
                f"    {provider.upper()}"
            ),
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="bottom",
            color=muted_color,
        )

        # ----------------------------------------------------
        # AXIS
        # ----------------------------------------------------

        ax.tick_params(
            axis="both",
            labelsize=8,
            colors=muted_color,
        )

        fig.autofmt_xdate()

        plt.tight_layout()

        # ----------------------------------------------------
        # EXPORT
        # ----------------------------------------------------

        buffer = io.BytesIO()

        fig.savefig(
            buffer,
            format="png",
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
        )

        plt.close(fig)

        buffer.seek(0)

        return buffer

    except Exception as error:

        print(
            f"❌ VEYL chart generation error: {error}"
        )

        try:
            plt.close("all")
        except Exception:
            pass

        return None


# ============================================================
# COMPLETE PIPELINE
# ============================================================

async def create_chart(
    coin_id,
    symbol,
    name,
    days=1,
):

    data = await get_chart_data(
        coin_id,
        days,
    )

    if not data:

        print(
            f"⚠️ VEYL Charts : "
            f"no data for {coin_id}."
        )

        return None

    # Matplotlib is synchronous.
    # Move generation to a worker thread so Discord
    # does not freeze while the image is being generated.

    return await asyncio.to_thread(
        generate_chart_image,
        data,
        symbol,
        name,
    )


# ============================================================
# STATUS
# ============================================================

def chart_engine_status():

    return {
        "engine": "VEYL CHART ENGINE",
        "status": "ONLINE",
        "cache_entries": len(
            _chart_cache
        ),
        "cache_ttl": CHART_CACHE_TTL,
        "max_points": MAX_POINTS,
        "binance": True,
        "coingecko_fallback": (
            coingecko_get_chart is not None
        ),
    }