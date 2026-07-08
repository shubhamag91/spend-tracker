from pathlib import Path
from pydantic_settings import BaseSettings


_DATA_DIR = Path(__file__).parent.parent.parent / "data"


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{_DATA_DIR / 'spend_tracker.db'}"
    watched_folder: str = str(_DATA_DIR / "watched_folder")
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    # Account-holder name(s) EXACTLY as they appear in your bank statements, used
    # to detect self / internal transfers between your own accounts (these are
    # excluded from income and spend analytics). Replace the placeholder with your
    # own name(s), or set ACCOUNT_HOLDER_NAMES in config/.env — see config/.env.example.
    account_holder_names: list[str] = ["YOUR_NAME_AS_IN_STATEMENTS"]
    # Investment-platform / fund names — flows to/from these are wealth, not
    # consumption (or real income), so they are pulled out of spend & income.
    # Applies to both debits (SIP purchases) and credits (redemptions).
    investment_keywords: list[str] = [
        "GRIP", "INDSTOCKS", "ZERODHA", "GROWW", "SMALLCASE", "KUVERA",
        "UPSTOX", "INDMONEY", "BROKING", "COIN DCX",
        "MUTUAL FUND", "WEALTH INDIA", "SIP ", "MOTILAL OSWAL", "CANARA ROBECO",
        "EDELWEISS", "NIPPON INDIA", "PARAG PARIKH", "MIRAE", "QUANT MUTUAL",
        "AXIS MUTUAL", "SBI MUTUAL", "HDFC MUTUAL", "ICICI PRU", "KOTAK MUTUAL",
        "UTI MUTUAL", "ADITYA BIRLA SUN", "DSP MUTUAL", "TATA MUTUAL", "FRANKLIN",
    ]
    # Credit-card bill payments — money settling a card where the actual spend
    # already happened on the card. Shown separately, not as category spend.
    card_payment_keywords: list[str] = [
        "CRED CLUB", "CRED.CLUB", "CREDITCARD", "CREDIT CARD", "CARD PAYMENT",
        "CC PAYMENT", "AUTOPAY-CRED", "BILLDESK CRED",
    ]
    # Poker settlements — money in/out of a private game, neither spend nor income.
    # Tagged into the "poker" bucket (and excluded from spend/income).
    poker_keywords: list[str] = ["KANSOUWA"]

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / "config" / ".env")


settings = Settings()
