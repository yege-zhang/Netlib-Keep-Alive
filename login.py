import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# 日志缓冲区
log_buffer = []

def log(msg):
    print(msg)
    log_buffer.append(msg)

def send_tg_log():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return  # 未配置则跳过

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_msg = f"📌 Netlib 保活执行日志\n🕒 {now}\n\n" + "\n".join(log_buffer)

    # 防止超出 Telegram 单条消息长度限制
    for i in range(0, len(final_msg), 3900):
        chunk = final_msg[i:i+3900]
        requests.get(
            f"https://api.telegram.org/bot{token}/sendMessage",
            params={"chat_id": chat_id, "text": chunk}
        )

# 从环境变量解析多个账号
accounts_env = os.environ.get("SITE_ACCOUNTS", "")
accounts = []

for item in accounts_env.split(";"):
    if item.strip():
        try:
            username, password = item.split(",", 1)
            accounts.append({"username": username.strip(), "password": password.strip()})
        except ValueError:
            log(f"⚠️ 忽略格式错误的账号项: {item}")

fail_msgs = [
    "Invalid credentials.",
    "Not connected to server.",
    "Error with the login: login size should be between 2 and 50 (currently: 1)"
]

def login_account(playwright, USER, PWD):
    log(f"🚀 开始登录账号: {USER}")
    try:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.netlib.re/")
        time.sleep(5)

        page.get_by_text("Login").click()
        time.sleep(2)
        page.get_by_role("textbox", name="Username").fill(USER)
        time.sleep(2)
        page.get_by_role("textbox", name="Password").fill(PWD)
        time.sleep(2)
        page.get_by_role("button", name="Validate").click()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        success_text = "You are the exclusive owner of the following domains."
        if page.query_selector(f"text={success_text}"):
            log(f"✅ 账号 {USER} 登录成功")
            time.sleep(5)
        else:
            failed_msg = None
            for msg in fail_msgs:
                if page.query_selector(f"text={msg}"):
                    failed_msg = msg
                    break
            if failed_msg:
                log(f"❌ 账号 {USER} 登录失败: {failed_msg}")
            else:
                log(f"❌ 账号 {USER} 登录失败: 未知错误")

        context.close()
        browser.close()

    except Exception as e:
        log(f"❌ 账号 {USER} 登录异常: {e}")

def run():
    with sync_playwright() as playwright:
        for acc in accounts:
            login_account(playwright, acc["username"], acc["password"])
            time.sleep(2)

if __name__ == "__main__":
    run()
    send_tg_log()  # 发送日志
