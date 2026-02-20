
from flask import Flask, render_template, request, jsonify, session
from datetime import datetime, timedelta
import json
import uuid
import heapq
import re
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "tablemate-secret-2024"

# ============================================================
# DATA MODELS
# ============================================================

class Restaurant:
    def __init__(self, name, cuisine, capacity, hours):
        self.name = name
        self.cuisine = cuisine
        self.capacity = capacity  # {table_size: count}
        self.hours = hours
        self.tables = self._init_tables()
        self.reservations = {}   # conf_num -> Reservation
        self.waitlist = WaitlistManager()

    def _init_tables(self):
        """Initialize tables from capacity config."""
        tables = {}
        tid = 1
        for size, count in self.capacity.items():
            for _ in range(count):
                tables[f"T{tid}"] = {
                    "id": f"T{tid}",
                    "size": size,
                    "status": "available",
                    "reservation": None
                }
                tid += 1
        return tables

    def get_available_tables(self, party_size, date, time):
        """Find optimal table for party using bin-packing heuristic."""
        candidates = []
        for tid, table in self.tables.items():
            if table["status"] == "available" and table["size"] >= party_size:
                # Score: prefer smallest table that fits (waste minimization)
                waste = table["size"] - party_size
                candidates.append((waste, tid, table))
        candidates.sort(key=lambda x: x[0])  # Sort by waste ascending
        return candidates

    def to_dict(self):
        available = sum(1 for t in self.tables.values() if t["status"] == "available")
        return {
            "name": self.name,
            "cuisine": self.cuisine,
            "hours": self.hours,
            "total_tables": len(self.tables),
            "available_tables": available,
            "occupancy_pct": round((1 - available/len(self.tables)) * 100)
        }


class Reservation:
    def __init__(self, name, party_size, date, time, restaurant, table_id, special="", dietary=""):
        self.conf_num = f"TM{str(uuid.uuid4())[:5].upper()}"
        self.name = name
        self.party_size = party_size
        self.date = date
        self.time = time
        self.restaurant = restaurant
        self.table_id = table_id
        self.special = special
        self.dietary = dietary
        self.created_at = datetime.now()
        self.status = "confirmed"

    def to_dict(self):
        return {
            "conf_num": self.conf_num,
            "name": self.name,
            "party_size": self.party_size,
            "date": self.date,
            "time": self.time,
            "restaurant": self.restaurant,
            "table_id": self.table_id,
            "special": self.special,
            "dietary": self.dietary,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }


class WaitlistManager:
    """Priority queue based waitlist: smaller parties get tables faster."""
    def __init__(self):
        self._queue = []  # min-heap: (wait_priority, timestamp, entry)
        self._counter = 0

    def add(self, name, party_size):
        timestamp = datetime.now()
        # Priority: smaller parties prioritized (get seated faster)
        priority = party_size * 10 + self._counter
        entry = {
            "id": self._counter,
            "name": name,
            "party_size": party_size,
            "joined_at": timestamp.isoformat(),
            "estimated_wait": self._estimate_wait(party_size)
        }
        heapq.heappush(self._queue, (priority, self._counter, entry))
        self._counter += 1
        return entry

    def _estimate_wait(self, party_size):
        base = len(self._queue) * 15  # 15 min per party ahead
        size_factor = 1.5 if party_size > 4 else 1.0
        # Peak hour detection (6-8 PM)
        hour = datetime.now().hour
        peak_factor = 1.3 if 18 <= hour <= 20 else 1.0
        wait = int(base * size_factor * peak_factor) + 10
        return f"~{wait} minutes"

    def get_next(self):
        if self._queue:
            _, _, entry = heapq.heappop(self._queue)
            return entry
        return None

    def get_all(self):
        return [entry for _, _, entry in sorted(self._queue)]

    def size(self):
        return len(self._queue)


