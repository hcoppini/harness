import pytest
import json
import shutil
from pathlib import Path
from app.db import init_db, DEFAULT_DB_PATH
from app.services import sync_service
from server import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_server.db"
    test_data = tmp_path / "data"
    test_data.mkdir(parents=True, exist_ok=True)

    if DEFAULT_DB_PATH.exists():
        shutil.copy2(DEFAULT_DB_PATH, test_db)
    else:
        init_db(test_db)

    src_data = DEFAULT_DB_PATH.parent
    if src_data.exists():
        for jf in src_data.glob("*.json"):
            shutil.copy2(jf, test_data / jf.name)

    monkeypatch.setenv("HARNESS_DB_PATH", str(test_db))
    monkeypatch.setattr("app.db.DEFAULT_DB_PATH", test_db)
    monkeypatch.setattr(sync_service, "DATA_DIR", test_data)
    monkeypatch.setattr(sync_service, "CONFIG_FILE", test_data / "sync_config.json")
    import server
    monkeypatch.setattr(server, "DATA_DIR", test_data)
    from app.services import vulcan_service
    test_vulcan_config = test_data / "vulcan_config.json"
    if test_vulcan_config.exists():
        test_vulcan_config.unlink()
    monkeypatch.setattr(vulcan_service, "CONFIG_FILE", test_vulcan_config)


    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"

def test_dashboard_api(client):
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.get_json()
    assert "metrics" in data
    assert "heatmap" in data
    assert "upcoming" in data
    assert len(data["heatmap"]["weeks"]) >= 12

def test_today_api_and_tasks_crud(client):
    # 1. Get today
    res = client.get("/api/today")
    assert res.status_code == 200
    today_data = res.get_json()
    assert "schedule" in today_data
    assert "tasks" in today_data

    # 2. Add task
    add_res = client.post(
        "/api/tasks",
        data=json.dumps({"title": "Test REST Task", "category": "Code"}),
        content_type="application/json"
    )
    assert add_res.status_code == 200
    task = add_res.get_json()
    assert task["title"] == "Test REST Task"
    task_id = task["id"]

    # 3. Toggle task
    tog_res = client.post(f"/api/tasks/{task_id}/toggle")
    assert tog_res.status_code == 200
    toggled = tog_res.get_json()
    assert toggled["completed"] is True

    # 4. Delete task
    del_res = client.post(f"/api/tasks/{task_id}/delete")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True

def test_metro_api(client):
    res = client.get("/api/metro")
    assert res.status_code == 200
    data = res.get_json()
    assert "stations" in data

    # Toggle deliverable on sep-2026
    deliv_res = client.post(
        "/api/metro/sep-2026/deliverable",
        data=json.dumps({"deliverable_key": "Code"}),
        content_type="application/json"
    )
    assert deliv_res.status_code == 200
    deliv_data = deliv_res.get_json()
    assert deliv_data["success"] is True

    # Toggle back
    client.post(
        "/api/metro/sep-2026/deliverable",
        data=json.dumps({"deliverable_key": "Code"}),
        content_type="application/json"
    )

def test_body_api(client):
    res = client.get("/api/body")
    assert res.status_code == 200
    data = res.get_json()
    assert "target_weight_kg" in data

