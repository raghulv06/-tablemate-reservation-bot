<div align="center">

# 🍽️ TableMate
### AI-Powered Restaurant Reservation Chatbot

*Gen AI for Gen Z — Challenge 2 Submission*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Tests](https://img.shields.io/badge/Tests-32%20Passing-4CAF50?style=for-the-badge&logo=checkmarx&logoColor=white)](./test_app.py)
[![Deploy](https://img.shields.io/badge/Deployed-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://tablemate-reservation-bot.onrender.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](./LICENSE)

<br>

**[🌐 Live Demo](https://tablemate-reservation-bot.onrender.com)** &nbsp;·&nbsp;
**[📖 Documentation](./docs/PROJECT_DOCS.md)** &nbsp;·&nbsp;
**[🐛 Report Bug](https://github.com/raghulv06/-tablemate-reservation-bot/issues)**

<br>

> A **production-grade** dining concierge chatbot with real Python engineering —
> NLP conversation engine, bin-packing table optimizer, priority-queue waitlist,
> dietary restriction matching, and a live REST API. **Not a copy-paste.**

</div>

---

## 📋 Table of Contents

- [About The Project](#-about-the-project)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [API Reference](#-api-reference)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Challenge Tasks](#-challenge-tasks)
- [Author](#-author)

---

## 🎯 About The Project

TableMate solves the full restaurant reservation problem with a conversational AI interface. A guest can type naturally — *"Book a table for 4 on Friday at 7pm, window seat please"* — and the bot handles the entire flow: name collection, party sizing, date/time selection, table assignment, special requests, confirmation, and SMS notification.

**What makes this different from other submissions:**

- ✅ Real Python OOP — 5 custom classes with single responsibilities
- ✅ Real algorithms — bin-packing heuristic + heapq priority queue
- ✅ Real API — 6 REST endpoints consumed by the frontend
- ✅ Real tests — 32 unit tests covering all classes and endpoints
- ✅ Real deployment — live on Render, not just a local demo

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **NLP Chatbot** | 8-phase state machine with intent detection across 10 categories |
| 📅 **Smart Booking** | Full flow: name → party → date → time → special requests → confirm |
| 🗺️ **Live Table Map** | Real-time visual grid showing available/reserved tables |
| ⏳ **Waitlist Queue** | Python heapq priority queue — smaller parties served first |
| 🥗 **Dietary Matching** | Detects 7 restrictions from natural language, filters menu instantly |
| 📱 **SMS Notifications** | Confirmation message generated on every booking action |
| 🔄 **Multi-Restaurant** | Switch between 3 restaurants, each with independent inventory |
| 📊 **Live Dashboard** | Real-time stats: occupancy %, reservations, waitlist count |
| ✏️ **Modify/Cancel** | Full CRUD on reservations via confirmation number |
| 🍴 **Menu Preview** | Compressed menus with dietary tags (V, GF, DF, NF, H, K) |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, Flask 3.0 |
| **Conversation** | Custom NLP engine (rule-based + regex) |
| **Data Structures** | heapq, defaultdict, in-memory dict store |
| **Frontend** | Vanilla HTML5, CSS3, JavaScript (zero frameworks) |
| **Testing** | Python unittest + Flask test client |
| **Server** | Gunicorn (WSGI production server) |
| **Deployment** | Render (free tier) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/raghulv06/-tablemate-reservation-bot.git
cd tablemate-reservation-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Open your browser at **http://localhost:5000** 🎉

### Run Tests
```bash
python test_app.py
```

---

## 📁 Project Structure

```
tablemate-reservation-bot/
│
├── app.py                     # 🐍 Main Flask app — all Python classes & routes
│   ├── class Restaurant       #    Table inventory + bin-packing algorithm
│   ├── class Reservation      #    Booking data model + confirmation numbers
│   ├── class WaitlistManager  #    heapq priority queue
│   ├── class DietaryMatcher   #    NLP dietary detection + menu filtering
│   ├── class ConversationEngine  # Intent detection + entity extraction
│   └── process_message()      #    8-phase state machine controller
│
├── templates/
│   └── index.html             # 🎨 Full chat UI (HTML + CSS + JS, zero deps)
│
├── test_app.py                # 🧪 32 unit tests across 6 test classes
├── requirements.txt           # 📦 flask>=3.0.0, gunicorn>=21.0.0
├── Procfile                   # 🚀 gunicorn app:app (Render/Heroku)
├── runtime.txt                # 🐍 python-3.11.0
└── README.md                  # 📖 You are here
```

---

## ⚙️ How It Works

### 1. 🤖 NLP Conversation Engine

The chatbot uses an **8-phase state machine** managed via Flask sessions:

```
greeting → idle → booking_name → booking_party → booking_date
        → booking_time → booking_special → booking_confirm
```

Each user message is processed by `detect_intent()` (10 intent categories), then entity extractors pull out structured data:

```python
# Party size extraction — handles numeric AND word numbers
r"(\d+)\s*(?:people|person|guest|pax)"   # "4 guests"
r"(?:for|party of)\s*(\d+)"              # "party of 4"
word_nums = {"two": 2, "four": 4, ...}   # "two of us"

# Time extraction
r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)"     # "7:30 PM"
```

### 2. 🗃️ Table Optimization — Bin-Packing Heuristic

```python
def get_available_tables(self, party_size, date, time):
    candidates = []
    for tid, table in self.tables.items():
        if table["status"] == "available" and table["size"] >= party_size:
            waste = table["size"] - party_size  # Minimize empty seats
            candidates.append((waste, tid, table))
    candidates.sort(key=lambda x: x[0])  # Best-fit first
    return candidates
```

A party of 2 always gets a 2-top (waste=0), never an 8-top (waste=6). This maximises table turnover.

### 3. ⏳ Waitlist Priority Queue

```python
import heapq

# Smaller parties get higher priority (seated faster)
priority = party_size * 10 + counter   # min-heap → smallest first

# Dynamic wait time with peak-hour detection
base_wait   = len(queue) * 15          # 15 min per party ahead
size_factor = 1.5 if party_size > 4 else 1.0
peak_factor = 1.3 if 18 <= hour <= 20 else 1.0  # 6–8 PM peak
wait        = int(base_wait * size_factor * peak_factor) + 10
```

### 4. 🥗 Dietary Restriction Matching

```python
# Auto-detect restrictions from natural language
DietaryMatcher.detect("I'm vegan and gluten free")
# → ["vegan", "gluten_free"]

# Auto-filter menu to matching items only
menu = DietaryMatcher.filter_menu(all_items, ["vegan", "gluten_free"])
# → Returns only items with V/VG AND GF tags
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Main chatbot — send `{"message": "...", "restaurant": "..."}` |
| `GET`  | `/api/restaurants` | All restaurants with live stats |
| `GET`  | `/api/tables/<restaurant>` | Real-time table grid |
| `GET`  | `/api/waitlist/<restaurant>` | Current priority queue |
| `GET`  | `/api/stats` | Occupancy %, reservation counts |
| `GET`  | `/api/menu/<restaurant>?dietary=vegan` | Filtered menu |

### Example Request

```bash
curl -X POST https://tablemate-reservation-bot.onrender.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Book a table for 4", "restaurant": "Maison Dorée"}'
```

### Response Types

| Type | Description |
|------|-------------|
| `text` | Simple message with optional chip buttons |
| `chips` | Message + quick-reply buttons |
| `menu` | Message + array of menu item cards |
| `confirm` | Booking summary with Confirm/Edit buttons |
| `success` | Confirmation with reference number + SMS string |
| `reservations` | List of bookings with cancel buttons |

---

## 🧪 Testing

```bash
python test_app.py
```

```
🧪 Running TableMate Test Suite...
==================================================
test_detect_intent_book          ... ok
test_detect_intent_dietary       ... ok
test_detect_intent_menu          ... ok
test_detect_intent_waitlist      ... ok
test_extract_name                ... ok
test_extract_party_size_numeric  ... ok
test_extract_party_size_words    ... ok
test_extract_time                ... ok
test_detect_gluten_free          ... ok
test_detect_multiple             ... ok
test_detect_vegan                ... ok
test_filter_menu_no_restrictions ... ok
test_filter_menu_vegan           ... ok
test_add_entry                   ... ok
test_get_all_returns_list        ... ok
test_size_increases              ... ok
test_smaller_party_priority      ... ok
test_available_tables_small      ... ok
test_larger_party_table          ... ok
test_no_tables_oversized         ... ok
test_tables_initialized          ... ok
test_creates_with_conf_num       ... ok
test_to_dict                     ... ok
test_chat_dietary                ... ok
test_chat_hello                  ... ok
test_chat_menu                   ... ok
test_index_loads                 ... ok
test_menu_api_dietary_filter     ... ok
test_restaurants_api             ... ok
test_stats_api                   ... ok
test_tables_api                  ... ok
test_waitlist_api                ... ok
==================================================
✅ All 32 tests passed in 0.025s!
```

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestConversationEngine` | 8 | Intent detection, entity extraction |
| `TestDietaryMatcher` | 5 | NLP detection, menu filtering |
| `TestWaitlistManager` | 4 | Priority ordering, wait time |
| `TestTableOptimization` | 4 | Bin-packing, best-fit selection |
| `TestReservation` | 2 | Data model, serialisation |
| `TestFlaskAPI` | 9 | All 6 endpoints + chat flows |

---

## 🌐 Deployment

### Live Demo
🟢 **[https://tablemate-reservation-bot.onrender.com](https://tablemate-reservation-bot.onrender.com)**

### Deploy Your Own (Free)

**Render (Recommended):**
1. Fork this repo
2. Go to [render.com](https://render.com) → New Web Service → Connect repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. Deploy ✅



---

## ✅ Challenge Tasks

| Task | Status | Evidence |
|------|--------|---------|
| 📁 **GitHub Repository** | ✅ | Public repo, all files, proper structure |
| 📖 **Detailed README** | ✅ | This file — algorithms, API, tests, deploy |
| 📄 **Project Documentation** | ✅ | Full Word doc + PROJECT_DOCS.md |
| ⭐ **Creative/Unique Feature** | ✅ | Multi-restaurant + live table map + peak-hour waitlist |
| 📢 **Build in Public LinkedIn** | ✅ | Posted with GitHub + demo links |

### ⭐ Unique Features

**1. Multi-Restaurant System** — 3 fully independent restaurants, each with separate tables, waitlist, reservations, and menu. Switchable mid-conversation.

**2. Live Table Map** — Visual grid updated in real-time from `/api/tables/`. Green = available, Red = reserved. Auto-refreshes every 10 seconds.

**3. Peak-Hour Waitlist** — Detects 6–8 PM rush and applies 1.3× wait time multiplier for accurate guest expectations.

---

## 💬 Sample Conversation

```
You → Book a table for 4 on Friday at 7pm
Bot → Let's get your table at Maison Dorée! What name shall I put it under?

You → Raghul V  
Bot → Lovely! Which date?  [Tonight] [Tomorrow] [Fri, Feb 21] ...

You → Friday
Bot → What time?  [6:00 PM] [7:00 PM] [8:00 PM] ...

You → 7pm
Bot → Any special requests?  [No requests] [Window seat] [Birthday] ...

You → Window seat, business dinner
Bot → ╔══════════════════════════════╗
      ║ 🍽️ Reservation Details       ║
      ║ Restaurant: Maison Dorée     ║
      ║ Name:       Raghul V         ║
      ║ Date:       Fri, Feb 21      ║
      ║ Time:       7:00 PM          ║
      ║ Party:      4 guests         ║
      ║ Special:    Window seat      ║
      ║ [✓ Confirm]    [Edit]        ║
      ╚══════════════════════════════╝

You → Confirm
Bot → 🎉 Reservation Confirmed!
      Ref: TM-C9M44
      📱 SMS sent: "Confirmed! TM-C9M44 — Maison Dorée, Fri Feb 21 at 7:00 PM for 4."
```

---

## 📊 Project Stats

| Metric | Value |
|--------|-------|
| Lines of Python | 500+ |
| Unit Tests | 32 passing |
| API Endpoints | 6 |
| NLP Intents | 10 categories |
| Conversation Phases | 8 |
| Restaurants | 3 |
| Dietary Types Detected | 7 |
| Dependencies | 2 (Flask, gunicorn) |

---


<div align="center">

Built with ❤️ for **Gen AI for Gen Z — Challenge 2**

*Real engineering. Real algorithms. Not a copy-paste.*

**⭐ Star this repo if you found it helpful! ⭐**

</div>