class DietaryMatcher:
    """Match dietary restrictions to menu items."""
    TAGS = {
        "vegan": ["V", "VG"],
        "vegetarian": ["V", "VG", "Ve"],
        "gluten_free": ["GF"],
        "nut_free": ["NF"],
        "dairy_free": ["DF"],
        "halal": ["H"],
        "kosher": ["K"]
    }

    KEYWORDS = {
        "vegan": ["vegan", "plant-based", "plant based"],
        "vegetarian": ["vegetarian", "veggie", "no meat"],
        "gluten_free": ["gluten", "celiac", "coeliac", "gluten-free"],
        "nut_free": ["nut", "peanut", "almond", "cashew", "nut allergy"],
        "dairy_free": ["dairy", "lactose", "milk", "cheese allergy"],
        "halal": ["halal"],
        "kosher": ["kosher"]
    }

    @classmethod
    def detect(cls, text):
        """Detect dietary requirements from text."""
        text_lower = text.lower()
        detected = []
        for restriction, keywords in cls.KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected.append(restriction)
        return detected

    @classmethod
    def filter_menu(cls, menu_items, restrictions):
        """Filter menu items by dietary restrictions."""
        if not restrictions:
            return menu_items
        matching = []
        for item in menu_items:
            item_tags = item.get("tags", [])
            required_tags = []
            for r in restrictions:
                required_tags.extend(cls.TAGS.get(r, []))
            if any(tag in item_tags for tag in required_tags):
                matching.append(item)
        return matching


# ============================================================
# DATABASE (In-memory for demo; swap for SQLite/PostgreSQL)
# ============================================================

MENU_DATA = {
    "Maison Dorée": [
        {"name": "Foie Gras Torchon", "desc": "Fig compote, brioche", "price": 28, "tags": ["GF"], "category": "starter"},
        {"name": "Bouillabaisse", "desc": "Saffron broth, rouille", "price": 42, "tags": [], "category": "main"},
        {"name": "Wagyu Tenderloin", "desc": "Truffle jus, pomme purée", "price": 68, "tags": ["GF"], "category": "main"},
        {"name": "Crème Brûlée", "desc": "Vanilla bean, berries", "price": 16, "tags": ["V", "GF"], "category": "dessert"},
        {"name": "Salade Lyonnaise", "desc": "Frisée, lardons, poached egg", "price": 18, "tags": [], "category": "starter"},
        {"name": "Tarte Tatin", "desc": "Caramelized apple, crème fraîche", "price": 14, "tags": ["V"], "category": "dessert"},
    ],
    "Sakura Garden": [
        {"name": "Omakase Sashimi", "desc": "12-piece chef selection", "price": 85, "tags": ["GF"], "category": "main"},
        {"name": "Wagyu Gyoza", "desc": "Pan-fried, ponzu dipping", "price": 18, "tags": [], "category": "starter"},
        {"name": "Sakura Ramen", "desc": "Tonkotsu broth, chashu pork", "price": 24, "tags": [], "category": "main"},
        {"name": "Mochi Ice Cream", "desc": "Matcha, mango, sesame", "price": 12, "tags": ["V", "GF", "DF"], "category": "dessert"},
        {"name": "Agedashi Tofu", "desc": "Dashi broth, grated daikon", "price": 14, "tags": ["VG", "GF"], "category": "starter"},
    ],
    "Trattoria Roma": [
        {"name": "Burrata Caprese", "desc": "Heirloom tomato, balsamic", "price": 19, "tags": ["V", "GF"], "category": "starter"},
        {"name": "Handmade Tagliatelle", "desc": "Wild boar ragù, pecorino", "price": 32, "tags": [], "category": "main"},
        {"name": "Branzino al Sale", "desc": "Salt-crusted, herb butter", "price": 44, "tags": ["GF"], "category": "main"},
        {"name": "Tiramisu", "desc": "Classic mascarpone, espresso", "price": 14, "tags": ["V"], "category": "dessert"},
        {"name": "Risotto ai Funghi", "desc": "Mixed wild mushrooms, truffle oil", "price": 28, "tags": ["V", "GF"], "category": "main"},
    ]
}

# Initialize restaurants
RESTAURANTS = {
    "Maison Dorée": Restaurant(
        "Maison Dorée", "French",
        capacity={2: 6, 4: 6, 6: 3, 8: 2},
        hours="5:00 PM – 11:00 PM"
    ),
    "Sakura Garden": Restaurant(
        "Sakura Garden", "Japanese",
        capacity={2: 4, 4: 5, 6: 2},
        hours="5:30 PM – 10:30 PM"
    ),
    "Trattoria Roma": Restaurant(
        "Trattoria Roma", "Italian",
        capacity={2: 5, 4: 6, 6: 3, 8: 1},
        hours="5:00 PM – 10:00 PM"
    )
}

POLICIES = {
    "Maison Dorée": "48-hour cancellation required. Smart dress code. Groups 6+ require deposit.",
    "Sakura Garden": "24-hour cancellation. Walk-ins welcome when available.",
    "Trattoria Roma": "24-hour cancellation. Groups 6+ require deposit."
}

