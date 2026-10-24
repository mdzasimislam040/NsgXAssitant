import os

API_ID = int(os.getenv("API_ID", "35999298"))
API_HASH = os.getenv("API_HASH", "69fd352462046b14e90b5e1f0fa66425")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8922485507:AAHpz1VX_MxCu-nqOOYxVXUKJpnhu58GlJA")
STRING_SESSION = os.getenv("STRING_SESSION", "1BVtsOLwBuy6RqUb-Ll5FJotXIxtKltHqzEhCyniCF1zIxyBMa9qxRghoK4pg4ITibEcPxBTxSaxyru8fet2KY9q2UTleqLR4tmX6G1hXDXzI_SfAuvVXWhwf21p01UyTs9DsHN2_4ebClRUkt27AM_BWemYmtGS-g-9O87WmOGGJyo_GNFgaUnHRc6OBTHzFE9YBkbh5rosz7WmJMSjCVR4F2zk62JZ-GxiF2EUdJngNisKhCqzmPn4igMdVwnFDtWJMvxi0ruPmorue_WmU2Cmosln2ArAqtXkGYfzZd4XCd9G29KknWUYT6CDLU-t5ttsfJkEh6WauP8PxOsM-dN6fkkX_irw=")

# Supergroup ID handling (-100 prefix support)
raw_log_id = os.getenv("LOG_GROUP_ID", "-1003703266540")
try:
    if raw_log_id and not raw_log_id.startswith("-100") and not raw_log_id.startswith("-"):
        LOG_GROUP_ID = int(f"-100{raw_log_id}")
    else:
        LOG_GROUP_ID = int(raw_log_id)
except Exception:
    LOG_GROUP_ID = 0

OWNER_ID = int(os.getenv("OWNER_ID", "7569652619"))
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "mongodb+srv://likeeadii80_db_user:BvxekuzSBMuULZmv@cluster0.08xzqdo.mongodb.net/?appName=Cluster0")
PORT = int(os.getenv("PORT", "10000"))

# Credit & Links
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/NSG_CHATE")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/NSG_CHEATS")
OWNER_URL = os.getenv("OWNER_URL", "https://t.me/NSG_CHEATS_ONWER")

RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")
PING_INTERVAL = int(os.getenv("PING_INTERVAL", "600"))

ASSISTANT_USERNAME = os.getenv("ASSISTANT_USERNAME", "Mitsuriass").replace("@", "")