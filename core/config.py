"""
🌸 Sakura Bot — core/config.py
Central configuration: all server IDs, role IDs, channel IDs, theme colours,
and tunable constants. Update this file if any IDs change on the server.
"""

import os

# ─────────────────────────────────────────────
#  SERVER  (reads from .env, falls back to hardcoded default)
# ─────────────────────────────────────────────
GUILD_ID = int(os.getenv("GUILD_ID", "1521335974783881306"))

# ─────────────────────────────────────────────
#  COLOURS  (hex → int)
# ─────────────────────────────────────────────
BASE_BLACK     = 0x0A0A0A
DEEP_CRIMSON   = 0x8B0000   # Primary accent
NEON_RED       = 0xFF073A   # Highlights / Warnings
BLOOD_RED      = 0x5C0000   # Secondary accent
OFF_WHITE      = 0xE8E8E8   # Text
MUTED_GREY     = 0x3A3A3A   # Disabled
SUCCESS_GREEN  = 0x2ECC71
ERROR_RED      = 0xE74C3C
WARNING_YELLOW = 0xF1C40F
INFO_BLUE      = 0x3498DB
GOLD           = 0xFFD700

# ─────────────────────────────────────────────
#  ROLE IDs
# ─────────────────────────────────────────────
ROLE_IDS = {
    # ── Staff track ───────────────────────────
    "owner":           1521348386991898847,
    "co_owner":        1521348385138020443,
    "developer":       1521348382390484992,
    "head_admin":      1521348380087812210,
    "admin":           1521348378380996608,
    "moderator":       1521348375952359596,
    "trial_moderator": 1521348374085767178,
    "event_manager":   1521348372102123560,
    "content_creator": 1521348370319409212,
    "streamer":        1521348368410869801,
    "volunteer":       1522077783021584414,
    "quarantined":     1522093422234832976, # Ticket-only role
    # ── Member rank track ─────────────────────
    "karma_legend":    1521447026028707922,
    "karma_elite":     1521447024053190768,
    "reaper":          1521447022144524388,
    "dragon_shadow":   1521447019967942726,
    "ronin":           1521447017618870442,
    "kitsune":         1521447015702200401,
    "fallen_blossom":  1521447012778639400,
    "crimson_soul":    1521447010442547232,
    "lost_soul":       1521447008445923499,
    # ── Utility ───────────────────────────────
    "verified":        1521348353592397834,
    "member":          1521348351487119520,
    "bots":            1521348349159014494,
}

# Staff roles (can use mod commands, see tickets/logs)
STAFF_ROLE_IDS = [
    ROLE_IDS["owner"],
    ROLE_IDS["co_owner"],
    ROLE_IDS["developer"],
    ROLE_IDS["head_admin"],
    ROLE_IDS["admin"],
    ROLE_IDS["moderator"],
    ROLE_IDS["trial_moderator"],
]

# Security System: Roles that trigger Anti-Nuke if assigned
CRITICAL_ROLE_IDS = [
    ROLE_IDS["head_admin"],
    ROLE_IDS["admin"],
    ROLE_IDS["moderator"],
    ROLE_IDS["trial_moderator"],
    ROLE_IDS["developer"],
]

# Security System: Roles authorized to assign critical roles
AUTHORIZED_ASSIGNER_IDS = [
    ROLE_IDS["owner"],
    ROLE_IDS["co_owner"],
]

# Level milestone roles  {level: role_id}  (low → high)
LEVEL_ROLES = {
    5:  ROLE_IDS["crimson_soul"],
    10: ROLE_IDS["fallen_blossom"],
    20: ROLE_IDS["kitsune"],
    30: ROLE_IDS["ronin"],
    40: ROLE_IDS["dragon_shadow"],
    50: ROLE_IDS["reaper"],
    60: ROLE_IDS["karma_elite"],
    70: ROLE_IDS["karma_legend"],
}

