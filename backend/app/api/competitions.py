from flask import Blueprint

from ..competitions import get_competition, get_edition, list_competitions


bp = Blueprint("competitions", __name__, url_prefix="/api/competitions")


def _edition_response(edition):
    return {
        "competition": {
            "slug": edition.competition_slug,
            "display_name": edition.competition_display_name,
        },
        "edition": edition.public_dict(),
    }


@bp.get("")
def catalog():
    return {
        "competitions": [
            {
                "slug": edition.competition_slug,
                "display_name": edition.competition_display_name,
                "current_edition": edition.public_dict(),
            }
            for edition in list_competitions()
        ]
    }


@bp.get("/<competition_slug>")
def current_competition(competition_slug: str):
    edition = get_competition(competition_slug)
    return _edition_response(edition) if edition else ({"error": "Competition not found"}, 404)


@bp.get("/<competition_slug>/editions/<edition_slug>")
def competition_edition(competition_slug: str, edition_slug: str):
    edition = get_edition(competition_slug, edition_slug)
    return _edition_response(edition) if edition else ({"error": "Competition Edition not found"}, 404)
