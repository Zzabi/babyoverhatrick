"""
Database seeder — run once to create the default games.
Usage: cd backend && uv run python -m app.scripts.seed

Creates:
  - Game: Guess the Cricketer (slug: guess-the-cricketer)
  - Game: Unscramble the Name (slug: unscramble-the-name)
  - A default question set for each game (empty — admin adds questions via /api/admin)
  - Sample cricketers in the autocomplete list

Safe to run multiple times — skips existing records.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.db import SessionLocal
from app.models.game import Game
from app.models.question import QuestionSet
from app.models.cricketer import Cricketer
from sqlalchemy import select


GAMES = [
    {
        "slug": "guess-the-cricketer",
        "name": "Guess the Cricketer",
        "description": "One image. Name the cricketer before the clock runs out.",
        "status": "active",
        "sort_order": 1,
        "config": {
            "rounds": 10,
            "timePerQuestion": 15,
            "scoring": {"basePoints": 100, "speedBonusCap": 20, "hintPenalty": 10},
        },
    },
    {
        "slug": "unscramble-the-name",
        "name": "Unscramble the Name",
        "description": "Tap the tiles back into a legend's name.",
        "status": "active",
        "sort_order": 2,
        "config": {
            "rounds": 10,
            "timePerQuestion": 30,
            "scoring": {"basePoints": 100, "speedBonusCap": 20, "hintPenalty": 10},
        },
    },
]

SAMPLE_CRICKETERS = [
    ("Sachin Tendulkar", "IND"), ("Virat Kohli", "IND"), ("MS Dhoni", "IND"),
    ("Rohit Sharma", "IND"), ("Jasprit Bumrah", "IND"), ("Ravichandran Ashwin", "IND"),
    ("Wasim Akram", "PAK"), ("Shahid Afridi", "PAK"), ("Babar Azam", "PAK"),
    ("Ricky Ponting", "AUS"), ("Steve Smith", "AUS"), ("Pat Cummins", "AUS"),
    ("Brian Lara", "WI"), ("Vivian Richards", "WI"), ("Chris Gayle", "WI"),
    ("AB de Villiers", "SA"), ("Kagiso Rabada", "SA"), ("Hashim Amla", "SA"),
    ("Kane Williamson", "NZ"), ("Ross Taylor", "NZ"),
    ("Joe Root", "ENG"), ("Ben Stokes", "ENG"), ("James Anderson", "ENG"),
    ("Shakib Al Hasan", "BAN"), ("Tamim Iqbal", "BAN"),
    ("Kumar Sangakkara", "SL"), ("Muttiah Muralitharan", "SL"),
]


def seed():
    db = SessionLocal()
    try:
        print("Seeding database...")

        # ── Games ──────────────────────────────────────────────────────────────
        for game_data in GAMES:
            existing = db.execute(
                select(Game).where(Game.slug == game_data["slug"])
            ).scalar_one_or_none()
            if existing:
                print(f"  Game '{game_data['slug']}' already exists — skipping")
                continue

            game = Game(**game_data)
            db.add(game)
            db.flush()

            # Default question set for each game
            q_set = QuestionSet(
                game_id=game.id,
                name="Default Set",
                difficulty_default="medium",
                is_active=True,
                is_daily_eligible=True,
            )
            db.add(q_set)
            print(f"  ✓ Created game: {game_data['name']}")

        # ── Cricketers ─────────────────────────────────────────────────────────
        added = 0
        for name, country in SAMPLE_CRICKETERS:
            exists = db.execute(
                select(Cricketer).where(Cricketer.name == name)
            ).scalar_one_or_none()
            if not exists:
                db.add(Cricketer(name=name, country=country))
                added += 1

        db.commit()
        print(f"  ✓ Added {added} cricketers to autocomplete list")
        print("\nSeed complete. Open the admin panel to add questions:")
        print("  Admin API: http://localhost:8000/api/admin/games")
        print("  SQLAdmin:  http://localhost:8000/admin")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