def test_rpc_dispatcher(client):
    # 1. Test get_dashboard via RPC
    res = client.post(
        "/api/rpc/get_dashboard",
        data=json.dumps({"args": []}),
        content_type="application/json"
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert "metrics" in data["result"]
    assert "heatmap" in data["result"]

    # 2. Test get_today via RPC
    res_today = client.post(
        "/api/rpc/get_today",
        data=json.dumps({"args": ["2026-09-01"]}),
        content_type="application/json"
    )
    assert res_today.status_code == 200
    today_res = res_today.get_json()
    assert today_res["status"] == "ok"
    assert "schedule" in today_res["result"]
    assert "tasks" in today_res["result"]

    # 3. Test get_easy_links via RPC
    res_links = client.post(
        "/api/rpc/get_easy_links",
        data=json.dumps({"args": []}),
        content_type="application/json"
    )
    assert res_links.status_code == 200
    assert isinstance(res_links.get_json()["result"], list)

    # 4. Test add_task / toggle_task / delete_task via RPC
    add_task_res = client.post(
        "/api/rpc/add_task",
        data=json.dumps({"args": ["RPC Test Task", "code", False, "2026-09-01"]}),
        content_type="application/json"
    )
    assert add_task_res.status_code == 200
    created_task = add_task_res.get_json()["result"]
    assert created_task["title"] == "RPC Test Task"
    task_id = created_task["id"]

    # Toggle task
    toggle_res = client.post(
        "/api/rpc/toggle_task",
        data=json.dumps({"args": [task_id]}),
        content_type="application/json"
    )
    assert toggle_res.status_code == 200
    assert toggle_res.get_json()["result"]["completed"] is True

    # Delete task
    delete_res = client.post(
        "/api/rpc/delete_task",
        data=json.dumps({"args": [task_id]}),
        content_type="application/json"
    )
    assert delete_res.status_code == 200
    assert delete_res.get_json()["result"] is True

    # 5. Test 404 on non-existent RPC method
    bad_res = client.post(
        "/api/rpc/non_existent_method_xyz",
        data=json.dumps({"args": []}),
        content_type="application/json"
    )
    assert bad_res.status_code == 404


def test_kill_list_rest_api(client):
    test_date = "2029-01-01"

    # 1. Get kill list
    res = client.get(f"/api/kill-list?date={test_date}")
    assert res.status_code == 200
    kl_data = res.get_json()
    assert "items" in kl_data
    assert "max_allowed" in kl_data

    # 2. Add kill list item
    add_res = client.post(
        "/api/kill-list",
        data=json.dumps({
            "category": "Math R",
            "title": "CKE Math R Arkusz 2024",
            "action_type": "pdf",
            "target_path": "arkusze/math.pdf",
            "target_spec": "Tasks 1-8",
            "station_deliverable_id": "sep26_math_diag",
            "date": test_date,
        }),
        content_type="application/json",
    )
    assert add_res.status_code == 201
    item = add_res.get_json()
    item_id = item["id"]
    assert item["title"] == "CKE Math R Arkusz 2024"

    # 3. Complete kill item (atomic link test)
    comp_res = client.post(f"/api/kill-list/{item_id}/complete")
    assert comp_res.status_code == 200
    comp_data = comp_res.get_json()
    assert comp_data["success"] is True
    assert comp_data["completed"] is True

    # 4. Toggle kill item
    toggle_res = client.post(f"/api/kill-list/{item_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.get_json()["completed"] is False

    # 5. Delete item
    del_res = client.delete(f"/api/kill-list/{item_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True


def test_tum_bavarian_aptitude_api(client):
    res = client.post(
        "/api/tum/aptitude",
        data=json.dumps({
            "gpa_pl": 5.5,
            "math_pl": 6.0,
            "cs_pl": 6.0,
            "lang_pl": 5.5,
        }),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_tum_points"] >= 88.0
    assert "DIRECT ADMISSION SAFE" in data["verdict"]


def test_static_routes_and_vercel_entrypoint(client):
    # Test Root Index
    res = client.get("/")
    assert res.status_code == 200
    assert b"HARNESS" in res.data

    # Test Static CSS
    res_css = client.get("/css/app.css")
    assert res_css.status_code == 200

    # Test Static JS
    res_js = client.get("/js/app.js")
    assert res_js.status_code == 200

    # Test Static API Bridge
    res_bridge = client.get("/js/api_bridge.js")
    assert res_bridge.status_code == 200

    # Test Mobile Index
    res_mobile = client.get("/mobile")
    assert res_mobile.status_code == 200

    # Test Manifest & Favicon
    res_manifest = client.get("/manifest.json")
    assert res_manifest.status_code == 200

    res_fav = client.get("/favicon.png")
    assert res_fav.status_code in (200, 404)

    # Test Vercel Entrypoint Module
    import os
    os.environ["VERCEL"] = "1"
    from api.index import app as vercel_app
    assert vercel_app is not None


def test_mobile_companion_assets_and_tabs(client):
    # Verify mobile HTML includes all 5 executive views and Kill List
    res_mobile = client.get("/mobile")
    assert res_mobile.status_code == 200
    html = res_mobile.get_data(as_text=True)
    assert "view-cockpit" in html
    assert "view-today" in html
    assert "view-tum" in html
    assert "view-projects" in html
    assert "view-body" in html
    assert "mKillList" in html

    # Verify mobile CSS includes editorial design system tokens
    res_css = client.get("/mobile/app.css")
    assert res_css.status_code == 200
    css = res_css.get_data(as_text=True)
    assert "--accent-lavender" in css
    assert "--bg-canvas" in css

    # Verify mobile JS includes extended mobile controller
    res_js = client.get("/mobile/app.js")
    assert res_js.status_code == 200
    js = res_js.get_data(as_text=True)
    assert "loadKillList" in js
    assert "loadProjects" in js



def test_sync_status_api(client):
    res = client.get("/api/sync/status")
    assert res.status_code == 200
    data = res.get_json()
    assert "status" in data
    assert "auto_sync" in data


def test_sync_exchange_api(client):
    import time
    uid = int(time.time() * 1000) % 900000 + 100000
    test_title = f"Direct Exchange Task {uid}"
    payload = {
        "client_time": "2026-09-12T22:30:00",
        "last_synced_at": None,
        "data": {
            "tasks": [
                {"id": uid, "title": test_title, "category": "Code", "is_tum": 1, "completed": 0, "date": "2026-09-12"}
            ],
            "daily_logs": [
                {
                    "date": "2099-09-01",
                    "scratchpad": "Exchange Scratchpad Note",
                    "wake_time": "06:45",
                    "sleep_time": "22:30",
                    "reflection_worked": "Sync logic implemented",
                    "reflection_slipped": "",
                    "reflection_tomorrow": "Rebuild exe",
                    "completed_blocks": "06:45-07:30",
                    "completed_exercises": "ex1",
                }
            ],
            "kill_list_items": [
                {
                    "id": f"k{uid}",
                    "date": "2026-09-12",
                    "category": "Raw CS",
                    "title": "Cross-sync test",
                    "action_type": "workspace",
                    "target_path": "c:/Users/heito/Desktop/harness",
                    "target_spec": "tests",
                    "completed": 1,
                }
            ],
            "body_metrics": [
                {
                    "id": uid,
                    "date": "2026-09-12",
                    "weight_kg": 71.2,
                    "calories_met": 1,
                    "protein_met": 1,
                    "notes": "Exchange weigh-in",
                }
            ],
            "workouts": [
                {
                    "id": uid,
                    "date": "2026-09-12",
                    "workout_type": "Gym",
                    "details": "Deadlift & Bench",
                    "intensity": 8,
                }
            ],
            "projects": [
                {
                    "id": uid,
                    "name": "Sync Module",
                    "description": "Cross device sync",
                    "current_milestone": "Testing",
                    "next_action": "Pytest",
                    "status": "active",
                }
            ],
        },
    }

    res = client.post(
        "/api/sync/exchange",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["synced_count"] >= 1
    assert "data" in data
    assert "tasks" in data["data"]
    # Check that the exchanged task exists in the returned server data
    task_titles = [t["title"] for t in data["data"]["tasks"]]
    assert test_title in task_titles

def test_dashboard_api_with_client_date(client):
    res = client.get("/api/dashboard?date=2026-09-13")
    assert res.status_code == 200
    data = res.get_json()
    assert data["heatmap"]["end_date"] == "2026-09-13"
    assert len(data["upcoming"]) == 7
    assert data["upcoming"][0]["date"] == "2026-09-14"

def test_probe_local_server_guarded():
    import os
    from app.services import sync_service
    os.environ["HARNESS_SERVER"] = "1"
    assert sync_service.probe_local_server() is None

def test_daily_log_update_and_persistence(client):
    res = client.post(
        "/api/today/log",
        data=json.dumps({
            "date": "2026-09-10",
            "completed_blocks": "0,1,2,3",
            "scratchpad": "Test scratchpad",
        }),
        content_type="application/json",
    )
    assert res.status_code == 200
    today_res = client.get("/api/today?date=2026-09-10")
    assert today_res.status_code == 200
    today_data = today_res.get_json()
    assert today_data["log"]["completed_blocks"] == "0,1,2,3"
    assert today_data["log"]["scratchpad"] == "Test scratchpad"


def test_four_day_selection_persistence_no_reset(client):
    """Ensure that selecting routine blocks & gym exercises across Sep 10-13 persists and never resets each other."""
    days_data = {
        "2026-09-10": {"completed_blocks": "0,1,2,3,4,5,6,7", "completed_exercises": "0,1,2,3,4,5"},
        "2026-09-11": {"completed_blocks": "0,1,2,3,4,5,6,7", "completed_exercises": ""},
        "2026-09-12": {"completed_blocks": "0,1,2", "completed_exercises": ""},
        "2026-09-13": {"completed_blocks": "0,1,2", "completed_exercises": ""},
    }

    # Post each day in sequence
    for dt, payload in days_data.items():
        res = client.post(
            "/api/today/log",
            data=json.dumps({"date": dt, **payload}),
            content_type="application/json",
        )
        assert res.status_code == 200

    # Verify each day independently retains its values without any cross-day overwrite
    for dt, expected in days_data.items():
        res = client.get(f"/api/today?date={dt}")
        assert res.status_code == 200
        data = res.get_json()
        assert "log" in data
        assert data["log"]["completed_blocks"] == expected["completed_blocks"]
        assert data["log"]["completed_exercises"] == expected["completed_exercises"]


def test_harness_3_workload_and_kill_list_routes(client):
    # 1. Sync Vulcan via POST /api/vulcan/sync
    sync_res = client.post(
        "/api/vulcan/sync",
        data=json.dumps({"date": "2026-09-14", "force": True}),
        content_type="application/json",
    )
    assert sync_res.status_code == 200
    sync_data = sync_res.get_json()
    assert sync_data["status"] == "synced"
    assert sync_data["exams_synced"] >= 4

    # 2. Get Workload Analysis via GET /api/workload
    wl_res = client.get("/api/workload?date=2026-09-14")
    assert wl_res.status_code == 200
    wl_data = wl_res.get_json()
    assert wl_data["mode"] == "SURGE"
    assert len(wl_data["upcoming_exams"]) >= 4

    # 3. Enqueue Progressive Deliverable (LeetCode #5)
    from app.db import get_connection
    conn = get_connection()
    conn.execute("DELETE FROM kill_list_items WHERE date = '2026-09-14'")
    conn.commit()
    conn.close()

    enq_res = client.post(
        "/api/kill-list/enqueue-progressive",
        data=json.dumps({"deliverable_id": "sep26_leetcode_15", "date": "2026-09-14"}),
        content_type="application/json",
    )
    assert enq_res.status_code == 200
    enq_data = enq_res.get_json()
    assert "Problem #5" in enq_data["target_spec"]
    assert enq_data["station_deliverable_id"] == "sep26_leetcode_15"


def test_sync_exchange_school_data(client):
    # Test bidirectional synchronization of school exams and homework items
    exchange_payload = {
        "school_exams": [
            {
                "id": 999,
                "subject": "Matematyka R",
                "title": "Sprawdzian Wektory",
                "exam_date": "2026-09-22",
                "scope": "Iloczyn skalarny i przestrzen trójwymiarowa",
                "completed": False,
                "result_percentage": None,
            }
        ],
        "homework_items": [
            {
                "id": 888,
                "subject": "Informatyka",
                "title": "Zadania CKE Grafy",
                "due_date": "2026-09-20",
                "completed": False,
                "source": "vulcan",
                "priority": 1,
                "notes": "BFS/DFS",
            }
        ],
    }

    res = client.post(
        "/api/sync/exchange",
        data=json.dumps(exchange_payload),
        content_type="application/json",
    )
    assert res.status_code == 200
    merged = res.get_json()
    data = merged.get("data", {})
    assert "school_exams" in data
    assert "homework_items" in data

    exam_ids = [e["id"] for e in data["school_exams"]]
    assert 999 in exam_ids
    hw_ids = [h["id"] for h in data["homework_items"]]
    assert 888 in hw_ids


def test_vulcan_status_and_manual_exam_endpoints(client, tmp_path, monkeypatch):
    from app.services import vulcan_service
    temp_config = tmp_path / "temp_server_vulcan_config.json"
    monkeypatch.setattr(vulcan_service, "CONFIG_FILE", temp_config)

    # 1. Check status
    res = client.get("/api/vulcan/status")

    assert res.status_code == 200
    st = res.get_json()
    assert "mode" in st
    assert "is_connected" in st

    # 2. Add manual exam
    manual_payload = {
        "subject": "Informatyka R",
        "title": "Sprawdzian: Drzewa BST",
        "exam_date": "2026-09-25",
        "scope": "Wstawianie, usuwanie, rotacje AVL",
        "weight": 3,
    }
    res_manual = client.post(
        "/api/school/exam/manual",
        data=json.dumps(manual_payload),
        content_type="application/json",
    )
    assert res_manual.status_code == 200
    ex = res_manual.get_json()
    assert ex["subject"] == "Informatyka R"
    assert ex["title"] == "Sprawdzian: Drzewa BST"
    assert ex["id"] is not None

    # 3. Disconnect
    res_disc = client.post("/api/vulcan/disconnect")
    assert res_disc.status_code == 200
    assert res_disc.get_json().get("success") is True



