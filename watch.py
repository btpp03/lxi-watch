#!/usr/bin/env python3
"""LXI.be 免费主机（btpp03.lxi.be）开通监视。

- 每跑一次：查 DNS A 记录 + HTTPS 首页状态；顺手登面板看服务是否已从
  "provisioning" 变成可管理。
- 只有「真开通」才推 Telegram，推送后写 state.json 记住，之后静默。
- 由 cron-job.org 外部腿触发（本账号 GA 原生 schedule 不 fire）。

手动跑：python3 watch.py manual   → 无论开通与否都推一条现状
"""
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar
import re

HOST = "btpp03.lxi.be"
BASE = "https://lxi.be"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
SOURCE = (os.environ.get("INPUT_SOURCE") or sys.argv[-1] or "cron").strip()


def dns_ips():
    try:
        return sorted({ai[4][0] for ai in socket.getaddrinfo(HOST, 443, proto=socket.IPPROTO_TCP)})
    except Exception:
        return []


def http_probe():
    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request("https://" + HOST + "/", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            body = r.read(4000).decode("utf-8", "ignore")
            return r.status, len(body), body
    except urllib.error.HTTPError as e:
        return e.code, 0, ""
    except Exception as e:
        return 0, 0, str(e)


def panel_state(email, pw):
    """登录 lxi.be，读 /account/services，判断主机是否已可管理。"""
    if not email or not pw:
        return None
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def g(path):
        r = op.open(urllib.request.Request(BASE + path, headers={"User-Agent": UA}), timeout=40)
        return r.read().decode("utf-8", "ignore")

    try:
        page = g("/login")
        m = re.search(r'<input[^>]*name="csrf"[^>]*>', page)
        csrf = re.search(r'value="([^"]*)"', m.group(0)).group(1) if m else ""
        data = urllib.parse.urlencode({"csrf": csrf, "email": email, "password": pw}).encode()
        req = urllib.request.Request(
            BASE + "/login", data=data, method="POST",
            headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded",
                     "Origin": BASE, "Referer": BASE + "/login"})
        op.open(req, timeout=40).read()
        services = g("/account/services")
    except Exception as e:
        return {"error": str(e)[:160]}

    return {
        "provisioning": "Provisioning" in services,
        "has_host": HOST in services,
        "panel_link": bool(re.search(r'href="[^"]*(?:panel|webspace|hosting/)[^"]*"', services, re.I)),
    }


def notify(text):
    tok = os.environ.get("TG_BOT_TOKEN", "").strip()
    chat = os.environ.get("TG_CHAT_ID", "").strip()
    if not tok or not chat:
        print("[warn] TG creds missing, skip notify")
        return
    payload = {"chat_id": chat, "text": text, "disable_web_page_preview": True}
    th = os.environ.get("TG_THREAD_ID", "").strip()
    if th:
        payload["message_thread_id"] = int(th)
    req = urllib.request.Request(
        "https://api.telegram.org/bot%s/sendMessage" % tok,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print("tg", r.status)
    except Exception as e:
        print("tg fail", e)


def main():
    st = {"ready": False}
    if os.path.exists(STATE):
        try:
            st = json.load(open(STATE))
        except Exception:
            pass

    ips = dns_ips()
    code, blen, body = http_probe()
    live = bool(ips) and code in (200, 301, 302, 403)
    ps = panel_state(os.environ.get("LXI_EMAIL", ""), os.environ.get("LXI_PW", ""))

    print(json.dumps({"dns": ips, "http": code, "len": blen,
                      "panel": ps, "prev_ready": st.get("ready")}, ensure_ascii=False))

    ready = live and (not isinstance(ps, dict) or not ps.get("provisioning", True) or ps.get("panel_link"))
    already = bool(st.get("ready"))

    if ready and not already:
        notify("\n".join([
            "✅ LXI 主机开通了",
            "%s → HTTP %s" % (HOST, code),
            "IP: " + (", ".join(ips) or "—"),
            "面板: %s/account/services" % BASE,
            "账号: btpplxi9wy29a@euploading.com / Hlm@0649lxi",
        ]))
        st["ready"] = True
    elif SOURCE == "manual":
        notify("\n".join([
            "LXI 主机还没开通（手动查）",
            "DNS: " + (", ".join(ips) or "无 A 记录"),
            "HTTP: %s" % code,
            "panel: %s" % json.dumps(ps, ensure_ascii=False),
        ]))

    st.update({"last_check": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
               "dns": ips, "http": code})
    json.dump(st, open(STATE, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
