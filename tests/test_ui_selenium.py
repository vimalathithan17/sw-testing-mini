import os
import socket
import threading
import time
from contextlib import closing

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By

# Utilities to start/stop a uvicorn server for the app during tests

def get_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_uvicorn(app_import: str, host: str, port: int):
    import uvicorn
    uvicorn.run(app_import, host=host, port=port, log_level="warning")


@pytest.fixture(scope="session")
def live_server():
    host = "127.0.0.1"
    port = get_free_port()
    thread = threading.Thread(target=run_uvicorn, args=("app.main:app", host, port), daemon=True)
    thread.start()

    # wait for server to be up
    url = f"http://{host}:{port}/health"
    import requests
    for _ in range(50):
        try:
            r = requests.get(url, timeout=0.2)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)
    else:
        pytest.skip("Server failed to start for Selenium tests")

    yield f"http://{host}:{port}"


@pytest.fixture(scope="session")
def browser():
    # Use Selenium Manager for automatic driver management; headless mode for CI
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        pytest.skip(f"Chrome not available for Selenium tests: {e}")
    yield driver
    try:
        driver.quit()
    except Exception:
        pass


def test_ui_homepage_loads(browser, live_server):
    browser.get(f"{live_server}/ui")
    assert "SW Testing Mini" in browser.page_source


def test_ui_create_user_and_order(browser, live_server):
    browser.get(f"{live_server}/ui")

    # Create user
    name_input = browser.find_element(By.NAME, "name")
    email_input = browser.find_element(By.NAME, "email")
    name_input.clear(); name_input.send_keys("S-User")
    email_input.clear(); email_input.send_keys("suser@example.com")
    name_input.submit()  # submits the first form (Create User)

    # Wait and verify user appears by refreshing
    time.sleep(0.2)
    browser.get(f"{live_server}/ui")
    assert "S-User" in browser.page_source

    # Find user id via API
    import requests
    users = requests.get(f"{live_server}/users").json()
    uid = [u["id"] for u in users if u["name"] == "S-User"][0]

    # Create order
    browser.get(f"{live_server}/ui")
    user_id_input = browser.find_element(By.NAME, "user_id")
    amount_input = browser.find_element(By.NAME, "amount")
    user_id_input.clear(); user_id_input.send_keys(str(uid))
    amount_input.clear(); amount_input.send_keys("7.235")
    amount_input.submit()

    time.sleep(0.2)
    browser.get(f"{live_server}/ui")
    assert "7.24" in browser.page_source


def test_ui_fk_violation_error(browser, live_server):
    browser.get(f"{live_server}/ui")

    user_id_input = browser.find_element(By.NAME, "user_id")
    amount_input = browser.find_element(By.NAME, "amount")
    user_id_input.clear(); user_id_input.send_keys("999999")
    amount_input.clear(); amount_input.send_keys("3.00")
    amount_input.submit()

    time.sleep(0.2)
    assert "foreign key" in browser.page_source.lower()


def test_ui_injection_like_search(browser, live_server):
    browser.get(f"{live_server}/ui?q=%25'%20OR%20'1'%3D'1")
    assert "No results" in browser.page_source