TIME_SLOTS = ["6:00 PM", "6:30 PM", "7:00 PM", "7:30 PM", "8:00 PM", "8:30 PM", "9:00 PM", "9:30 PM"]


# ============================================================
# NLP CONVERSATION ENGINE
# ============================================================

class ConversationEngine:
    """State machine for multi-turn restaurant booking conversations."""

    INTENTS = {
        "book":     ["book", "reserv", "table", "seat", "tonight", "tomorrow", "friday", "saturday", "sunday", "weekend"],
        "menu":     ["menu", "food", "eat", "dish", "cuisine", "starter", "dessert", "drink"],
        "waitlist": ["waitlist", "wait list", "join wait", "how long", "queue"],
        "cancel":   ["cancel", "delete", "remove reserv"],
        "modify":   ["modif", "change", "reschedul", "edit", "update"],
        "my_bookings": ["my reserv", "my book", "view", "check booking", "my table"],
        "dietary":  ["vegan", "vegetarian", "gluten", "allerg", "dietary", "nut", "dairy", "halal", "kosher"],
        "hours":    ["hour", "open", "close", "when", "schedule"],
        "policy":   ["polic", "cancel", "dress", "deposit", "rule"],
        "hello":    ["hello", "hi", "hey", "start", "help"],
    }

    def __init__(self):
        pass

    def detect_intent(self, text):
        text_lower = text.lower()
        for intent, keywords in self.INTENTS.items():
            if any(kw in text_lower for kw in keywords):
                return intent
        return "unknown"

    def extract_party_size(self, text):
        patterns = [
            r"(\d+)\s*(?:people|person|guest|pax|of us)",
            r"(?:for|party of)\s*(\d+)",
            r"^(\d+)$",
            r"table for (\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        # Word numbers
        word_nums = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8}
        for word, num in word_nums.items():
            if word in text.lower():
                return num
        return None

    def extract_time(self, text):
        match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text, re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            minute = match.group(2) or "00"
            ampm = match.group(3).upper()
            return f"{hour}:{minute} {ampm}"
        # Check for slot matches
        text_lower = text.lower()
        for slot in TIME_SLOTS:
            if slot.lower().replace(" ", "") in text_lower.replace(" ", ""):
                return slot
        return None

    def extract_name(self, text):
        removals = ["my name is", "i'm", "i am", "it's", "its", "call me", "under", "name"]
        name = text
        for r in removals:
            name = re.sub(r, "", name, flags=re.IGNORECASE)
        name = name.strip().strip(",.!?")
        # Capitalize properly
        return " ".join(w.capitalize() for w in name.split() if w)


engine = ConversationEngine()


# ============================================================
# FLASK ROUTES
# ============================================================

