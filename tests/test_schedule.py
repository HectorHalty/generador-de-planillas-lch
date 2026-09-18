from processor.names import names_equivalent
from processor.schedule import parse_schedule, sort_matches


def test_sort_category_then_court_then_time():
    parsed = parse_schedule(
        """
        Mujeres:
        Cancha 2
        16:00: Cebras vs Pido Bar
        12:00: Troyanas vs Caramelo
        Hombres:
        Cancha 8
        16:15: Coky F.C. vs Tres Dedos F.C.
        Cancha 1
        13:00: As Broma vs Mimetizarte
        11:30: Mambo F.C. vs Echale Pesteke
        """
    )
    ordered = sort_matches(parsed.matches, "category")
    assert [match.home for match in ordered] == [
        "Mambo F.C.",
        "As Broma",
        "Coky F.C.",
        "Troyanas",
        "Cebras",
    ]


def test_ignores_duplicate_lines():
    parsed = parse_schedule(
        """
        Hombres:
        Cancha 1
        11:30: Mambo F.C. vs Echale Pesteke
        11:30: Mambo F.C. vs Echale Pesteke
        """
    )
    assert len(parsed.matches) == 1


def test_short_names_do_not_collide():
    assert not names_equivalent("FAES", "Fútbol Champagne")
    assert not names_equivalent("ADN F.C.", "Aston Girls")
