"""FastAPI application: accounts, account requests, card management, and shuffled Review."""

import logging
import time
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Iterator

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from sqlite3 import Connection

from . import repository as repo
from .admin import ensure_admin
from .config import Settings, load_settings
from .db import connect, initialize
from .domain import (
    ValidationError,
    clean_deck_name,
    clean_note,
    shuffled_cards,
    utc_now,
    validate_password,
    validate_username,
)
from .security import (
    generate_temporary_password,
    hash_password,
    new_token,
    tokens_match,
    verify_password,
)

PACKAGE_DIR = Path(__file__).resolve().parent
SESSION_COOKIE = "vic_session"
CSRF_COOKIE = "vic_csrf"
CONTACT_MAX = 200
NOTE_MAX = 1000

logger = logging.getLogger(__name__)


class CardInput(BaseModel):
    front: str
    back: str

    model_config = ConfigDict(extra="forbid")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    initialize(settings.database_path)
    if settings.admin_username:
        try:
            with closing(connect(settings.database_path)) as connection:
                with connection:
                    action = ensure_admin(
                        connection, settings.admin_username, settings.admin_password
                    )
        except (ValueError, repo.UsernameTaken) as exc:
            raise RuntimeError(
                f"Administrator bootstrap (VIC_ADMIN_USERNAME) failed: {exc}"
            ) from exc
        logger.info("Administrator bootstrap for %r: %s", settings.admin_username, action)

    app = FastAPI(title="Virtual Index Cards", version="0.2.0")
    app.state.settings = settings
    templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    def get_connection(request: Request) -> Iterator[Connection]:
        connection = connect(request.app.state.settings.database_path)
        try:
            yield connection
        finally:
            connection.close()

    def current_user(request: Request, connection: Connection) -> object | None:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        return repo.get_session_user(connection, token, int(time.time()))

    def require_user(request: Request, connection: Annotated[Connection, Depends(get_connection)]) -> object:
        user = current_user(request, connection)
        if user is None:
            raise HTTPException(status_code=401, detail="Authentication required.")
        return user

    def require_admin(request: Request, connection: Annotated[Connection, Depends(get_connection)]) -> object:
        user = require_user(request, connection)
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Administrator access required.")
        return user

    def require_csrf(request: Request) -> None:
        if not tokens_match(
            request.cookies.get(CSRF_COOKIE), request.headers.get("X-CSRF-Token")
        ):
            raise HTTPException(status_code=403, detail="Invalid CSRF token.")

    def require_form_csrf(request: Request, csrf_token: str | None) -> None:
        if not tokens_match(request.cookies.get(CSRF_COOKIE), csrf_token):
            raise HTTPException(status_code=403, detail="Invalid CSRF token.")

    def set_auth_cookies(
        response: Response, session_token: str, csrf_token: str
    ) -> None:
        common = {
            "max_age": settings.session_ttl_seconds,
            "samesite": "lax",
            "secure": settings.cookie_secure,
            "path": "/",
        }
        response.set_cookie(SESSION_COOKIE, session_token, httponly=True, **common)
        response.set_cookie(CSRF_COOKIE, csrf_token, httponly=False, **common)

    def clear_auth_cookies(response: Response) -> None:
        response.delete_cookie(SESSION_COOKIE, path="/")
        response.delete_cookie(CSRF_COOKIE, path="/")

    def start_session(
        connection: Connection, user_id: int, response: Response
    ) -> None:
        session_token = new_token()
        csrf_token = new_token()
        repo.delete_expired_sessions(connection, int(time.time()))
        repo.create_session(
            connection,
            session_token,
            user_id,
            int(time.time()) + settings.session_ttl_seconds,
            utc_now(),
        )
        set_auth_cookies(response, session_token, csrf_token)

    def validated_note_pair(payload: CardInput) -> tuple[str, str]:
        try:
            return clean_note(payload.front, "Front"), clean_note(payload.back, "Back")
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    def render_admin_requests(
        request: Request,
        user: object,
        connection: Connection,
        error: str | None = None,
        status_code: int = 200,
    ) -> HTMLResponse:
        all_requests = repo.list_account_requests(connection, decided_limit=20)
        pending = [row for row in all_requests if row["status"] == "pending"]
        decided = [row for row in all_requests if row["status"] != "pending"]
        return templates.TemplateResponse(
            request,
            "admin_requests.html",
            {
                "user": user,
                "pending": pending,
                "decided": decided,
                "error": error,
                "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
            },
            status_code=status_code,
        )

    def render_admin_users(
        request: Request,
        user: object,
        connection: Connection,
        error: str | None = None,
        status_code: int = 200,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "admin_users.html",
            {
                "user": user,
                "users": repo.list_users(connection),
                "error": error,
                "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
            },
            status_code=status_code,
        )

    def render_admin_profile(
        request: Request,
        user: object,
        error: str | None = None,
        saved: str | None = None,
        status_code: int = 200,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "admin_profile.html",
            {
                "user": user,
                "error": error,
                "saved": saved,
                "env_admin_pinned": bool(request.app.state.settings.admin_password),
                "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
            },
            status_code=status_code,
        )

    def render_credentials(
        request: Request,
        user: object,
        username: str,
        password: str,
        heading: str,
        detail: str,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "admin_credentials.html",
            {
                "user": user,
                "account_username": username,
                "password": password,
                "heading": heading,
                "detail": detail,
                "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
            },
        )

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # --- Account request pages ---------------------------------------------

    @app.get("/register", response_class=HTMLResponse, tags=["accounts"])
    def register_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": None, "username": "", "contact": "", "note": ""},
        )

    @app.post("/register", tags=["accounts"])
    def register(
        request: Request,
        username: Annotated[str, Form()],
        connection: Annotated[Connection, Depends(get_connection)],
        contact: Annotated[str, Form()] = "",
        note: Annotated[str, Form()] = "",
    ) -> Response:
        username = username.strip()
        contact = contact.strip()
        note = note.strip()
        error = validate_username(username)
        if error is None and len(contact) > CONTACT_MAX:
            error = f"Contact must be at most {CONTACT_MAX} characters."
        if error is None and len(note) > NOTE_MAX:
            error = f"Note must be at most {NOTE_MAX} characters."
        if error is None:
            with connection:
                if repo.get_user_by_username(connection, username) is not None:
                    error = "That username is already taken. Please choose another."
                elif repo.find_pending_request(connection, username) is not None:
                    error = "That username already has a request awaiting review."
                else:
                    repo.create_account_request(
                        connection, username, contact or None, note or None, utc_now()
                    )
        if error is not None:
            return templates.TemplateResponse(
                request,
                "register.html",
                {"error": error, "username": username, "contact": contact, "note": note},
                status_code=400,
            )
        return RedirectResponse("/register/received", status_code=303)

    @app.get("/register/received", response_class=HTMLResponse, tags=["accounts"])
    def register_received(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "register_done.html", {})

    @app.get("/login", response_class=HTMLResponse, tags=["accounts"])
    def login_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "login.html", {"error": None})

    @app.post("/login", tags=["accounts"])
    def login(
        request: Request,
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> Response:
        user = repo.get_user_by_username(connection, username.strip())
        if user is None or not verify_password(
            password, user["salt"], user["password_hash"]
        ):
            return templates.TemplateResponse(
                request,
                "login.html",
                {"error": "Invalid username or password."},
                status_code=401,
            )
        response = RedirectResponse("/", status_code=303)
        with connection:
            start_session(connection, int(user["id"]), response)
        return response

    @app.post("/logout", tags=["accounts"])
    def logout(
        request: Request,
        csrf_token: Annotated[str, Form()],
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> Response:
        require_form_csrf(request, csrf_token)
        token = request.cookies.get(SESSION_COOKIE)
        if token:
            with connection:
                repo.delete_session(connection, token)
        response = RedirectResponse("/login", status_code=303)
        clear_auth_cookies(response)
        return response

    # --- Administrator: account request queue -------------------------------

    @app.get("/admin/requests", response_class=HTMLResponse, tags=["admin"])
    def admin_requests_page(
        request: Request,
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> Response:
        user = current_user(request, connection)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Administrator access required.")
        return render_admin_requests(request, user, connection)

    @app.post("/admin/requests/{request_id}/approve", response_class=HTMLResponse, tags=["admin"])
    def approve_request(
        request_id: int,
        request: Request,
        admin: Annotated[object, Depends(require_admin)],
        connection: Annotated[Connection, Depends(get_connection)],
        account_username: Annotated[str, Form()] = "",
        account_password: Annotated[str, Form()] = "",
        csrf_token: Annotated[str, Form()] = "",
    ) -> HTMLResponse:
        require_form_csrf(request, csrf_token)
        account_request = repo.get_account_request(connection, request_id)
        if account_request is None:
            raise HTTPException(status_code=404, detail="Request not found.")
        if account_request["status"] != "pending":
            return render_admin_requests(
                request, admin, connection,
                error="That request has already been decided.",
                status_code=409,
            )
        username = account_username.strip() or account_request["username"]
        error = validate_username(username)
        password = account_password or None
        if error is None and password is not None:
            error = validate_password(password)
        if error is None and repo.get_user_by_username(connection, username) is not None:
            error = f"The account name {username!r} is already taken; choose another."
        if error is not None:
            return render_admin_requests(request, admin, connection, error=error, status_code=400)

        final_password = password if password is not None else generate_temporary_password()
        with connection:
            salt, digest = hash_password(final_password)
            try:
                user_id = repo.create_user(
                    connection, username, salt, digest, utc_now(), role="user"
                )
            except repo.UsernameTaken:
                user_id = None
            if user_id is None:
                return render_admin_requests(
                    request, admin, connection,
                    error=f"The account name {username!r} is already taken; choose another.",
                    status_code=400,
                )
            decided = repo.decide_account_request(
                connection, request_id, "approved", int(admin["id"]), utc_now(), user_id
            )
            if not decided:
                # Lost a race with another decision: roll back the created account.
                raise HTTPException(status_code=409, detail="That request has already been decided.")
        return render_credentials(
            request,
            admin,
            username,
            final_password,
            heading="Account created",
            detail="Hand these credentials to the requester so they can log in. "
            "The password is shown only on this page and is never stored in plain text. "
            "If they lose it later, an administrator can reset it from the request queue.",
        )

    @app.post("/admin/requests/{request_id}/reject", tags=["admin"])
    def reject_request(
        request_id: int,
        request: Request,
        admin: Annotated[object, Depends(require_admin)],
        connection: Annotated[Connection, Depends(get_connection)],
        csrf_token: Annotated[str, Form()] = "",
    ) -> Response:
        require_form_csrf(request, csrf_token)
        account_request = repo.get_account_request(connection, request_id)
        if account_request is None:
            raise HTTPException(status_code=404, detail="Request not found.")
        with connection:
            decided = repo.decide_account_request(
                connection, request_id, "rejected", int(admin["id"]), utc_now()
            )
        if not decided:
            return render_admin_requests(
                request, admin, connection,
                error="That request has already been decided.",
                status_code=409,
            )
        return RedirectResponse("/admin/requests", status_code=303)

    @app.post("/admin/users/{user_id}/reset-password", response_class=HTMLResponse, tags=["admin"])
    def reset_user_password(
        user_id: int,
        request: Request,
        admin: Annotated[object, Depends(require_admin)],
        connection: Annotated[Connection, Depends(get_connection)],
        csrf_token: Annotated[str, Form()] = "",
    ) -> HTMLResponse:
        require_form_csrf(request, csrf_token)
        target = repo.get_user_by_id(connection, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Account not found.")
        if target["role"] == "admin":
            return render_admin_requests(
                request, admin, connection,
                error="Administrator passwords cannot be reset here; use the "
                "create_admin command with --password instead.",
                status_code=400,
            )
        new_password = generate_temporary_password()
        with connection:
            salt, digest = hash_password(new_password)
            repo.set_user_password(connection, user_id, salt, digest)
            repo.delete_user_sessions(connection, user_id)
        return render_credentials(
            request,
            admin,
            target["username"],
            new_password,
            heading="Password reset",
            detail="A temporary password was generated and all existing sessions for "
            "this account were signed out. Hand the new password to the user; it is "
            "shown only on this page and is never stored in plain text.",
        )

    # --- Administrator: user management ----------------------------------------

    @app.get("/admin/users", response_class=HTMLResponse, tags=["admin"])
    def admin_users_page(
        request: Request,
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> Response:
        user = current_user(request, connection)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Administrator access required.")
        return render_admin_users(request, user, connection)

    @app.post("/admin/users/{user_id}/delete", tags=["admin"])
    def delete_user(
        user_id: int,
        request: Request,
        admin: Annotated[object, Depends(require_admin)],
        connection: Annotated[Connection, Depends(get_connection)],
        csrf_token: Annotated[str, Form()] = "",
    ) -> Response:
        require_form_csrf(request, csrf_token)
        target = repo.get_user_by_id(connection, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Account not found.")
        if target["role"] == "admin":
            return render_admin_users(
                request,
                admin,
                connection,
                error="Administrator accounts cannot be deleted here. "
                "Remove the admin role via the create_admin command instead.",
                status_code=400,
            )
        with connection:
            repo.delete_user(connection, user_id)
        return RedirectResponse("/admin/users", status_code=303)

    # --- Administrator: own profile ------------------------------------------

    @app.get("/admin/profile", response_class=HTMLResponse, tags=["admin"])
    def admin_profile_page(
        request: Request,
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> Response:
        user = current_user(request, connection)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Administrator access required.")
        saved = request.query_params.get("saved")
        if saved not in ("updated", "nothing"):
            saved = None
        return render_admin_profile(request, user, saved=saved)

    @app.post("/admin/profile", tags=["admin"])
    def admin_profile_update(
        request: Request,
        username: Annotated[str, Form()],
        current_password: Annotated[str, Form()],
        admin: Annotated[object, Depends(require_admin)],
        connection: Annotated[Connection, Depends(get_connection)],
        new_password: Annotated[str, Form()] = "",
        confirm_password: Annotated[str, Form()] = "",
        csrf_token: Annotated[str, Form()] = "",
    ) -> Response:
        require_form_csrf(request, csrf_token)
        error: str | None = None
        if not verify_password(current_password, admin["salt"], admin["password_hash"]):
            error = "Current password is incorrect."

        username = username.strip()
        username_changed = username != admin["username"]
        if error is None and username_changed:
            if not username:
                error = "Username must not be empty."
            else:
                username_error = validate_username(username)
                if username_error is not None:
                    error = username_error
                elif username.lower() != admin["username"].lower():
                    existing = repo.get_user_by_username(connection, username)
                    if existing is not None and int(existing["id"]) != int(admin["id"]):
                        error = "That username is already taken."

        password_changed = bool(new_password)
        if error is None and password_changed:
            password_error = validate_password(new_password)
            if password_error is not None:
                error = password_error
            elif new_password != confirm_password:
                error = "The new passwords do not match."

        if error is not None:
            return render_admin_profile(request, admin, error=error, status_code=400)
        if not username_changed and not password_changed:
            return RedirectResponse("/admin/profile?saved=nothing", status_code=303)

        with connection:
            if username_changed:
                repo.update_username(connection, int(admin["id"]), username)
            if password_changed:
                salt, digest = hash_password(new_password)
                repo.set_user_password(connection, int(admin["id"]), salt, digest)
                repo.delete_user_sessions_except(
                    connection,
                    int(admin["id"]),
                    request.cookies.get(SESSION_COOKIE) or "",
                )
        return RedirectResponse("/admin/profile?saved=updated", status_code=303)

    # --- Deck pages and creation -------------------------------------------

    def require_selected_deck(
        connection: Connection, user_id: int, deck_id: int | None
    ) -> object:
        deck = repo.get_deck(connection, user_id, deck_id)
        if deck is None:
            raise HTTPException(status_code=404, detail="Deck not found.")
        return deck

    def render_deck_page(
        request: Request,
        user: object,
        connection: Connection,
        deck: object,
        error: str | None = None,
        status_code: int = 200,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "deck.html",
            {
                "user": user,
                "deck": deck,
                "decks": repo.list_decks(connection, int(user["id"])),
                "cards": repo.list_cards_newest_first(
                    connection, int(user["id"]), int(deck["id"])
                ),
                "deck_error": error,
                "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
            },
            status_code=status_code,
        )

    @app.post("/decks", tags=["decks"])
    def create_deck_page(
        request: Request,
        user: Annotated[object, Depends(require_user)],
        connection: Annotated[Connection, Depends(get_connection)],
        csrf_token: Annotated[str | None, Form()] = None,
        name: Annotated[str | None, Form()] = None,
        current_deck_id: Annotated[int | None, Form()] = None,
    ) -> Response:
        require_form_csrf(request, csrf_token)
        selected = require_selected_deck(
            connection, int(user["id"]), current_deck_id
        )
        try:
            clean_name = clean_deck_name(name) if name not in (None, "") else None
            with connection:
                deck = repo.create_deck(
                    connection, int(user["id"]), utc_now(), clean_name
                )
        except (ValidationError, repo.DeckNameTaken) as exc:
            return render_deck_page(
                request, user, connection, selected, str(exc), status_code=400
            )
        return RedirectResponse(f"/?deck_id={deck['id']}", status_code=303)

    @app.post("/decks/{deck_id}/rename", tags=["decks"])
    def rename_deck_page(
        deck_id: int,
        request: Request,
        user: Annotated[object, Depends(require_user)],
        connection: Annotated[Connection, Depends(get_connection)],
        name: Annotated[str, Form()],
        csrf_token: Annotated[str | None, Form()] = None,
    ) -> Response:
        require_form_csrf(request, csrf_token)
        deck = require_selected_deck(connection, int(user["id"]), deck_id)
        try:
            clean_name = clean_deck_name(name)
            with connection:
                renamed = repo.rename_deck(
                    connection, int(user["id"]), deck_id, clean_name
                )
        except (ValidationError, repo.DeckNameTaken) as exc:
            return render_deck_page(
                request, user, connection, deck, str(exc), status_code=400
            )
        if renamed is None:
            raise HTTPException(status_code=404, detail="Deck not found.")
        return RedirectResponse(f"/?deck_id={deck_id}", status_code=303)

    @app.get("/", response_class=HTMLResponse, tags=["ui"])
    def deck_page(
        request: Request,
        connection: Annotated[Connection, Depends(get_connection)],
        deck_id: int | None = None,
    ) -> Response:
        user = current_user(request, connection)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        deck = require_selected_deck(connection, int(user["id"]), deck_id)
        return render_deck_page(request, user, connection, deck)

    @app.get("/review", response_class=HTMLResponse, tags=["ui"])
    def review_page(
        request: Request,
        connection: Annotated[Connection, Depends(get_connection)],
        index: int = 0,
        deck_id: int | None = None,
    ) -> Response:
        user = current_user(request, connection)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        deck = require_selected_deck(connection, int(user["id"]), deck_id)
        decks = repo.list_decks(connection, int(user["id"]))
        cards = repo.list_cards(connection, int(user["id"]), int(deck["id"]))
        total = len(cards)
        position = index % total if total else 0
        return templates.TemplateResponse(
            request,
            "review.html",
            {
                "user": user,
                "deck": deck,
                "decks": decks,
                "card": cards[position] if cards else None,
                "position": position,
                "total": total,
                "prev_index": (position - 1) % total if total else 0,
                "next_index": (position + 1) % total if total else 0,
                "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
            },
        )

    # --- Card API -----------------------------------------------------------

    @app.post("/api/cards", status_code=status.HTTP_201_CREATED, tags=["cards"])
    def create_card(
        request: Request,
        payload: CardInput,
        user: Annotated[object, Depends(require_user)],
        connection: Annotated[Connection, Depends(get_connection)],
        deck_id: int | None = None,
    ) -> dict:
        require_csrf(request)
        front, back = validated_note_pair(payload)
        deck = require_selected_deck(connection, int(user["id"]), deck_id)
        with connection:
            card = repo.create_card(
                connection, int(user["id"]), front, back, utc_now(), int(deck["id"])
            )
        return {"card": asdict(card)}

    @app.patch("/api/cards/{card_id}", tags=["cards"])
    def update_card(
        card_id: int,
        request: Request,
        payload: CardInput,
        user: Annotated[object, Depends(require_user)],
        connection: Annotated[Connection, Depends(get_connection)],
        deck_id: int | None = None,
    ) -> dict:
        require_csrf(request)
        front, back = validated_note_pair(payload)
        deck = require_selected_deck(connection, int(user["id"]), deck_id)
        with connection:
            card = repo.update_card(
                connection, int(user["id"]), card_id, front, back, utc_now(), int(deck["id"])
            )
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found.")
        return {"card": asdict(card)}

    @app.delete("/api/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["cards"])
    def delete_card(
        card_id: int,
        request: Request,
        user: Annotated[object, Depends(require_user)],
        connection: Annotated[Connection, Depends(get_connection)],
        deck_id: int | None = None,
    ) -> Response:
        require_csrf(request)
        deck = require_selected_deck(connection, int(user["id"]), deck_id)
        with connection:
            removed = repo.delete_card(
                connection, int(user["id"]), card_id, int(deck["id"])
            )
        if not removed:
            raise HTTPException(status_code=404, detail="Card not found.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/deck/shuffle", tags=["deck"])
    def shuffle_deck(
        request: Request,
        user: Annotated[object, Depends(require_user)],
        connection: Annotated[Connection, Depends(get_connection)],
        deck_id: int | None = None,
    ) -> dict:
        require_csrf(request)
        deck = require_selected_deck(connection, int(user["id"]), deck_id)
        with connection:
            cards = repo.list_cards(connection, int(user["id"]), int(deck["id"]))
            shuffled = shuffled_cards(cards)
            repo.replace_positions(
                connection, int(user["id"]), shuffled, int(deck["id"])
            )
        return {"cards": [asdict(card) for card in shuffled]}

    return app


app = create_app()
