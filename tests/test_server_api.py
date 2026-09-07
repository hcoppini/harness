import pytest
import json
from server import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

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

