"""Tests for GET /api/cricketers/search endpoint."""


class TestCricketersSearch:
    def test_search_empty_db(self, client):
        """Returns empty list when no cricketers exist."""
        resp = client.get("/api/cricketers/search?q=kohli")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_finds_cricketer(self, client, seeded_cricketer):
        resp = client.get("/api/cricketers/search?q=kohli")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["name"] == "Virat Kohli"

    def test_search_case_insensitive(self, client, seeded_cricketer):
        resp = client.get("/api/cricketers/search?q=KOHLI")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_partial_name(self, client, seeded_cricketer):
        resp = client.get("/api/cricketers/search?q=vir")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_no_match(self, client, seeded_cricketer):
        resp = client.get("/api/cricketers/search?q=xyzxyz")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_result_has_required_fields(self, client, seeded_cricketer):
        resp = client.get("/api/cricketers/search?q=kohli")
        result = resp.json()[0]
        assert "id" in result
        assert "name" in result
        assert "country" in result

    def test_search_country_field(self, client, seeded_cricketer):
        resp = client.get("/api/cricketers/search?q=kohli")
        assert resp.json()[0]["country"] == "IND"

    def test_search_multiple_results(self, client, db):
        from app.models.cricketer import Cricketer
        db.add(Cricketer(name="Rohit Sharma", country="IND"))
        db.add(Cricketer(name="Virat Kohli", country="IND"))
        db.add(Cricketer(name="Steve Smith", country="AUS"))
        db.commit()

        resp = client.get("/api/cricketers/search?q=sharma")
        results = resp.json()
        assert len(results) == 1
        assert results[0]["name"] == "Rohit Sharma"

    def test_search_limit_respected(self, client, db):
        """Default limit is 10 (or 20 max per cricketers.py)."""
        from app.models.cricketer import Cricketer
        for i in range(25):
            db.add(Cricketer(name=f"Cricketer {i}", country="IND"))
        db.commit()

        resp = client.get("/api/cricketers/search?q=Cricketer")
        assert resp.status_code == 200
        # Should be capped at 20 (max) or 10 (default)
        assert len(resp.json()) <= 20
