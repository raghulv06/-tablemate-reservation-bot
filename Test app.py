
import unittest
import sys
sys.path.insert(0, '.')

from app import (
    ConversationEngine, DietaryMatcher, WaitlistManager,
    Restaurant, Reservation, RESTAURANTS, MENU_DATA, app
)


class TestConversationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ConversationEngine()

    def test_detect_intent_book(self):
        tests = ["book a table", "I want to reserve a table", "table for tonight"]
        for t in tests:
            self.assertEqual(self.engine.detect_intent(t), "book", f"Failed: '{t}'")

    def test_detect_intent_menu(self):
        self.assertEqual(self.engine.detect_intent("show me the menu"), "menu")
        self.assertEqual(self.engine.detect_intent("what food do you have"), "menu")

    def test_detect_intent_waitlist(self):
        self.assertEqual(self.engine.detect_intent("join the waitlist"), "waitlist")
        self.assertEqual(self.engine.detect_intent("how long is the wait"), "waitlist")

    def test_detect_intent_dietary(self):
        self.assertEqual(self.engine.detect_intent("I'm vegan"), "dietary")
        self.assertEqual(self.engine.detect_intent("gluten free options"), "dietary")

    def test_extract_party_size_numeric(self):
        tests = [("table for 4 people", 4), ("party of 6", 6), ("2 guests", 2), ("3", 3)]
        for text, expected in tests:
            result = self.engine.extract_party_size(text)
            self.assertEqual(result, expected, f"Failed: '{text}' expected {expected}, got {result}")

    def test_extract_party_size_words(self):
        self.assertEqual(self.engine.extract_party_size("two of us"), 2)
        self.assertEqual(self.engine.extract_party_size("four people"), 4)

    def test_extract_time(self):
        tests = [("7pm", "7:00 PM"), ("7:30 PM", "7:30 PM"), ("8 pm", "8:00 PM")]
        for text, expected in tests:
            result = self.engine.extract_time(text)
            self.assertEqual(result, expected, f"'{text}' → {result}, expected {expected}")

    def test_extract_name(self):
        tests = [
            ("my name is John Smith", "John Smith"),
            ("I'm Alice", "Alice"),
            ("under Maria Garcia", "Maria Garcia"),
        ]
        for text, expected in tests:
            result = self.engine.extract_name(text)
            self.assertIn(expected, result, f"'{text}' → '{result}', expected '{expected}'")


