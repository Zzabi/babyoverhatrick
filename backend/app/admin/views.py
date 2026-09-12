"""
SQLAdmin views — mounted in FastAPI at /admin.
Content team can manage all game content from here without code deploys.
Admin access is gated by Clerk JWT + role='admin' in production.
In dev (DEV_BYPASS_AUTH=true), the /admin panel is open.
"""
from sqladmin import ModelView
from app.models.user import User
from app.models.game import Game, Category
from app.models.question import QuestionSet, Question, QuestionOption
from app.models.session import PlayerSession
from app.models.streak import Streak
from app.models.daily import DailyChallenge
from app.models.leaderboard import LeaderboardEntry


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.username, User.role, User.created_at]
    column_searchable_list = [User.email, User.username, User.clerk_user_id]
    column_sortable_list = [User.created_at, User.role]
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-users"


class GameAdmin(ModelView, model=Game):
    column_list = [Game.id, Game.slug, Game.name, Game.status, Game.sort_order]
    column_searchable_list = [Game.name, Game.slug]
    column_sortable_list = [Game.sort_order, Game.status]
    form_include_pk = True
    name = "Game"
    name_plural = "Games"
    icon = "fa-solid fa-gamepad"


class CategoryAdmin(ModelView, model=Category):
    column_list = [Category.id, Category.name, Category.slug, Category.parent_id]
    column_searchable_list = [Category.name]
    name = "Category"
    name_plural = "Categories"
    icon = "fa-solid fa-tags"


class QuestionSetAdmin(ModelView, model=QuestionSet):
    column_list = [QuestionSet.id, QuestionSet.name, QuestionSet.game_id, QuestionSet.is_active, QuestionSet.is_daily_eligible, QuestionSet.difficulty_default]
    column_searchable_list = [QuestionSet.name]
    column_sortable_list = [QuestionSet.is_active, QuestionSet.game_id]
    name = "Question Set"
    name_plural = "Question Sets"
    icon = "fa-solid fa-layer-group"


class QuestionAdmin(ModelView, model=Question):
    column_list = [Question.id, Question.question_type, Question.difficulty, Question.points, Question.is_active, Question.set_id]
    column_searchable_list = [Question.question_text]
    column_sortable_list = [Question.sort_order, Question.difficulty, Question.is_active]
    name = "Question"
    name_plural = "Questions"
    icon = "fa-solid fa-circle-question"


class QuestionOptionAdmin(ModelView, model=QuestionOption):
    column_list = [QuestionOption.id, QuestionOption.question_id, QuestionOption.option_text, QuestionOption.is_correct, QuestionOption.sort_order]
    name = "Answer Option"
    name_plural = "Answer Options"
    icon = "fa-solid fa-list-check"


class DailyChallengeAdmin(ModelView, model=DailyChallenge):
    column_list = [DailyChallenge.id, DailyChallenge.game_id, DailyChallenge.set_id, DailyChallenge.challenge_date]
    column_sortable_list = [DailyChallenge.challenge_date]
    name = "Daily Challenge"
    name_plural = "Daily Challenges"
    icon = "fa-solid fa-calendar-day"


class PlayerSessionAdmin(ModelView, model=PlayerSession):
    column_list = [PlayerSession.id, PlayerSession.game_id, PlayerSession.score, PlayerSession.status, PlayerSession.completed_at]
    can_create = False
    can_edit = False
    name = "Session"
    name_plural = "Sessions"
    icon = "fa-solid fa-chart-bar"


class LeaderboardAdmin(ModelView, model=LeaderboardEntry):
    column_list = [LeaderboardEntry.id, LeaderboardEntry.game_id, LeaderboardEntry.user_id, LeaderboardEntry.best_score, LeaderboardEntry.games_played]
    can_create = False
    name = "Leaderboard Entry"
    name_plural = "Leaderboard"
    icon = "fa-solid fa-trophy"


def register_admin_views(admin):
    """Register all admin views. Called from main.py."""
    for view in [
        GameAdmin,
        QuestionSetAdmin,
        QuestionAdmin,
        QuestionOptionAdmin,
        CategoryAdmin,
        DailyChallengeAdmin,
        UserAdmin,
        PlayerSessionAdmin,
        LeaderboardAdmin,
    ]:
        admin.add_view(view)
