"""Unit tests for School timetable integration and URL launcher."""


import pytest
from datetime import datetime
from app.services import school_service, project_service


def test_school_optivum_parser_offline_mock():
    mock_html = """
    <html>
    <span class="tytulnapis">3lb</span>
    <table class="tabela">
      <tr>
        <th>Nr</th><th>Godz</th><th>Poniedziałek</th><th>Wtorek</th><th>Środa</th><th>Czwartek</th><th>Piątek</th>
      </tr>
      <tr>
        <td class="nr">1</td>
        <td class="g"> 8:00- 8:45</td>
        <td class="l"><span class="p">j.polski</span> <a class="n">AM</a> <a class="s">200</a></td>
        <td class="l"><span class="p">fizyka</span> <a class="n">MD</a> <a class="s">407</a></td>
        <td class="l"><span class="p">matematyka</span> <a class="n">ZK</a> <a class="s">112</a></td>
        <td class="l"><span class="p">j.angielski</span></td>
        <td class="l"><span class="p">informatyka</span> <a class="s">17</a></td>
      </tr>
      <tr>
        <td class="nr">2</td>
        <td class="g"> 8:50- 9:35</td>
        <td class="l"><span class="p">historia</span> <a class="s">101</a></td>
        <td class="l">&nbsp;</td>
        <td class="l"><span class="p">chemia</span> <a class="s">302</a></td>
        <td class="l">&nbsp;</td>
        <td class="l">&nbsp;</td>
      </tr>
    </table>
    </html>
    """
    plan = school_service.parse_optivum_html(mock_html)
    assert "Poniedziałek" in plan
    assert len(plan["Poniedziałek"]) == 2
    assert plan["Poniedziałek"][0]["subject"] == "j.polski"
    assert plan["Poniedziałek"][0]["time"] == "8:00- 8:45"
    assert plan["Poniedziałek"][0]["room"] == "200"

    assert len(plan["Wtorek"]) == 1
    assert plan["Wtorek"][0]["subject"] == "fizyka"


def test_get_lessons_for_weekday():
    mock_plan = {
        "Poniedziałek": [{"nr": 1, "time": "8:00- 8:45", "subject": "j.polski", "room": "200"}],
        "Wtorek": [{"nr": 1, "time": "8:00- 8:45", "subject": "fizyka", "room": "407"}],
    }
    # 2026-08-31 is Monday
    lessons_mon = school_service.get_lessons_for_date("2026-08-31", cached_plan=mock_plan)
    assert len(lessons_mon) == 1
    assert lessons_mon[0]["subject"] == "j.polski"

    # Saturday should have 0 lessons
    lessons_sat = school_service.get_lessons_for_date("2026-09-05", cached_plan=mock_plan)
    assert len(lessons_sat) == 0


def test_url_validation():
    assert school_service.is_safe_url("https://tm1.edu.pl") is True
    assert school_service.is_safe_url("http://planlekcji2.staff.edu.pl/") is True
    assert school_service.is_safe_url("javascript:alert(1)") is False
    assert school_service.is_safe_url("file:///C:/Windows/notepad.exe") is False


def test_easy_links_crud():
    original_links = school_service.get_easy_links()
    initial_count = len(original_links)

    # Add link
    new_link = school_service.add_easy_link(
        name="LeetCode Algorithms",
        url="https://leetcode.com",
        category="dev",
        desc="Daily algorithmic problem solving"
    )
    assert new_link["name"] == "LeetCode Algorithms"

    links = school_service.get_easy_links()
    assert len(links) == initial_count + 1
    new_idx = len(links) - 1

    # Update link
    updated = school_service.update_easy_link(
        index=new_idx,
        name="LeetCode Practice",
        url="https://leetcode.com/problemset",
        category="dev",
        desc="Daily practice"
    )
    assert updated is True

    links_after_update = school_service.get_easy_links()
    assert links_after_update[new_idx]["name"] == "LeetCode Practice"

    # Delete link
    deleted = school_service.delete_easy_link(new_idx)
    assert deleted is True
    assert len(school_service.get_easy_links()) == initial_count