class TestDietaryMatcher(unittest.TestCase):
    def test_detect_vegan(self):
        result = DietaryMatcher.detect("I'm vegan")
        self.assertIn("vegan", result)

    def test_detect_gluten_free(self):
        result = DietaryMatcher.detect("I have a gluten intolerance")
        self.assertIn("gluten_free", result)

    def test_detect_multiple(self):
        result = DietaryMatcher.detect("I'm vegetarian and also dairy free")
        self.assertIn("vegetarian", result)
        self.assertIn("dairy_free", result)

    def test_filter_menu_vegan(self):
        menu = [
            {"name": "Salad", "tags": ["V", "GF"]},
            {"name": "Steak", "tags": []},
            {"name": "Soup", "tags": ["GF"]},
        ]
        result = DietaryMatcher.filter_menu(menu, ["vegetarian"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Salad")

    def test_filter_menu_no_restrictions(self):
        menu = MENU_DATA["Maison Dorée"]
        result = DietaryMatcher.filter_menu(menu, [])
        self.assertEqual(len(result), len(menu))


class TestWaitlistManager(unittest.TestCase):
    def setUp(self):
        self.wl = WaitlistManager()

    def test_add_entry(self):
        entry = self.wl.add("Alice", 2)
        self.assertEqual(entry["name"], "Alice")
        self.assertEqual(entry["party_size"], 2)
        self.assertIn("estimated_wait", entry)

    def test_size_increases(self):
        self.assertEqual(self.wl.size(), 0)
        self.wl.add("Bob", 2)
        self.assertEqual(self.wl.size(), 1)
        self.wl.add("Carol", 4)
        self.assertEqual(self.wl.size(), 2)

    def test_smaller_party_priority(self):
        """Smaller parties should be prioritized."""
        self.wl.add("Large", 6)
        self.wl.add("Small", 2)
        self.wl.add("Medium", 4)
        next_entry = self.wl.get_next()
        self.assertEqual(next_entry["party_size"], 2)

    def test_get_all_returns_list(self):
        self.wl.add("A", 2)
        self.wl.add("B", 3)
        all_entries = self.wl.get_all()
        self.assertIsInstance(all_entries, list)
        self.assertEqual(len(all_entries), 2)


class TestTableOptimization(unittest.TestCase):
    def setUp(self):
        self.rest = Restaurant("Test", "Test", {2:4, 4:4, 6:2}, "6PM-10PM")

    def test_tables_initialized(self):
        self.assertGreater(len(self.rest.tables), 0)

    def test_available_tables_for_small_party(self):
        candidates = self.rest.get_available_tables(2, "Tonight", "7:00 PM")
        self.assertGreater(len(candidates), 0)
        # First candidate should be 2-top (waste = 0)
        self.assertEqual(candidates[0][0], 0)  # waste = 0

    def test_larger_party_gets_larger_table(self):
        candidates = self.rest.get_available_tables(5, "Tonight", "7:00 PM")
        # Should only return 6-person tables
        for waste, tid, table in candidates:
            self.assertGreaterEqual(table["size"], 5)

    def test_no_tables_for_oversized_party(self):
        candidates = self.rest.get_available_tables(10, "Tonight", "7:00 PM")
        self.assertEqual(len(candidates), 0)


class TestReservation(unittest.TestCase):
    def test_creates_with_conf_num(self):
        res = Reservation("John", 2, "Tonight", "7:00 PM", "Test Rest", "T1")
        self.assertTrue(res.conf_num.startswith("TM"))
        self.assertEqual(len(res.conf_num), 7)  # TM + 5 chars

    def test_to_dict(self):
        res = Reservation("Jane", 4, "Tomorrow", "8:00 PM", "Test Rest", "T2", "Window seat")
        d = res.to_dict()
        self.assertEqual(d["name"], "Jane")
        self.assertEqual(d["party_size"], 4)
        self.assertEqual(d["special"], "Window seat")
        self.assertEqual(d["status"], "confirmed")


class TestFlaskAPI(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-key'
        self.client = app.test_client()

    def test_index_loads(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)

    def test_restaurants_api(self):
        res = self.client.get('/api/restaurants')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data), 3)
        self.assertIn("name", data[0])

    def test_tables_api(self):
        res = self.client.get('/api/tables/Maison%20Dor%C3%A9e')
        self.assertEqual(res.status_code, 200)

    def test_stats_api(self):
        res = self.client.get('/api/stats')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("Maison Dorée", data)

    def test_chat_hello(self):
        res = self.client.post('/api/chat',
            json={"message": "hello", "restaurant": "Maison Dorée"},
            content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("message", data)

    def test_chat_menu(self):
        with self.client.session_transaction() as sess:
            sess["phase"] = "idle"
            sess["booking"] = {}
            sess["reservations"] = []
        res = self.client.post('/api/chat',
            json={"message": "show me the menu", "restaurant": "Maison Dorée"},
            content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("type"), "menu")
        self.assertIn("menu", data)

    def test_chat_dietary(self):
        with self.client.session_transaction() as sess:
            sess["phase"] = "idle"
            sess["booking"] = {}
            sess["reservations"] = []
        res = self.client.post('/api/chat',
            json={"message": "I'm vegan", "restaurant": "Sakura Garden"},
            content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("menu", data)

    def test_menu_api_with_dietary_filter(self):
        res = self.client.get('/api/menu/Maison%20Dor%C3%A9e?dietary=vegetarian')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        for item in data:
            self.assertTrue(any(t in item.get('tags', []) for t in ['V', 'VG', 'Ve']))

    def test_waitlist_api(self):
        res = self.client.get('/api/waitlist/Maison%20Dor%C3%A9e')
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    print("🧪 Running TableMate Test Suite...")
    print("="*50)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestConversationEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestDietaryMatcher))
    suite.addTests(loader.loadTestsFromTestCase(TestWaitlistManager))
    suite.addTests(loader.loadTestsFromTestCase(TestTableOptimization))
    suite.addTests(loader.loadTestsFromTestCase(TestReservation))
    suite.addTests(loader.loadTestsFromTestCase(TestFlaskAPI))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("="*50)
    if result.wasSuccessful():
        print(f"✅ All {result.testsRun} tests passed!")
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")
    sys.exit(0 if result.wasSuccessful() else 1)