# ───────────────────────────────
#  CHANNEL IDs  (verified against live server 2026-07-01)
# ───────────────────────────────
CHANNEL_IDS = {
    # 🩸 THE GATE
    "verification":  1521555646414327971,   # ✅ verified live
    "announcements": 1521348040605040796,   # ✅ verified live
    "rules":         1521761311891918899,   # ✅ verified live
    "updates":       1521348051745374339,   # ✅ verified live
    "roles":         1521928646015844534,                    

    # 🗄️ UTILITY (Sakura-only, no category)
    "joins":         1521558685963386961,   # join log channel (actual)
    "moderator_only":1521761311891918902,   # hidden mod channel

    # 🖤 THE GARDEN
    "general":       1521348060494430248,
    "gaming_chat":   1521348062377938994,
    "other_games":   1521447476589232188,
    "memes":         1521447336847474849,
    "introductions": 1521479189138636912,   # ✅ corrected

    # 🎮 THE ARENA
    "fortnite_chat":     1521348064445464717,
    "custom_matchmaking":1521348175020163216,
    "looking_for_party": 1521447376970190898,
    "clips":             1521447394753908776,
    "settings":          1521447401985019955,

    # 🩸 THE SHRINE
    "suggestions":   1521348191222763560,
    "giveaways":     1521348184369004625,
    "events":        1521348186646778007,
    "partnerships":  1521348195236712609,
    "appeals":       1521348197149180005,
    "bug_reports":   1521447702725001358,
    "contact_staff": 1521447705107238912,

    # 🖤 CREATOR HUB
    "tiktok":        1521447695535833233,
    "twitch":        1521447693661245450,

    # ⚖️ KARMA COURT
    "create_ticket": 1521348193286095018,

    # 🖤 THE THRONE  (staff-only)
    "staff_chat":     1521348251154907229,
    "staff_commands": 1521348253038149794,
    "reports":        1521348255521177772,
    "logs":           1521348261586145341,   # General / voice / role logs
    "mod_logs":       1521348261586145341,   # Moderation action logs — TODO: split to own channel
    "join_leave_logs":1521558685963386961,   # ✅ mapped to actual #joins channel
    "ticket_logs":    1521348261586145341,  # Using #logs until a dedicated #ticket-logs channel is created — update when ready

    # 🖤 ECHO CHAMBERS
    "karma_lounge": 1521348228002480179,
    "gaming_vc_1":  1521348230363877376,
    "gaming_vc_2":  1521348232264028231,
    "duo_vc":       1521348234554114189,
    "trio_vc":      1521348239163523174,
    "squad_vc":     1521348243290591263,
    "afk":          1521348249078726726,
}

# Category IDs
CATEGORY_IDS = {
    "the_gate":       1521347876049912018,
    "the_garden":     1521347878176423956,
    "the_arena":      1521347880219049984,
    "other_games":    1521347890889490555,
    "the_shrine":     1521347882026795125,
    "the_underworld": 1521447193947537490,
    "dragons_den":    1521347892453965918,
    "creator_hub":    1521447195910471721,
    "karma_court":    1521347884698697808,
    "the_throne":     1521347888784080908,
    "echo_chambers":  1521347886510772318,
}

# ─────────────────────────────────────────────
#  XP / LEVELING CONSTANTS
# ─────────────────────────────────────────────
XP_MIN             = 15   # Minimum XP per eligible message
XP_MAX             = 25   # Maximum XP per eligible message
XP_COOLDOWN_SECONDS = 60  # Cooldown between XP awards per user

# Channels where XP is awarded (keys from CHANNEL_IDS)
XP_CHANNEL_KEYS = [
    "general",
    "gaming_chat",
    "fortnite_chat",
    "looking_for_party",
    "introductions",
    "clips",
    "memes",
    "other_games",
]

# ─────────────────────────────────────────────
#  WARN THRESHOLDS (auto-punishment escalation)
# ─────────────────────────────────────────────
WARN_TIMEOUT_THRESHOLD = 3   # 3 warns → 1 hour timeout
WARN_KICK_THRESHOLD    = 5   # 5 warns → kick
WARN_BAN_THRESHOLD     = 7   # 7 warns → ban

# ───────────────────────────────
#  VERIFICATION SETTINGS
# ───────────────────────────────
VERIFY_MIN_ACCOUNT_AGE_DAYS = 7   # Minimum Discord account age to pass verification

# ───────────────────────────────
#  AUTOMOD SETTINGS
# ───────────────────────────────
AUTOMOD_SPAM_COUNT   = 5    # Messages within the window before spam action
AUTOMOD_SPAM_WINDOW  = 5.0  # Sliding window in seconds for spam detection
AUTOMOD_MENTION_MAX  = 5    # Max unique @user mentions allowed per message
# Guild IDs whose Discord invites are permitted (add partner server IDs here)
AUTOMOD_ALLOWED_GUILDS: list[int] = [GUILD_ID]
# Channels exempt from automod (e.g. staff-only channels)
AUTOMOD_EXEMPT_CHANNELS: list[int] = [
    # CHANNEL_IDS values evaluated at runtime — populated from keys
    # This list is built in automod.py using config.CHANNEL_IDS
]
