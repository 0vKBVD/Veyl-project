import os
import json
import asyncio
from datetime import datetime, timezone


# ============================================================
# VEYL / USER DATA ENGINE
# ============================================================
#
# Persistent user system for:
#
#   • XP
#   • Levels
#   • Badges
#   • Commands used
#   • Watchlist counter
#   • Alerts counter
#   • Member since
#
# Data stored locally in:
#
#   data/users.json
#
# ============================================================


DATA_FOLDER = "data"
DATA_FILE = os.path.join(
    DATA_FOLDER,
    "users.json"
)


# ============================================================
# LOCK
# ============================================================

_DATA_LOCK = asyncio.Lock()


# ============================================================
# DEFAULT USER
# ============================================================

def default_user():

    return {
        "xp": 0,
        "commands_used": 0,
        "alerts": 0,
        "watchlist": [],
        "badges": [],
        "created_at": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ============================================================
# ENSURE DATA DIRECTORY
# ============================================================

def ensure_data_folder():

    os.makedirs(
        DATA_FOLDER,
        exist_ok=True
    )


# ============================================================
# LOAD DATABASE
# ============================================================

def load_users():

    ensure_data_folder()

    if not os.path.exists(
        DATA_FILE
    ):

        return {}

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(
            data,
            dict
        ):

            return data

    except (
        json.JSONDecodeError,
        OSError
    ):

        print(
            "⚠️ VEYL User Data • "
            "Unable to load users.json."
        )

    return {}


# ============================================================
# SAVE DATABASE
# ============================================================

def save_users(users):

    ensure_data_folder()

    temp_file = (
        DATA_FILE
        + ".tmp"
    )

    try:

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                users,
                file,
                indent=4,
                ensure_ascii=False
            )

        os.replace(
            temp_file,
            DATA_FILE
        )

        return True

    except OSError as error:

        print(
            f"❌ VEYL User Data • "
            f"Save error: {error}"
        )

        return False


# ============================================================
# GET USER
# ============================================================

def get_user(
    user_id
):

    user_id = str(
        user_id
    )

    users = load_users()

    if user_id not in users:

        users[user_id] = default_user()

        save_users(
            users
        )

    user = users[user_id]

    # --------------------------------------------------------
    # Safety migration for old data
    # --------------------------------------------------------

    defaults = default_user()

    for key, value in defaults.items():

        if key not in user:

            user[key] = value

    save_users(
        users
    )

    return user


# ============================================================
# UPDATE USER
# ============================================================

def update_user(
    user_id,
    user_data
):

    user_id = str(
        user_id
    )

    users = load_users()

    users[user_id] = user_data

    save_users(
        users
    )


# ============================================================
# XP REQUIRED
# ============================================================

def xp_required_for_level(
    level
):

    if level <= 1:

        return 0

    # Progressive XP curve.
    return int(
        100
        * (level - 1)
        * (level - 1)
        + 100
        * (level - 1)
        / 2
    )


# ============================================================
# CALCULATE LEVEL
# ============================================================

def calculate_level(
    xp
):

    xp = max(
        0,
        int(xp)
    )

    level = 1

    while (
        xp_required_for_level(
            level + 1
        )
        <= xp
    ):

        level += 1

        if level >= 100:

            break

    return level


# ============================================================
# LEVEL PROGRESS
# ============================================================

def get_level_progress(
    xp
):

    level = calculate_level(
        xp
    )

    current_level_xp = (
        xp_required_for_level(
            level
        )
    )

    next_level_xp = (
        xp_required_for_level(
            level + 1
        )
    )

    if level >= 99:

        return {
            "level": level,
            "current": xp,
            "required": xp,
            "remaining": 0,
            "percentage": 100
        }

    progress_xp = (
        xp
        - current_level_xp
    )

    required_xp = (
        next_level_xp
        - current_level_xp
    )

    percentage = (
        progress_xp
        / required_xp
        * 100
        if required_xp > 0
        else 100
    )

    return {
        "level": level,
        "current": progress_xp,
        "required": required_xp,
        "remaining": max(
            0,
            next_level_xp - xp
        ),
        "percentage": min(
            100,
            percentage
        )
    }


# ============================================================
# ADD XP
# ============================================================

def add_xp(
    user_id,
    amount
):

    user_id = str(
        user_id
    )

    amount = max(
        0,
        int(amount)
    )

    users = load_users()

    if user_id not in users:

        users[user_id] = default_user()

    user = users[user_id]

    old_level = calculate_level(
        user.get(
            "xp",
            0
        )
    )

    user["xp"] = (
        user.get(
            "xp",
            0
        )
        + amount
    )

    new_level = calculate_level(
        user["xp"]
    )

    save_users(
        users
    )

    return {
        "xp_added": amount,
        "xp": user["xp"],
        "old_level": old_level,
        "new_level": new_level,
        "level_up": (
            new_level > old_level
        )
    }


# ============================================================
# COMMAND TRACKING
# ============================================================

def track_command(
    user_id,
    xp_amount=10
):

    user_id = str(
        user_id
    )

    users = load_users()

    if user_id not in users:

        users[user_id] = default_user()

    user = users[user_id]

    user["commands_used"] = (
        user.get(
            "commands_used",
            0
        )
        + 1
    )

    old_level = calculate_level(
        user.get(
            "xp",
            0
        )
    )

    user["xp"] = (
        user.get(
            "xp",
            0
        )
        + max(
            0,
            xp_amount
        )
    )

    new_level = calculate_level(
        user["xp"]
    )

    save_users(
        users
    )

    return {
        "xp_added": xp_amount,
        "xp": user["xp"],
        "commands_used": user[
            "commands_used"
        ],
        "old_level": old_level,
        "new_level": new_level,
        "level_up": (
            new_level > old_level
        )
    }


# ============================================================
# BADGES
# ============================================================

def add_badge(
    user_id,
    badge
):

    user_id = str(
        user_id
    )

    users = load_users()

    if user_id not in users:

        users[user_id] = default_user()

    user = users[user_id]

    if badge not in user["badges"]:

        user["badges"].append(
            badge
        )

        save_users(
            users
        )

        return True

    return False


# ============================================================
# WATCHLIST
# ============================================================

def add_watchlist_asset(
    user_id,
    asset
):

    user_id = str(
        user_id
    )

    users = load_users()

    if user_id not in users:

        users[user_id] = default_user()

    user = users[user_id]

    asset = asset.strip().upper()

    if asset not in user["watchlist"]:

        user["watchlist"].append(
            asset
        )

        save_users(
            users
        )

        return True

    return False


# ============================================================
# REMOVE WATCHLIST ASSET
# ============================================================

def remove_watchlist_asset(
    user_id,
    asset
):

    user_id = str(
        user_id
    )

    users = load_users()

    if user_id not in users:

        return False

    asset = asset.strip().upper()

    if asset in users[user_id]["watchlist"]:

        users[user_id]["watchlist"].remove(
            asset
        )

        save_users(
            users
        )

        return True

    return False


# ============================================================
# GET ALL USERS
# ============================================================

def get_all_users():

    return load_users()


# ============================================================
# RANK
# ============================================================

def get_user_rank(
    user_id
):

    user_id = str(
        user_id
    )

    users = load_users()

    sorted_users = sorted(
        users.items(),
        key=lambda item: item[1].get(
            "xp",
            0
        ),
        reverse=True
    )

    for index, (
        current_id,
        _
    ) in enumerate(
        sorted_users,
        start=1
    ):

        if current_id == user_id:

            return index

    return None