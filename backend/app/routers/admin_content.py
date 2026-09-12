"""
Admin content management API.

Authentication: HTTP Basic Auth (ADMIN_USERNAME / ADMIN_PASSWORD from .env).
All endpoints require admin credentials — not accessible without them.

Endpoints cover:
  - Viewing and managing games and question sets
  - Adding questions for Guess the Cricketer (image_guess)
  - Adding questions for Unscramble (unscramble)
  - Managing the cricketers autocomplete list
  - Image upload to object storage (MinIO/R2)
"""
import secrets
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
from app.core.db import get_db
from app.core.config import settings
from app.core.storage import upload_bytes, public_url
from app.models.game import Game
from app.models.question import QuestionSet, Question, QuestionOption
from app.models.cricketer import Cricketer

router = APIRouter(prefix="/api/admin", tags=["admin-content"])
security = HTTPBasic()


# ── Auth dependency ────────────────────────────────────────────────────────────

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)) -> HTTPBasicCredentials:
    """Constant-time comparison to prevent timing attacks on credentials."""
    correct_user = secrets.compare_digest(
        credentials.username.encode(), settings.admin_username.encode()
    )
    correct_pass = secrets.compare_digest(
        credentials.password.encode(), settings.admin_password.encode()
    )
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


# ── Games ──────────────────────────────────────────────────────────────────────

