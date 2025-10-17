import re
import time
import os
from playwright.sync_api import sync_playwright, expect

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # --- Step 1: Register a new user (which is now auto-activated) ---
    page.goto("http://localhost:8000/users/signup/")
    page.locator('input[name="username"]').fill("verifyuser")
    page.locator('input[name="email"]').fill("verify@example.com")
    page.locator('input[name="password1"]').fill("aVeryGoodPassword123")
    page.locator('input[name="password2"]').fill("aVeryGoodPassword123")
    page.get_by_role("button", name="註冊").click()

    # --- Step 2: Log in directly ---
    expect(page.get_by_role("heading", name="登入")).to_be_visible()
    page.locator('input[name="username"]').fill("verifyuser")
    page.locator('input[name="password"]').fill("aVeryGoodPassword123")
    page.get_by_role("button", name="登入").click()

    # --- Step 3: Add stock and verify dashboard ---
    expect(page.get_by_role("heading", name="儀表板")).to_be_visible()
    page.get_by_placeholder("輸入股票代號 (e.g., 2330.TW)").fill("2330.TW")
    page.get_by_role("button", name="新增").click()

    # --- Step 4: Take screenshot ---
    expect(page.get_by_text("2330.TW")).to_be_visible()
    expect(page.locator("#chart-container")).to_be_visible()
    page.screenshot(path="jules-scratch/verification/verification.png")

    browser.close()

with sync_playwright() as playwright:
    run_verification(playwright)