@app.route("/")
def index():
    session.clear()
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Main chatbot endpoint - processes messages and returns responses."""
    data = request.json
    user_msg = data.get("message", "").strip()
    restaurant_name = data.get("restaurant", "Maison Dorée")

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    # Get or initialize conversation state
    if "phase" not in session:
        session["phase"] = "greeting"
        session["booking"] = {}
        session["reservations"] = []

    phase = session.get("phase", "greeting")
    booking = session.get("booking", {})
    restaurant = RESTAURANTS.get(restaurant_name)

    response = process_message(user_msg, phase, booking, restaurant, restaurant_name)

    # Save updated state
    session["phase"] = response.pop("next_phase", phase)
    session["booking"] = response.pop("booking", booking)
    session.modified = True

    return jsonify(response)


def process_message(text, phase, booking, restaurant, restaurant_name):
    """Core NLP processing - returns response dict."""
    text_lower = text.lower()
    intent = engine.detect_intent(text)

    # ── Phase: GREETING ──────────────────────────────────────
    if phase == "greeting" or intent == "hello":
        return {
            "type": "chips",
            "message": f"Welcome to **{restaurant_name}** 🍽️\n\nI'm TableMate, your personal dining concierge. What can I help you with?",
            "chips": ["📅 Book a table", "🍴 View menu", "⏳ Join waitlist", "📋 View my reservations", "🥗 Dietary options"],
            "next_phase": "idle",
            "booking": {}
        }

    # ── MENU ─────────────────────────────────────────────────
    if intent == "menu":
        dietary = DietaryMatcher.detect(text)
        menu = MENU_DATA.get(restaurant_name, [])
        if dietary:
            menu = DietaryMatcher.filter_menu(menu, dietary)
            label = " & ".join(d.replace("_", "-") for d in dietary)
            title = f"**{label.title()} options** at {restaurant_name}:"
        else:
            title = f"**Menu preview** — {restaurant_name}:"
        return {
            "type": "menu",
            "message": title,
            "menu": menu,
            "next_phase": "idle",
            "booking": booking
        }

    # ── DIETARY ──────────────────────────────────────────────
    if intent == "dietary":
        dietary = DietaryMatcher.detect(text)
        if not dietary:
            dietary = ["vegetarian"]
        menu = DietaryMatcher.filter_menu(MENU_DATA.get(restaurant_name, []), dietary)
        tags_str = ", ".join(d.replace("_"," ").title() for d in dietary)
        return {
            "type": "menu",
            "message": f"Here are **{tags_str}** friendly options at {restaurant_name}. Our chef can also adapt most dishes — just let us know when booking:",
            "menu": menu,
            "chips": ["Book a table with dietary notes"],
            "next_phase": "idle",
            "booking": booking
        }

    # ── HOURS / POLICY ───────────────────────────────────────
    if intent == "hours" or intent == "policy":
        return {
            "type": "text",
            "message": f"📋 **{restaurant_name}**\n\n⏰ Hours: {restaurant.hours}\n\n📜 Policy: {POLICIES.get(restaurant_name, 'Please contact us for details.')}",
            "chips": ["Book a table", "View menu"],
            "next_phase": "idle",
            "booking": booking
        }

    # ── WAITLIST ─────────────────────────────────────────────
    if intent == "waitlist" and phase == "idle":
        current_wait = restaurant.waitlist.size()
        return {
            "type": "text",
            "message": f"I'll add you to the waitlist for **{restaurant_name}**.\n\nCurrent queue: **{current_wait} parties** ahead of you.\n\nWhat name should I put you under?",
            "next_phase": "waitlist_name",
            "booking": booking
        }

    if phase == "waitlist_name":
        name = engine.extract_name(text)
        if not name or len(name) < 2:
            return {"type": "text", "message": "Could you share your name please?", "next_phase": "waitlist_name", "booking": booking}
        booking["name"] = name
        return {
            "type": "chips",
            "message": f"Got it, **{name}**! How many guests?",
            "chips": ["1", "2", "3", "4", "5", "6"],
            "next_phase": "waitlist_party",
            "booking": booking
        }

    if phase == "waitlist_party":
        party = engine.extract_party_size(text)
        if not party:
            return {"type": "chips", "message": "How many guests?", "chips": ["1","2","3","4","5","6"], "next_phase": "waitlist_party", "booking": booking}
        entry = restaurant.waitlist.add(booking["name"], party)
        return {
            "type": "success",
            "message": "Added to waitlist!",
            "details": {
                "Name": entry["name"],
                "Party size": party,
                "Position": f"#{restaurant.waitlist.size()} in queue",
                "Est. wait": entry["estimated_wait"]
            },
            "sms": f"TableMate: You're #{restaurant.waitlist.size()} on the waitlist at {restaurant.name}. Est. wait: {entry['estimated_wait']}",
            "next_phase": "idle",
            "booking": {}
        }

    # ── MY BOOKINGS ───────────────────────────────────────────
    if intent == "my_bookings":
        reservations = session.get("reservations", [])
        if not reservations:
            return {
                "type": "text",
                "message": "You don't have any reservations yet. Would you like to make one?",
                "chips": ["Book a table for 2", "Book a table for 4"],
                "next_phase": "idle",
                "booking": {}
            }
        return {
            "type": "reservations",
            "message": f"Here are your **{len(reservations)}** reservation(s):",
            "reservations": reservations,
            "next_phase": "idle",
            "booking": booking
        }

    # ── CANCEL ───────────────────────────────────────────────
    if intent == "cancel" and "cancel" in text_lower:
        conf_match = re.search(r"TM[A-Z0-9]+", text.upper())
        if conf_match:
            conf = conf_match.group()
            reservations = session.get("reservations", [])
            session["reservations"] = [r for r in reservations if r.get("conf_num") != conf]
            # Free the table
            for rest in RESTAURANTS.values():
                if conf in rest.reservations:
                    res = rest.reservations.pop(conf)
                    if res.table_id in rest.tables:
                        rest.tables[res.table_id]["status"] = "available"
                        rest.tables[res.table_id]["reservation"] = None
            return {
                "type": "text",
                "message": f"✅ Reservation **{conf}** has been cancelled. No charges apply within our cancellation window.",
                "next_phase": "idle",
                "booking": {}
            }
        return {
            "type": "text",
            "message": "Please provide your confirmation number (e.g. TM-XXXXX) to cancel.",
            "next_phase": "idle",
            "booking": booking
        }

    # ── BOOKING FLOW ─────────────────────────────────────────
    if (intent == "book" or phase.startswith("book")) and phase == "idle":
        # Try to pre-extract info from message
        party = engine.extract_party_size(text)
        if party:
            booking["party"] = party
        return {
            "type": "text",
            "message": f"Let's get your table at **{restaurant_name}**! 🎉\n\nWhat name should the reservation be under?",
            "next_phase": "booking_name",
            "booking": booking
        }

    if phase == "booking_name" or (intent == "book" and phase == "idle"):
        if phase != "booking_name":
            return {
                "type": "text",
                "message": f"Let's book your table at **{restaurant_name}**! What name shall I put it under?",
                "next_phase": "booking_name",
                "booking": {}
            }
        name = engine.extract_name(text)
        if not name or len(name) < 2:
            return {"type": "text", "message": "What name should the reservation be under?", "next_phase": "booking_name", "booking": booking}
        booking["name"] = name
        if "party" in booking:
            # Skip party question
            return {
                "type": "chips",
                "message": f"Lovely, **{name}**! Which date works for you?",
                "chips": get_date_options(),
                "next_phase": "booking_date",
                "booking": booking
            }
        return {
            "type": "chips",
            "message": f"Lovely, **{name}**! How many guests will be joining you?",
            "chips": ["1", "2", "3", "4", "5", "6", "7", "8"],
            "next_phase": "booking_party",
            "booking": booking
        }

    if phase == "booking_party":
        party = engine.extract_party_size(text)
        if not party:
            return {"type": "chips", "message": "How many guests will be joining you?", "chips": ["1","2","3","4","5","6","7","8"], "next_phase": "booking_party", "booking": booking}
        if party > 8:
            return {
                "type": "text",
                "message": "For parties larger than 8, please contact us directly for private dining arrangements. 🥂",
                "chips": ["Book for 8", "Start over"],
                "next_phase": "idle",
                "booking": {}
            }
        booking["party"] = party
        return {
            "type": "chips",
            "message": f"Perfect — **{party} guests**! Which date works best?",
            "chips": get_date_options(),
            "next_phase": "booking_date",
            "booking": booking
        }

    if phase == "booking_date":
        booking["date"] = text.strip().capitalize()
        return {
            "type": "chips",
            "message": f"And what time would you prefer?",
            "chips": TIME_SLOTS,
            "next_phase": "booking_time",
            "booking": booking
        }

    if phase == "booking_time":
        time = engine.extract_time(text) or text.strip()
        booking["time"] = time

        # Check table availability
        party = booking.get("party", 2)
        candidates = restaurant.get_available_tables(party, booking.get("date"), time)

        if not candidates:
            # Offer waitlist
            return {
                "type": "chips",
                "message": f"😔 No tables available for **{party} guests** at **{time}** on **{booking.get('date')}**.\n\nWould you like to join the waitlist or try a different time?",
                "chips": ["Join waitlist", "Try 7:00 PM", "Try 8:00 PM"],
                "next_phase": "idle",
                "booking": booking
            }

        booking["table_id"] = candidates[0][1]  # Best fit table
        return {
            "type": "chips",
            "message": "Any special requests or dietary requirements?",
            "chips": ["No special requests", "Window seat 🪟", "Birthday 🎂", "Anniversary 💑", "I have dietary needs 🥗"],
            "next_phase": "booking_special",
            "booking": booking
        }

    if phase == "booking_special":
        booking["special"] = "None" if "no special" in text_lower else text.strip()
        dietary = DietaryMatcher.detect(text)
        booking["dietary"] = ", ".join(dietary) if dietary else ""
        return {
            "type": "confirm",
            "message": "Please confirm your reservation:",
            "details": {
                "Restaurant": restaurant_name,
                "Name": booking.get("name"),
                "Date": booking.get("date"),
                "Time": booking.get("time"),
                "Party": f"{booking.get('party')} guests",
                "Special requests": booking.get("special", "None"),
                "Dietary": booking.get("dietary") or "None"
            },
            "next_phase": "booking_confirm",
            "booking": booking
        }

    if phase == "booking_confirm":
        positive = any(w in text_lower for w in ["yes", "confirm", "book", "great", "perfect", "ok", "sure", "go ahead"])
        negative = any(w in text_lower for w in ["no", "cancel", "wrong", "change"])

        if positive:
            return complete_booking(booking, restaurant, restaurant_name, session)
        elif negative:
            return {
                "type": "chips",
                "message": "No problem — what would you like to change?",
                "chips": ["Change date", "Change time", "Change party size", "Start over"],
                "next_phase": "idle",
                "booking": booking
            }
        return {
            "type": "confirm",
            "message": "Shall I confirm this reservation?",
            "details": {
                "Restaurant": restaurant_name,
                "Name": booking.get("name"),
                "Date": booking.get("date"),
                "Time": booking.get("time"),
                "Party": f"{booking.get('party')} guests"
            },
            "next_phase": "booking_confirm",
            "booking": booking
        }

    # Default
    return {
        "type": "chips",
        "message": "I'd be happy to help! What would you like to do?",
        "chips": ["📅 Book a table", "🍴 View menu", "⏳ Join waitlist", "📋 My reservations"],
        "next_phase": "idle",
        "booking": booking
    }


def complete_booking(booking, restaurant, restaurant_name, session):
    """Finalize reservation and update state."""
    res = Reservation(
        name=booking["name"],
        party_size=booking["party"],
        date=booking["date"],
        time=booking["time"],
        restaurant=restaurant_name,
        table_id=booking.get("table_id", "TBD"),
        special=booking.get("special", ""),
        dietary=booking.get("dietary", "")
    )
    # Update table status
    if res.table_id in restaurant.tables:
        restaurant.tables[res.table_id]["status"] = "reserved"
        restaurant.tables[res.table_id]["reservation"] = res.conf_num
    restaurant.reservations[res.conf_num] = res

    # Store in session
    reservations = session.get("reservations", [])
    reservations.append(res.to_dict())
    session["reservations"] = reservations

    return {
        "type": "success",
        "message": "Reservation confirmed!",
        "details": {
            "Confirmation": res.conf_num,
            "Restaurant": restaurant_name,
            "Name": res.name,
            "Date": res.date,
            "Time": res.time,
            "Table": res.table_id,
            "Party": f"{res.party_size} guests",
        },
        "sms": f"TableMate: Reservation confirmed! {res.conf_num} — {restaurant_name} on {res.date} at {res.time} for {res.party_size}. See you soon!",
        "next_phase": "idle",
        "booking": {}
    }


def get_date_options():
    today = datetime.now()
    options = ["Tonight"]
    for i in range(1, 6):
        d = today + timedelta(days=i)
        options.append(d.strftime("%a, %b %d"))
    return options


# ============================================================
# API ENDPOINTS
# ============================================================

@app.route("/api/restaurants", methods=["GET"])
def get_restaurants():
    return jsonify([r.to_dict() for r in RESTAURANTS.values()])


@app.route("/api/tables/<restaurant_name>", methods=["GET"])
def get_tables(restaurant_name):
    restaurant = RESTAURANTS.get(restaurant_name)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404
    return jsonify(list(restaurant.tables.values()))


@app.route("/api/waitlist/<restaurant_name>", methods=["GET"])
def get_waitlist(restaurant_name):
    restaurant = RESTAURANTS.get(restaurant_name)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404
    return jsonify(restaurant.waitlist.get_all())


@app.route("/api/stats", methods=["GET"])
def get_stats():
    stats = {}
    for name, rest in RESTAURANTS.items():
        total = len(rest.tables)
        reserved = sum(1 for t in rest.tables.values() if t["status"] == "reserved")
        stats[name] = {
            "total_tables": total,
            "reserved": reserved,
            "available": total - reserved,
            "occupancy_pct": round(reserved / total * 100) if total else 0,
            "waitlist_count": rest.waitlist.size(),
            "total_reservations": len(rest.reservations)
        }
    return jsonify(stats)


@app.route("/api/menu/<restaurant_name>", methods=["GET"])
def get_menu(restaurant_name):
    dietary = request.args.get("dietary", "").split(",") if request.args.get("dietary") else []
    menu = MENU_DATA.get(restaurant_name, [])
    if dietary and dietary != [""]:
        menu = DietaryMatcher.filter_menu(menu, dietary)
    return jsonify(menu)


if __name__ == "__main__":
    print("  TableMate Restaurant Bot — Starting...")
    print("  API running at http://localhost:5000")
    print("  Chat at http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)