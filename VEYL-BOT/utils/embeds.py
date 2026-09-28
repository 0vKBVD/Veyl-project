import discord


def create_price_embed(data):

    change = data["change_24h"]

    if change >= 0:

        color = discord.Color.green()
        arrow = "🟢 ▲"

    else:

        color = discord.Color.red()
        arrow = "🔴 ▼"

    price = data["price"]

    if price >= 1:

        price_text = f"${price:,.2f}"

    else:

        price_text = f"${price:,.8f}"

    embed = discord.Embed(
        title=(
            f"VEYL • {data['name']} "
            f"({data['symbol']})"
        ),
        description=f"# {price_text}",
        color=color
    )

    embed.add_field(
        name="24H",
        value=f"{arrow} {change:.2f}%",
        inline=True
    )

    embed.add_field(
        name="Market Cap",
        value=(
            f"${data['market_cap']:,.0f}"
        ),
        inline=True
    )

    embed.add_field(
        name="Volume 24H",
        value=(
            f"${data['volume_24h']:,.0f}"
        ),
        inline=True
    )

    embed.set_footer(
        text="VEYL • Live Market Data"
    )

    return embed