@router.get("/games")
def list_games(
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    games = db.execute(select(Game).order_by(Game.sort_order)).scalars().all()
    return [{"id": g.id, "slug": g.slug, "name": g.name, "status": g.status} for g in games]


# ── Question sets ──────────────────────────────────────────────────────────────

@router.get("/games/{slug}/sets")
def list_question_sets(
    slug: str,
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    game = db.execute(select(Game).where(Game.slug == slug)).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    sets = db.execute(
        select(QuestionSet).where(QuestionSet.game_id == game.id).order_by(QuestionSet.id)
    ).scalars().all()
    return [{"id": s.id, "name": s.name, "is_active": s.is_active, "difficulty": s.difficulty_default} for s in sets]


class CreateSetRequest(BaseModel):
    name: str
    difficulty: str = "medium"
    is_active: bool = True


@router.post("/games/{slug}/sets")
def create_question_set(
    slug: str,
    body: CreateSetRequest,
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    game = db.execute(select(Game).where(Game.slug == slug)).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    q_set = QuestionSet(
        game_id=game.id,
        name=body.name,
        difficulty_default=body.difficulty,
        is_active=body.is_active,
        is_daily_eligible=True,
    )
    db.add(q_set)
    db.commit()
    db.refresh(q_set)
    return {"id": q_set.id, "name": q_set.name}


# ── Questions (read) ────────────────────────────────────────────────────────────

@router.get("/games/{slug}/questions")
def list_questions(
    slug: str,
    set_id: int | None = None,
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    """Admin view — includes correct answers."""
    game = db.execute(select(Game).where(Game.slug == slug)).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    query = select(Question).join(QuestionSet).where(QuestionSet.game_id == game.id)
    if set_id:
        query = query.where(Question.set_id == set_id)
    questions = db.execute(query.order_by(Question.id.desc())).scalars().all()

    result = []
    for q in questions:
        correct = next((o.option_text for o in q.options if o.is_correct), None)
        result.append({
            "id": q.id,
            "type": q.question_type,
            "set_id": q.set_id,
            "image_url": q.image_url,
            "question_text": q.question_text,
            "correct_answer": correct,
            "aliases": q.accepted_aliases,
            "difficulty": q.difficulty,
            "is_active": q.is_active,
            "explanation": q.explanation,
        })
    return result


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(q)
    db.commit()
    return {"deleted": True}


# ── Image upload ───────────────────────────────────────────────────────────────

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    """
    Upload an image to object storage (MinIO/R2).
    Filename is a UUID — intentionally opaque so the URL cannot reveal the answer.
    Returns the public URL to use in a question's image_url field.
    """
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP and GIF images are accepted")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "jpg"
    object_key = f"questions/{uuid.uuid4().hex}.{ext}"
    data = await file.read()
    url = upload_bytes(object_key, data, content_type=file.content_type or "image/jpeg")
    return {"url": url, "key": object_key}


# ── Add question: Guess the Cricketer (image_guess) ───────────────────────────

@router.post("/questions/image-guess")
async def add_image_guess_question(
    game_slug: str = Form("guess-the-cricketer"),
    set_id: int = Form(...),
    image_url: str = Form(...),      # URL from /admin/upload-image, or external URL
    answer: str = Form(...),         # cricketer's name (correct answer)
    aliases: str = Form(""),         # comma-separated alternate spellings
    difficulty: str = Form("medium"),
    points: int = Form(100),
    explanation: str = Form(""),
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    """
    Add a Guess the Cricketer question.
    The image_url must be an opaque UUID-named URL (from /admin/upload-image).
    The answer and aliases are stored server-side only; never returned to the client.
    """
    q_set = db.get(QuestionSet, set_id)
    if not q_set:
        raise HTTPException(status_code=404, detail="Question set not found")

    alias_list = [a.strip() for a in aliases.split(",") if a.strip()] if aliases else []

    question = Question(
        set_id=set_id,
        question_type="image_guess",
        image_url=image_url,
        difficulty=difficulty,
        points=points,
        explanation=explanation or None,
        accepted_aliases=alias_list,
        is_active=True,
    )
    db.add(question)
    db.flush()

    # Store correct answer as the single QuestionOption with is_correct=True
    option = QuestionOption(
        question_id=question.id,
        option_text=answer,
        is_correct=True,
    )
    db.add(option)

    # Auto-add the cricketer to the autocomplete list if not already present
    clean_name = answer.strip()
    existing_c = db.execute(
        select(Cricketer).where(Cricketer.name == clean_name)
    ).scalar_one_or_none()
    if not existing_c:
        db.add(Cricketer(name=clean_name, country=None))

    db.commit()

    return {"question_id": question.id, "image_url": image_url}


# ── Add question: Unscramble the Name ─────────────────────────────────────────

class UnscrambleRequest(BaseModel):
    game_slug: str = "unscramble-the-name"
    set_id: int
    answer: str            # cricketer name to unscramble, e.g. "KOHLI"
    country: str = ""      # e.g. "IND"
    role: str = ""         # e.g. "Top-order batter"
    difficulty: str = "medium"
    points: int = 100
    hints: list[str] = []  # hint strings shown progressively


@router.post("/questions/unscramble")
def add_unscramble_question(
    body: UnscrambleRequest,
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    """
    Add an Unscramble the Name question.
    The answer is stored server-side; client only receives scrambled letters.
    question_text stores "COUNTRY|ROLE" for display without revealing the answer.
    """
    q_set = db.get(QuestionSet, body.set_id)
    if not q_set:
        raise HTTPException(status_code=404, detail="Question set not found")

    # Store country|role in question_text — visible to client, not the answer
    display_text = f"{body.country}|{body.role}"

    # accepted_aliases: first entry is the canonical answer (uppercase), rest are hints
    aliases = [body.answer.upper()] + body.hints

    question = Question(
        set_id=body.set_id,
        question_type="unscramble",
        question_text=display_text,
        difficulty=body.difficulty,
        points=body.points,
        accepted_aliases=aliases,
        is_active=True,
    )
    db.add(question)
    db.flush()

    # Correct answer stored in QuestionOption
    option = QuestionOption(
        question_id=question.id,
        option_text=body.answer.upper(),
        is_correct=True,
    )
    db.add(option)
    db.commit()

    return {"question_id": question.id}


# ── Update existing question ───────────────────────────────────────────────────

class UpdateQuestionRequest(BaseModel):
    answer: str | None = None          # new correct answer text
    image_url: str | None = None       # new image URL (for image_guess)
    aliases: list[str] | None = None   # replace aliases/hints list
    difficulty: str | None = None
    points: int | None = None
    explanation: str | None = None
    is_active: bool | None = None
    # For unscramble: update display metadata
    country: str | None = None
    role: str | None = None


@router.patch("/questions/{question_id}")
def update_question(
    question_id: int,
    body: UpdateQuestionRequest,
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    """Update any field of an existing question. Only provided fields are changed."""
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    if body.difficulty is not None:
        q.difficulty = body.difficulty
    if body.points is not None:
        q.points = body.points
    if body.explanation is not None:
        q.explanation = body.explanation or None
    if body.is_active is not None:
        q.is_active = body.is_active
    if body.image_url is not None:
        q.image_url = body.image_url

    # Update correct answer in QuestionOption
    if body.answer is not None:
        correct_opt = db.execute(
            select(QuestionOption).where(
                QuestionOption.question_id == question_id,
                QuestionOption.is_correct == True,
            )
        ).scalar_one_or_none()
        if correct_opt:
            correct_opt.option_text = body.answer
        else:
            db.add(QuestionOption(question_id=question_id, option_text=body.answer, is_correct=True))
        # Also upsert cricketer if image_guess
        if q.question_type == "image_guess":
            clean = body.answer.strip()
            existing_c = db.execute(select(Cricketer).where(Cricketer.name == clean)).scalar_one_or_none()
            if not existing_c:
                db.add(Cricketer(name=clean, country=None))

    # Replace aliases / hints
    if body.aliases is not None:
        q.accepted_aliases = body.aliases

    # For unscramble: update country|role in question_text
    if q.question_type == "unscramble" and (body.country is not None or body.role is not None):
        current_country, current_role = "", ""
        if q.question_text and "|" in q.question_text:
            parts = q.question_text.split("|", 1)
            current_country, current_role = parts[0].strip(), parts[1].strip()
        new_country = body.country if body.country is not None else current_country
        new_role = body.role if body.role is not None else current_role
        q.question_text = f"{new_country}|{new_role}"

    db.commit()
    db.refresh(q)
    correct = next((o.option_text for o in q.options if o.is_correct), None)
    return {
        "id": q.id,
        "type": q.question_type,
        "correct_answer": correct,
        "aliases": q.accepted_aliases,
        "difficulty": q.difficulty,
        "is_active": q.is_active,
    }


# ── Update cricketer ───────────────────────────────────────────────────────────

class UpdateCricketerRequest(BaseModel):
    name: str | None = None
    country: str | None = None


@router.patch("/cricketers/{cricketer_id}")
def update_cricketer(
    cricketer_id: int,
    body: UpdateCricketerRequest,
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    """Update a cricketer's name or country."""
    c = db.get(Cricketer, cricketer_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cricketer not found")
    if body.name is not None:
        c.name = body.name.strip()
    if body.country is not None:
        c.country = body.country.strip().upper() or None
    db.commit()
    db.refresh(c)
    return {"id": c.id, "name": c.name, "country": c.country}


# ── Cricketers list ────────────────────────────────────────────────────────────

class CricketerRequest(BaseModel):
    name: str
    country: str = ""


@router.get("/cricketers")
def list_cricketers(
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    cricketers = db.execute(select(Cricketer).order_by(Cricketer.name)).scalars().all()
    return [{"id": c.id, "name": c.name, "country": c.country} for c in cricketers]


@router.post("/cricketers")
def add_cricketer(
    body: CricketerRequest,
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    existing = db.execute(
        select(Cricketer).where(Cricketer.name == body.name)
    ).scalar_one_or_none()
    if existing:
        return {"id": existing.id, "name": existing.name, "already_exists": True}

    cricketer = Cricketer(name=body.name, country=body.country or None)
    db.add(cricketer)
    db.commit()
    db.refresh(cricketer)
    return {"id": cricketer.id, "name": cricketer.name}


@router.delete("/cricketers/{cricketer_id}")
def delete_cricketer(
    cricketer_id: int,
    db: Session = Depends(get_db),
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    c = db.get(Cricketer, cricketer_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cricketer not found")
    db.delete(c)
    db.commit()
    return {"deleted": True}
