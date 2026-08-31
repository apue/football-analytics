from football_analytics.academy_roster_parser import parse_roster_blocks


def test_parse_roster_blocks_uses_juvenil_a_region_and_role_rows():
    blocks = [
        (50, 70, 150, 90, "JUVENIL A\n"),
        (300, 200, 500, 220, "PORTERO: One Keeper y Two Keeper\n"),
        (300, 225, 520, 250, "DEFENSA: Three Back, Four Back\n"),
        (300, 255, 500, 275, "ENTRENADOR: Coach Name\n"),
        (50, 430, 150, 450, "JUVENIL B\n"),
        (300, 600, 500, 620, "PORTERO: Wrong Keeper\n"),
    ]

    candidates = parse_roster_blocks(
        blocks,
        academy_id="barca-u19",
        season_start=2016,
        source_url="official-report",
        source_page=25,
    )

    assert [(row.displayed_name, row.position) for row in candidates] == [
        ("One Keeper", "goalkeeper"),
        ("Two Keeper", "goalkeeper"),
        ("Three Back", "defender"),
        ("Four Back", "defender"),
    ]
    assert len({row.candidate_id for row in candidates}) == 4


def test_parse_roster_blocks_supports_catalan_role_labels():
    candidates = parse_roster_blocks(
        [
            (50, 70, 150, 90, "JUVENIL A"),
            (50, 300, 280, 320, "Porter: U, Dos"),
            (50, 325, 280, 345, "Migcampista: Tres, Quatre"),
            (50, 350, 280, 370, "Davanter: Cinc"),
        ],
        academy_id="barca-u19",
        season_start=2015,
        source_url="official-report",
        source_page=32,
    )

    assert [row.position for row in candidates] == [
        "goalkeeper",
        "goalkeeper",
        "midfielder",
        "midfielder",
        "forward",
    ]


def test_parse_roster_blocks_joins_wrapped_role_blocks():
    candidates = parse_roster_blocks(
        [
            (50, 70, 150, 90, "JUVENIL A"),
            (60, 400, 290, 410, "DEFENSA: One Back, Two Back,\n"),
            (60, 412, 250, 422, "Three Back, Four Back\n"),
            (60, 425, 250, 435, "DELANTERO: One Forward\n"),
        ],
        academy_id="barca-u19",
        season_start=2019,
        source_url="official-report",
        source_page=22,
    )

    assert [row.displayed_name for row in candidates] == [
        "One Back",
        "Two Back",
        "Three Back",
        "Four Back",
        "One Forward",
    ]
