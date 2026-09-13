"""Unit tests for School Homework & Exam tracking service."""

import sqlite3
import pytest
from app.db import init_db
from app.services import homework_service


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_homework.db"
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_add_and_get_homework(test_db):
    hw = homework_service.add_homework(
        subject="Matematyka R",
        title="Zadania 1-15 z geometrii analitycznej",
        due_date="2026-09-25",
        priority=2,
        notes="Wymagane dowody twierdzeń",
        conn=test_db,
    )
    assert hw["id"] is not None
    assert hw["subject"] == "Matematyka R"
    assert hw["completed"] is False

    upcoming = homework_service.get_upcoming_homework(conn=test_db)
    assert len(upcoming) == 1
    assert upcoming[0]["title"] == "Zadania 1-15 z geometrii analitycznej"


def test_toggle_and_delete_homework(test_db):
    hw = homework_service.add_homework(
        subject="Informatyka",
        title="Implementacja przeszukiwania binarnego",
        due_date="2026-09-24",
        conn=test_db,
    )
    
    toggled = homework_service.toggle_homework(hw["id"], conn=test_db)
    assert toggled["completed"] is True

    deleted = homework_service.delete_homework(hw["id"], conn=test_db)
    assert deleted is True

    remaining = homework_service.get_upcoming_homework(conn=test_db)
    assert len(remaining) == 0


def test_add_and_get_exams(test_db):
    exam = homework_service.add_exam(
        subject="Fizyka",
        title="Sprawdzian: Termodynamika i praca gazu",
        exam_date="2026-09-20",
        scope="Rozdział 3 i 4 podręcznika",
        conn=test_db,
    )
    assert exam["id"] is not None
    assert exam["subject"] == "Fizyka"

    upcoming_exams = homework_service.get_upcoming_exams(conn=test_db)
    assert len(upcoming_exams) == 1
    assert upcoming_exams[0]["title"] == "Sprawdzian: Termodynamika i praca gazu"
    assert "days_left" in upcoming_exams[0]


def test_json_school_data_import_and_export(test_db):
    sample_json = """
    {
        "homework": [
            {
                "subject": "Język Niemiecki",
                "title": "Napisz esej o technologii (150 słów)",
                "due_date": "2026-09-28",
                "priority": 1
            }
        ],
        "exams": [
            {
                "subject": "Matematyka R",
                "title": "Próbna Matura CKE",
                "exam_date": "2026-09-25",
                "scope": "Całość materiału klasa 1-2"
            }
        ]
    }
    """
    imported = homework_service.import_school_data_json(sample_json, conn=test_db)
    assert imported is True

    hw_list = homework_service.get_upcoming_homework(conn=test_db)
    assert any("Niemiecki" in h["subject"] for h in hw_list)

    exams = homework_service.get_upcoming_exams(conn=test_db)
    assert any("Próbna Matura" in e["title"] for e in exams)


def test_prune_expired_homework(test_db):
    # Overdue homework with past deadline
    homework_service.add_homework(
        subject="Historia",
        title="Zadanie z przeszłości",
        due_date="2026-09-01",
        conn=test_db,
    )
    # Active homework with future deadline
    homework_service.add_homework(
        subject="Matematyka",
        title="Zadanie z przyszłości",
        due_date="2026-09-20",
        conn=test_db,
    )

    # Calling get_upcoming_homework with today="2026-09-13" must prune past homework
    upcoming = homework_service.get_upcoming_homework(conn=test_db, today_str="2026-09-13")
    assert len(upcoming) == 1
    assert upcoming[0]["subject"] == "Matematyka"

    # Verify past item is completely deleted from the database
    cursor = test_db.cursor()
    cursor.execute("SELECT count(*) FROM homework_items WHERE due_date < '2026-09-13'")
    assert cursor.fetchone()[0] == 0
