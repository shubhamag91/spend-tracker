import json

DEFAULT_CATEGORIES = [
    {
        "name": "Food & Dining",
        "color": "#f97316",
        "keywords": ["zomato", "swiggy", "dominos", "mcdonald", "pizza", "kfc", "subway", "burger", "cafe", "restaurant", "biryani", "dunzo", "blinkit food"],
    },
    {
        "name": "Transport",
        "color": "#3b82f6",
        "keywords": ["uber", "ola", "rapido", "irctc", "makemytrip", "goibibo", "metro", "petrol", "fuel", "indigo", "air india", "spicejet", "redbus"],
    },
    {
        "name": "Groceries",
        "color": "#22c55e",
        "keywords": ["bigbasket", "zepto", "blinkit", "grofers", "dmart", "reliance fresh", "more supermarket", "nature basket", "supermarket"],
    },
    {
        "name": "Shopping",
        "color": "#a855f7",
        "keywords": ["amazon", "flipkart", "myntra", "ajio", "nykaa", "meesho", "snapdeal", "tatacliq", "croma", "vijay sales"],
    },
    {
        "name": "Utilities",
        "color": "#64748b",
        # cred.telecom / cred.utility are phone and utility bills paid *through* CRED —
        # the UPI handle is the only clue to what was actually bought.
        "keywords": ["airtel", "jio", "bsnl", "electricity", "bescom", "tatapower", "adani electric", "gas", "water bill", "broadband", "recharge", "cred.telecom", "cred.utility"],
    },
    {
        "name": "Entertainment",
        "color": "#ec4899",
        "keywords": ["netflix", "hotstar", "spotify", "youtube", "bookmyshow", "pvr", "inox", "prime video", "zee5", "sonyliv", "gaming"],
    },
    {
        "name": "Health",
        "color": "#06b6d4",
        "keywords": ["pharmeasy", "netmeds", "1mg", "apollo", "practo", "medplus", "hospital", "clinic", "pharmacy", "doctor", "diagnostic"],
    },
    {
        "name": "Finance",
        "color": "#eab308",
        "keywords": ["mutual fund", "zerodha", "groww", "sip", "insurance", "lic", "hdfc life", "emi", "loan", "fd", "ppf"],
    },
    {
        "name": "Personal Care",
        "color": "#f43f5e",
        "keywords": ["salon", "spa", "haircut", "gym", "fitness", "cult.fit", "urban clap", "urbancompany"],
    },
    {
        "name": "Education",
        "color": "#8b5cf6",
        "keywords": ["udemy", "coursera", "byju", "unacademy", "book", "stationery", "school fee", "college fee", "tuition"],
    },
]
