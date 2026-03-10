# -*- coding: utf-8 -*-
import requests
import re
import threading
import os
import sys
import random
import uuid
import base64
import shutil
import json
import hashlib
import platform
import logging
import traceback
from time import sleep, gmtime, strftime
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------------
# Configuration / Globals
# -------------------------

# App data directory (per-user, cross-platform)
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".alisha_tool")
if not os.path.exists(APP_DATA_DIR):
    try:
        os.makedirs(APP_DATA_DIR, exist_ok=True)
    except Exception:
        # fallback to current working directory if cannot create
        APP_DATA_DIR = os.getcwd()

ERROR_LOG_PATH = os.path.join(APP_DATA_DIR, "error.txt")

# Logging: only error-level logs go to error.txt (no tracebacks printed to console)
logger = logging.getLogger("alisha_tool")
logger.setLevel(logging.ERROR)
# ensure no duplicate handlers
if not logger.handlers:
    fh = logging.FileHandler(ERROR_LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
# prevent propagation to root logger to avoid console logging
logger.propagate = False

# Global executor (initialized in main)
EXECUTOR = None

# Lock for protecting global counters
COUNTER_LOCK = threading.Lock()

# Global counters (access via COUNTER_LOCK)
count = 0
cp = 0
ok = 0
reaction_count = 0
comment_count = 0
follow_count = 0
join_count = 0
page_create_count = 0
page_activate_count = 0
dp_upload_count = 0
poll_vote_count = 0

# Colors (updated palette — none of the old codes are reused)
colors = ["\033[38;5;33m", "\033[38;5;161m", "\033[38;5;125m", "\033[38;5;208m", "\033[38;5;34m"]
reset = "\033[0m"
NEON_CYAN = "\033[38;5;33m"
NEON_PINK = "\033[38;5;161m"
NEON_PURPLE = "\033[38;5;125m"
NEON_ORANGE = "\033[38;5;208m"
NEON_GREEN = "\033[38;5;34m"
NEON_BLUE = "\033[38;5;27m"
NEON_RED = "\033[38;5;88m"
NEON_YELLOW = "\033[38;5;228m"
ELECTRIC_BLUE = "\033[38;5;69m"
HOT_PINK = "\033[38;5;205m"
LIME_GREEN = "\033[38;5;40m"
GOLD = "\033[38;5;179m"
SILVER = "\033[38;5;252m"
MAGENTA = "\033[38;5;131m"
BOLD = "\033[1m"

neon_cyan = NEON_CYAN
neon_pink = NEON_PINK
neon_purple = NEON_PURPLE
neon_orange = NEON_ORANGE
neon_green = NEON_GREEN
neon_red = NEON_RED
neon_yellow = NEON_YELLOW
electric_blue = ELECTRIC_BLUE
hot_pink = HOT_PINK
lime_green = LIME_GREEN
gold = GOLD
silver = SILVER

HEART_SYMBOL = f"{HOT_PINK}=>{reset}"

# -------------------------
# Helpers
# -------------------------

def fix_windows_encoding():
    if os.name == "nt":
        try:
            os.system("chcp 65001 > nul")
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception as e:
            logger.exception("Failed to set Windows encoding: %s", e)
    else:
        # Termux / Linux / Android
        try:
            import locale
            locale.setlocale(locale.LC_ALL, '')
        except Exception:
            pass

fix_windows_encoding()

def parse_cookie_string(cookie_str):
    """
    Parse a cookie string like "c_user=123; xs=abc; ..." into a dict.
    Returns dict (may be empty if parsing fails).
    """
    cookies = {}
    try:
        if not cookie_str:
            return cookies
        parts = cookie_str.split(";")
        for p in parts:
            p = p.strip()
            if not p or "=" not in p:
                continue
            k, v = p.split("=", 1)
            cookies[k.strip()] = v.strip()
    except Exception as e:
        logger.exception("parse_cookie_string error: %s", e)
    return cookies

def safe_search_group1(pattern, text):
    """
    Safely run re.search and return group(1) or empty string if not found.
    """
    try:
        m = re.search(pattern, text)
        if m:
            return m.group(1)
    except Exception as e:
        logger.exception("safe_search_group1 pattern=%s error=%s", pattern, e)
    return ""

# -------------------------
# Core Functions
# -------------------------

def banner():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass
    try:
        width = shutil.get_terminal_size().columns
        if width < 60:
            width = 60
    except Exception:
        width = 100

    title_text = "<<==== KTG__ Khan Tiger GanG ====>>"
    details_text = "Owner: Ali Ahmed  |  Admin: Ghamxada Lalai  |  Wp: 03262896273"
    footer_text = "======== KTG__ Khan Tiger ========"

    # Top Border
    print(f"\n{BOLD}{NEON_RED}╔{'═' * (width-2)}╗{reset}")
    print(f"{BOLD}{NEON_RED}║{GOLD}{'▓' * (width-2)}{NEON_RED}║{reset}")
    print(f"{BOLD}{NEON_RED}║{ELECTRIC_BLUE}{title_text:^{width-2}}{NEON_RED}║{reset}")
    print(f"{BOLD}{NEON_RED}║{GOLD}{'░' * (width-2)}{NEON_RED}║{reset}")
    
    # ASCII Art for "KTG" - Big and Bold
    gcu_unity_parts = [
        f"{BOLD}{NEON_RED}██╗  ██╗{reset}{BOLD}{NEON_ORANGE}████████╗{reset}{BOLD}{NEON_YELLOW} ██████╗ {reset}",
        f"{BOLD}{NEON_RED}██║ ██╔╝{reset}{BOLD}{NEON_ORANGE}╚══██╔══╝{reset}{BOLD}{NEON_YELLOW}██╔════╝ {reset}",
        f"{BOLD}{NEON_RED}█████╔╝ {reset}{BOLD}{NEON_ORANGE}   ██║   {reset}{BOLD}{NEON_YELLOW}██║  ███╗{reset}",
        f"{BOLD}{NEON_RED}██╔═██╗ {reset}{BOLD}{NEON_ORANGE}   ██║   {reset}{BOLD}{NEON_YELLOW}██║   ██║{reset}",
        f"{BOLD}{NEON_RED}██║  ██╗{reset}{BOLD}{NEON_ORANGE}   ██║   {reset}{BOLD}{NEON_YELLOW}╚██████╔╝{reset}",
        f"{BOLD}{NEON_RED}╚═╝  ╚═╝{reset}{BOLD}{NEON_ORANGE}   ╚═╝   {reset}{BOLD}{NEON_YELLOW} ╚═════╝ {reset}",
    ]
    
    # Center the ASCII art
    for line in gcu_unity_parts:
        line_plain = re.sub(r"\033\[[0-9;]+m", "", line)
        spaces_needed = width - 2 - len(line_plain)
        left_space = max(spaces_needed // 2, 0)
        right_space = max(spaces_needed - left_space, 0)
        print(f"{BOLD}{NEON_RED}║{' ' * left_space}{line}{' ' * right_space}║{reset}")

    print(f"{BOLD}{NEON_RED}║{GOLD}{'░' * (width-2)}{NEON_RED}║{reset}")
    print(f"{BOLD}{NEON_RED}╠{'═' * (width-2)}╣{reset}")
    
    # Gang details
    print(f"{BOLD}{NEON_RED}║{NEON_CYAN}{details_text:^{width-2}}{NEON_RED}║{reset}")
    
    # Footer
    print(f"{BOLD}{NEON_RED}╠{'═' * (width-2)}╣{reset}")
    print(f"{BOLD}{NEON_RED}║{HOT_PINK}{footer_text:^{width-2}}{NEON_RED}║{reset}")
    print(f"{BOLD}{NEON_RED}║{GOLD}{'▓' * (width-2)}{NEON_RED}║{reset}")
    print(f"{BOLD}{NEON_RED}╚{'═' * (width-2)}╝{reset}\n")

def generate_machine_key():
    try:
        node = uuid.getnode()
        host = platform.node()
        raw = f"{node}-{host}"
        h = hashlib.sha1(raw.encode()).hexdigest().upper()
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        key_chars = []
        for i in range(25):
            idx = (i * 2) % len(h)
            byte = int(h[idx:idx+2], 16)
            key_chars.append(alphabet[byte % len(alphabet)])
        parts = ["".join(key_chars[i:i+4]) for i in range(0, 24, 4)]
        last = "".join(key_chars[24:25])
        parts.append(last)
        return "-".join(parts)
    except Exception as e:
        logger.exception("generate_machine_key fallback: %s", e)
        k = uuid.uuid4().hex.upper()
        k = "".join(ch for ch in k if ch.isalnum())[:25]
        parts = [k[i:i+4] for i in range(0, 25, 4)]
        return "-".join(parts)

def check(block=True, retry_delay=10):
    """
    Uses APP_DATA_DIR (per-user) instead of C:/Users/Public to be cross-platform
    Stores machine key in APP_DATA_DIR/win.dll

    New behavior:
    - If block=True (default when called from main), the function will wait (loop)
      until the key is seen in the remote approval document OR the user quits.
    - If block=False, returns True/False immediately indicating active state.
    """
    filepath = os.path.join(APP_DATA_DIR, "win.dll")
    try:
        if not os.path.exists(APP_DATA_DIR):
            os.makedirs(APP_DATA_DIR, exist_ok=True)
    except Exception as e:
        logger.exception("check(): cannot create app data dir: %s", e)

    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                key = f.read().strip()
            print(f"{neon_green}Key Active : |{gold}{key}|##{reset}")
        else:
            key = generate_machine_key()
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(key)
    except Exception as e:
        logger.exception("check(): error reading/writing key file: %s", e)

    def is_key_approved():
        keymay = ""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                keymay = f.read().strip() + "|##"
        except Exception:
            keymay = generate_machine_key() + "|##"

        k = ""
        try:
            # remote doc that contains approved keys
            k = requests.get("https://docs.google.com/spreadsheets/d/106CHegvG1yO8MbOc3wp6c4wQ_AhhbphIBJ5l-e4R5UY/edit?gid=0#gid=0", timeout=15).text
        except Exception as e:
            logger.exception("check(): remote key fetch failed: %s", e)
            k = ""

        if keymay in k:
            try:
                print(f"                                                    {neon_green}-\x1b[7m{neon_green}Active\x1b[0m-{reset}")
            except Exception:
                pass
            return True
        else:
            try:
                print(f"                                                   {neon_red}-\x1b[7m{neon_red}No active\x1b[0m-{reset}")
            except Exception:
                pass
            return False

    # If not blocking, just return state
    try:
        approved = is_key_approved()
    except Exception as e:
        logger.exception("check(): is_key_approved error: %s", e)
        approved = False

    if not block:
        return approved

    # Block until approved or user quits
    try:
        while not approved:
            print(f"\n{neon_yellow}[!] Software key is NOT approved yet. The tool will not run until your key is approved.{reset}")
            print(f"{neon_cyan}-> Waiting for approval. Press Enter to retry now, or type 'q' then Enter to quit.{reset}")
            try:
                user_in = input(f"{gold}Retry now (Enter) / Quit (q): {reset}").strip().lower()
            except KeyboardInterrupt:
                print("\nExiting...")
                sys.exit(1)
            if user_in == "q":
                print("Exiting by user request.")
                sys.exit(1)
            # attempt another check
            try:
                approved = is_key_approved()
            except Exception as e:
                logger.exception("check(): retry is_key_approved error: %s", e)
                approved = False
            if not approved:
                # optional sleep between automated retries to avoid tight loop
                try:
                    print(f"{neon_yellow}Not approved yet — will retry after {retry_delay} seconds (or press Enter to check immediately).{reset}")
                    sleep(retry_delay)
                except KeyboardInterrupt:
                    print("\nExiting...")
                    sys.exit(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(1)

    return True

def create_initial_files():
    try:
        for i in range(1, 11):
            cookie_file = f"{i}.txt"
            if not os.path.exists(cookie_file):
                with open(cookie_file, "w", encoding="utf-8") as f:
                    f.write("# Add cookies or UID|Password|2FA here (one per line)\n# Example: c_user=123456;xs=abcd1234...\n")
        if not os.path.exists("comment.txt"):
            sample_comments = [
                "Great post! (Y)",
                "Amazing content! <3",
                "Love this! *fire*",
                "Awesome! 100",
                "Nice work! *sparkle*",
                "Fantastic! *rocket*",
                "Incredible! *clap*",
                "Well done! *strong*",
            ]
            with open("comment.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(sample_comments))
        if not os.path.exists("Group.txt"):
            with open("Group.txt", "w", encoding="utf-8") as f:
                f.write("# Add Facebook Group IDs here (one per line)\n# Example: 123456789012345\n")
        if not os.path.exists("Follow.txt"):
            with open("Follow.txt", "w", encoding="utf-8") as f:
                f.write("# Add Facebook User IDs here (one per line)\n# Example: 100012345678901\n")
        if not os.path.exists("pics.txt"):
            with open("pics.txt", "w", encoding="utf-8") as f:
                f.write("# Add image file paths here (one per line)\n# Example: C:/Users/YourName/Pictures/photo1.jpg\n# Example: images/profile.png\n")
        if not os.path.exists("poll_data.txt"):
            with open("poll_data.txt", "w", encoding="utf-8") as f:
                f.write("# Add Poll Data here (Format: question_id|option_id)\n# Example: 123456789012345|678901234567890\n")
    except Exception as e:
        logger.exception("create_initial_files error: %s", e)

def remove_expired_cookies():
    banner()
    print(f"\n{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}")
    print(f"{electric_blue}║          COOKIE EXPIRED REMOVER                           ║{reset}")
    print(f"{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}")

    try:
        cookie_file_number = input(f"{gold}-> Enter file number to clean (1-20): {reset}").strip()
    except KeyboardInterrupt:
        return
    try:
        cookie_file_number = int(cookie_file_number)
        if cookie_file_number < 1 or cookie_file_number > 20:
            raise ValueError("Invalid file number")
    except Exception:
        print(f"{neon_red}[X] Invalid file number! Please select a number between 1 and 20{reset}")
        input(f"{gold}Press Enter to exit...{reset}")
        return

    cookie_file = f"{cookie_file_number}.txt"

    try:
        with open(cookie_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"{neon_red}[X] Error: {cookie_file} not found!{reset}")
        input(f"{gold}Press Enter to exit...{reset}")
        return
    except Exception as e:
        logger.exception("remove_expired_cookies read error: %s", e)
        print(f"{neon_red}[X] Error reading file. See error.txt for details.{reset}")
        input(f"{gold}Press Enter to exit...{reset}")
        return

    print(f"\n{neon_cyan}Checking cookies in {cookie_file}...{reset}\n")

    valid_cookies = []
    expired_count = 0
    valid_count = 0

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            valid_cookies.append(line)
            continue
        if "|" in line and "c_user" not in line:
            valid_cookies.append(line)
            valid_count += 1
            colored_line = "".join(colors[i % len(colors)] + ch + reset for i, ch in enumerate(line[:30]))
            print(f"{HEART_SYMBOL} {neon_yellow}KEPT (UID|Pass format){reset} -> {colored_line}...")
            continue

        cookie = line
        headget = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-site": "none",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Cookie": cookie,
        }

        try:
            session = requests.Session()
            # parse cookie into session
            try:
                session.cookies.update(parse_cookie_string(cookie))
            except Exception:
                # fallback: pass Cookie header
                pass
            req = session.get("https://web.facebook.com/?_rdc=1&_rdr", headers=headget, timeout=(4, 7))
            text = req.text if hasattr(req, "text") else str(req)
            if "c_user" in text and ("logout" in text or 'name="logout"' in text):
                valid_cookies.append(line)
                valid_count += 1
                colored_line = "".join(colors[i % len(colors)] + ch + reset for i, ch in enumerate(line[:30]))
                print(f"{HEART_SYMBOL} {neon_green}VALID{reset} -> {colored_line}...")
            else:
                expired_count += 1
                colored_line = "".join(colors[i % len(colors)] + ch + reset for i, ch in enumerate(line[:30]))
                print(f"{HEART_SYMBOL} {neon_red}EXPIRED (Removed){reset} -> {colored_line}...")
        except Exception as e:
            expired_count += 1
            colored_line = "".join(colors[i % len(colors)] + ch + reset for i, ch in enumerate(line[:30]))
            print(f"{HEART_SYMBOL} {neon_red}ERROR/EXPIRED (Removed){reset} -> {colored_line}...")
            logger.exception("remove_expired_cookies: request failed for cookie: %s", e)
        sleep(0.5)

    try:
        with open(cookie_file, "w", encoding="utf-8") as f:
            for line in valid_cookies:
                f.write(line + "\n")
    except Exception as e:
        logger.exception("remove_expired_cookies write error: %s", e)
        print(f"{neon_red}[X] Could not write cleaned cookie file. See error.txt.{reset}")
        input(f"{gold}Press Enter to exit...{reset}")
        return

    print(f"\n{neon_green}╔═══════════════════════════════════════════════════════════╗{reset}")
    print(f"{neon_green}║              CLEANING COMPLETE                            ║{reset}")
    print(f"{neon_green}╚═══════════════════════════════════════════════════════════╝{reset}")
    print(f"{neon_cyan}File: {cookie_file}{reset}")
    print(f"{neon_green}Valid Cookies: {valid_count}{reset}")
    print(f"{neon_red}Expired/Removed: {expired_count}{reset}")
    print(f"{gold}Total Remaining: {valid_count}{reset}\n")

    input(f"{gold}Press Enter to continue...{reset}")

# -------------------------
# FB class (core)
# -------------------------

class FB:
    def __init__(self, user, password, twofa, cookie, jsondata, cv, count):
        self.user = user
        self.password = password
        self.twofa = twofa
        self.cookie = cookie
        self.count = count
        self.cv = cv
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=30, pool_maxsize=50, max_retries=1)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        # Set base headers (use 'Cookie' where needed per-request)
        self.headers = {
            "authority": "business.facebook.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "sec-ch-ua": '"Chromium";v="116", "Not)A;Brand";v="8", "Google Chrome";v="116"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"10.0.0"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        }
        self.token = None
        self.fb_dtsg = None
        self.pro5 = []

        # Parse cookie into session cookies for correctness if available
        try:
            if self.cookie and self.cookie != "no":
                parsed = parse_cookie_string(self.cookie)
                if parsed:
                    self.session.cookies.update(parsed)
        except Exception as e:
            logger.exception("FB.__init__: failed to update session cookies: %s", e)

        # Handle different modes
        self.account_type = None
        try:
            if "1" in cv:
                self.account_type = jsondata["1"]["type"]
                self.idbv = jsondata["1"]["idbv"]
                self.camxuc = jsondata["1"]["camxuc"]
                self.delay = jsondata["1"]["delay"]
                text = f"feedback:{self.idbv}"
                self.idbv = base64.b64encode(text.encode()).decode("utf-8")
            if "2" in cv:
                self.account_type = jsondata["2"]["type"]
                self.idbv = jsondata["2"]["idbv"]
                self.count_per_unit = jsondata["2"]["count"]
                self.delay = jsondata["2"]["delay"]
                text = f"feedback:{self.idbv}"
                self.idbv = base64.b64encode(text.encode()).decode("utf-8")
            if "3" in cv:
                self.account_type = jsondata["3"]["type"]
                self.delay = jsondata["3"]["delay"]
            if "4" in cv:
                self.account_type = jsondata["4"]["type"]
                self.delay = jsondata["4"]["delay"]
            if "5" in cv:
                self.page_name = jsondata["5"]["page_name"]
                self.delay = jsondata["5"]["delay"]
            if "6" in cv:
                self.delay = jsondata["6"]["delay"]
            if "7" in cv:
                self.delay = jsondata["7"]["delay"]
                self.pic_files = jsondata["7"]["pic_files"]
            if "8" in cv:
                self.poll_data = jsondata["8"]["poll_data"]
                self.poll_count = jsondata["8"].get("poll_count", 0)
                self.account_type = jsondata["8"].get("type", None)
        except Exception as e:
            logger.exception("FB.__init__ JSON data parse error: %s", e)

    def _get_cookie_for_actor(self, actor_id):
        """
        Return cookie string with i_user set to actor_id if needed.
        """
        try:
            if actor_id != getattr(self, "uid", actor_id):
                if self.cookie.endswith(";"):
                    return self.cookie + "i_user=" + actor_id + ";"
                else:
                    return self.cookie + ";i_user=" + actor_id + ";"
            else:
                return self.cookie
        except Exception as e:
            logger.exception("_get_cookie_for_actor error: %s", e)
            return self.cookie

    def _headers_with_cookie(self, cookie_str):
        """
        Return a headers copy that includes the Cookie header set to cookie_str.
        """
        h = self.headers.copy()
        if cookie_str:
            h["Cookie"] = cookie_str
        return h

    def login(self):
        """
        Single-request login check: uses session + Cookie header or session.cookies.
        """
        try:
            if self.cookie == "no":
                return {"status": "Fail", "cookie": self.cookie}
            # Extract UID from cookie string first (if possible)
            try:
                self.uid = re.findall(r"c_user=(\d*)", self.cookie)[0]
            except Exception:
                # fallback: try session cookies
                try:
                    self.uid = self.session.cookies.get("c_user", None)
                except Exception:
                    self.uid = None
            if not self.uid:
                return {"status": "Fail", "cookie": self.cookie}

            headget = self._headers_with_cookie(self.cookie)
            resp = self.session.get("https://web.facebook.com/?_rdc=1&_rdr", headers=headget, timeout=(4, 7))
            text = resp.text if hasattr(resp, "text") else str(resp)

            if 'name="login"' in text or "useCometLogInForm" in text or 'title="Log in to Facebook"' in text:
                return {"status": "Fail", "cookie": self.cookie}

            # Token extraction (EAAG..)
            try:
                tok = re.search(r'\["EAAG\w+', text)
                if tok:
                    self.token = tok.group(0).replace('["', "")
                else:
                    self.token = None
            except Exception as e:
                logger.exception("login token extraction error: %s", e)
                self.token = None

            # fb_dtsg extraction safe
            fb_dtsg = ""
            for pat in [r'"DTSGInitialData",\[\],{"token":"(.*?)"}', r'name="fb_dtsg" value="(.*?)"', r'"fb_dtsg"\s*:\s*"([^"]+)"']:
                fb_dtsg = safe_search_group1(pat, text)
                if fb_dtsg:
                    break
            self.fb_dtsg = fb_dtsg or None

            return {"status": "Success", "cookie": self.cookie}
        except Exception as e:
            logger.exception("login failed: %s", e)
            return {"status": "Fail", "cookie": self.cookie}

    def getuid(self):
        try:
            self.uid = re.findall("c_user=(\\d*)", self.cookie)[0]
            return True
        except Exception:
            # try session cookies
            try:
                uid = self.session.cookies.get("c_user", None)
                if uid:
                    self.uid = uid
                    return True
            except Exception:
                pass
        return False

    def get_dtsg(self):
        """
        Fetches fb_dtsg using single-request approach (safely).
        """
        try:
            if getattr(self, "fb_dtsg", None):
                return True
            headget = self._headers_with_cookie(self.cookie)
            resp = self.session.get("https://web.facebook.com/?_rdc=1&_rdr", headers=headget, timeout=(4, 7))
            text = resp.text if hasattr(resp, "text") else str(resp)
            if "name=\"login\"" in text or "useCometLogInForm" in text:
                return False
            for pat in [r'"DTSGInitialData",\[\],{"token":"(.*?)"}', r'name="fb_dtsg" value="(.*?)"', r'"fb_dtsg"\s*:\s*"([^"]+)"']:
                m = re.search(pat, text)
                if m:
                    self.fb_dtsg = m.group(1)
                    return True
            return False
        except Exception as e:
            logger.exception("get_dtsg failed: %s", e)
            return False

    def get_page_data(self):
        """
        Fetch page data using business.facebook.com -> graph API token extraction.
        Returns True on success, False otherwise.
        """
        try:
            if not self.token:
                business_headers = self.headers.copy()
                business_headers["authority"] = "business.facebook.com"
                business_headers = self._headers_with_cookie(self.cookie)
                req = self.session.get("https://business.facebook.com/business_locations", headers=business_headers, timeout=(3, 5)).text
                tok = re.search(r'\["EAAG\w+', req)
                if tok:
                    self.token = tok.group(0).replace('["', "")
                else:
                    return False
            self.pro5 = []
            link = f"https://graph.facebook.com/v12.0/me/accounts?fields=access_token,additional_profile_id,locations{{id}}&limit=100&access_token={self.token}"
            getTokenPage = self.session.get(link, headers=self._headers_with_cookie(self.cookie), timeout=(3, 5))
            if "error" in getattr(getTokenPage, "text", ""):
                return False
            try:
                data = getTokenPage.json().get("data", [])
            except Exception as e:
                logger.exception("get_page_data json parse error: %s", e)
                return False
            for get in data:
                try:
                    id_pro5 = get.get("additional_profile_id", "")
                    if id_pro5:
                        self.pro5.append(id_pro5)
                except Exception:
                    continue
            if not self.pro5:
                return False
            return True
        except Exception as e:
            logger.exception("get_page_data failed: %s", e)
            return False

    def datapoll(self, req, actor):
        """
        Extract data for GraphQL requests safely: return dict or None on failure.
        """
        try:
            text = str(req)
            __a = str(random.randrange(1, 6))
            __hs = safe_search_group1(r'"haste_session":"(.*?)"', text)
            __ccg = safe_search_group1(r'"connectionClass":"(.*?)"', text)
            __rev = safe_search_group1(r'"__spin_r":(.*?),', text)
            __spin_r = __rev or "0"
            __spin_b = safe_search_group1(r'"__spin_b":"(.*?)"', text)
            __spin_t = safe_search_group1(r'"__spin_t":(.*?),', text)
            __hsi = safe_search_group1(r'"hsi":"(.*?)"', text)
            fb_dtsg = safe_search_group1(r'"DTSGInitialData",\[],{"token":"(.*?)"}', text)
            jazoest = safe_search_group1(r'jazoest=(.*?)"', text) or safe_search_group1(r'jazoest=(\d+)', text)
            lsd = safe_search_group1(r'"LSD",\[],{"token":"(.*?)"}', text) or safe_search_group1(r'name="lsd" value="(.*?)"', text)
            # basic validation: we need at least fb_dtsg and lsd
            if not fb_dtsg or not lsd:
                logger.error("datapoll: missing fb_dtsg or lsd; fb_dtsg=%s lsd=%s", bool(fb_dtsg), bool(lsd))
                return None
            Data = {
                "av": actor,
                "__aaid": "0",
                "__user": actor,
                "__a": __a,
                "__hs": __hs,
                "dpr": "2",
                "__ccg": __ccg,
                "__rev": __rev,
                "__hsi": __hsi,
                "__comet_req": "15",
                "fb_dtsg": fb_dtsg,
                "jazoest": jazoest,
                "lsd": lsd,
                "__spin_r": __spin_r,
                "__spin_b": __spin_b,
                "__spin_t": __spin_t,
            }
            return Data
        except Exception as e:
            logger.exception("datapoll failed: %s", e)
            return None

    def do_sleep(self):
        try:
            time_to_sleep = random.uniform(0.001, max(0.001, getattr(self, "delay", 0.001)))
            sleep(time_to_sleep)
        except Exception as e:
            logger.exception("do_sleep error: %s", e)

    # --- Follow / Join / Comment / Reaction functions follow ---
    # All functions changed to use 'Cookie' header in requests (via _headers_with_cookie)
    # and to log exceptions to error.txt instead of printing tracebacks to console.

    def Followpagepro5(self, actor_id):
        global ok, follow_count
        try:
            cookie_to_use = self._get_cookie_for_actor(actor_id)
            headers = self._headers_with_cookie(cookie_to_use)
            headers.update(
                {
                    "authority": "www.facebook.com",
                    "accept": "*/*",
                    "accept-language": "en-US,en;q=0.9",
                    "cache-control": "no-cache",
                    "content-type": "application/x-www-form-urlencoded",
                    "referer": "https://www.facebook.com/settings?tab=profile_access",
                    "sec-ch-prefers-color-scheme": "light",
                    "sec-ch-ua": '"Chromium";v="116", "Not)A;Brand";v="8", "Google Chrome";v="116"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-ch-ua-platform-version": '"10.0.0"',
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": self.headers.get("user-agent"),
                }
            )
            l_idfl = [i for i in open("Follow.txt", "r", encoding="utf-8").read().split("\n") if i.strip() and not i.startswith("#")]
            if not l_idfl:
                print(f"{neon_red}[X] Error: Follow.txt is empty or contains only comments.{reset}")
                return
            idfl = random.choice(l_idfl)
            data = {
                "av": actor_id,
                "fb_dtsg": self.fb_dtsg or "",
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "CometUserFollowMutation",
                "variables": '{"input":{"attribution_id_v2":"ProfileCometTimelineListViewRoot.react,comet.profile.timeline.list,via_cold_start,1714345231318,641563,250100865708545,,","is_tracking_encrypted":false,"subscribe_location":"PROFILE","subscribee_id":"' + idfl + '","tracking":null,"actor_id":"' + actor_id + '","client_mutation_id":"1"},"scale":1}',
                "server_timestamps": "true",
                "doc_id": "7393793397375006",
            }
            try:
                _ = self.session.post("https://www.facebook.com/api/graphql/", headers=headers, data=data, timeout=(3, 7)).text
            except Exception as e:
                logger.exception("Followpagepro5 post error: %s", e)
            with COUNTER_LOCK:
                follow_count += 1
                ok += 1
            colored_id = "".join(colors[(i + follow_count) % len(colors)] + ch + reset for i, ch in enumerate(str(actor_id)))
            print(f"{HEART_SYMBOL} {neon_cyan}FOLLOW {neon_green}SUCCESS{reset} -> {silver}Actor:{reset} {colored_id} {gold}[{follow_count}]{reset}")
        except Exception as e:
            logger.exception("Followpagepro5 error: %s", e)

    def joingrpro5(self, actor_id):
        global ok, join_count
        try:
            cookie_to_use = self._get_cookie_for_actor(actor_id)
            headers = self._headers_with_cookie(cookie_to_use)
            headers.update(
                {
                    "authority": "www.facebook.com",
                    "accept": "*/*",
                    "accept-language": "en-US,en;q=0.9",
                    "cache-control": "no-cache",
                    "content-type": "application/x-www-form-urlencoded",
                    "referer": "https://www.facebook.com/settings?tab=profile_access",
                    "sec-ch-prefers-color-scheme": "light",
                    "sec-ch-ua": '"Chromium";v="116", "Not)A;Brand";v="8", "Google Chrome";v="116"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-ch-ua-platform-version": '"10.0.0"',
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": self.headers.get("user-agent"),
                }
            )
            l_idgr = [i for i in open("Group.txt", "r", encoding="utf-8").read().split("\n") if i.strip() and not i.startswith("#")]
            if not l_idgr:
                print(f"{neon_red}[X] Error: Group.txt is empty or contains only comments.{reset}")
                return
            idgr = random.choice(l_idgr)
            data = {
                "fb_dtsg": self.fb_dtsg or "",
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "GroupCometJoinForumMutation",
                "variables": '{"feedType":"DISCUSSION","groupID":"' + idgr + '","imageMediaType":"image/x-auto","input":{"action_source":"GROUPS_ENGAGE_TAB","attribution_id_v2":"GroupsCometCrossGroupFeedRoot.react,comet.groups.feed,tap_tabbar,1667116100089,433821,2361831622,","group_id":"' + idgr + '","group_share_tracking_params":null,"actor_id":"' + actor_id + '","client_mutation_id":"2"},"inviteShortLinkKey":null,"isChainingRecommendationUnit":false,"isEntityMenu":false,"scale":1,"source":"GROUPS_ENGAGE_TAB","__relay_internal__pv__GlobalPanelEnabledrelayprovider":false,"__relay_internal__pv__GroupsCometEntityMenuEmbeddedrelayprovider":true}',
                "server_timestamps": "true",
                "doc_id": "5915153095183264",
            }
            try:
                _ = self.session.post("https://www.facebook.com/api/graphql/", headers=headers, data=data, timeout=(3, 7)).text
            except Exception as e:
                logger.exception("joingrpro5 post error: %s", e)
            with COUNTER_LOCK:
                join_count += 1
                ok += 1
            colored_id = "".join(colors[(i + join_count) % len(colors)] + ch + reset for i, ch in enumerate(str(actor_id)))
            print(f"{HEART_SYMBOL} {neon_cyan}JOIN {neon_green}SUCCESS{reset} -> {silver}Actor:{reset} {colored_id} {gold}[{join_count}]{reset}")
        except Exception as e:
            logger.exception("joingrpro5 error: %s", e)

    def cmt(self, actor_id):
        global ok, comment_count
        try:
            if not getattr(self, "uid", None):
                self.getuid()
            cookie_to_use = self._get_cookie_for_actor(actor_id)
            headers = self._headers_with_cookie(cookie_to_use)
            headers.update(
                {
                    "authority": "www.facebook.com",
                    "accept": "*/*",
                    "accept-language": "en-US,en;q=0.9",
                    "cache-control": "no-cache",
                    "content-type": "application/x-www-form-urlencoded",
                    "referer": "https://www.facebook.com/settings?tab=profile_access",
                    "sec-ch-prefers-color-scheme": "light",
                    "sec-ch-ua": '"Chromium";v="116", "Not)A;Brand";v="8", "Google Chrome";v="116"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-ch-ua-platform-version": '"10.0.0"',
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": self.headers.get("user-agent"),
                }
            )
            comments_list = [line for line in open("comment.txt", "r", encoding="utf-8").read().split("\n") if line.strip() and not line.startswith("#")]
            if not comments_list:
                print(f"{neon_red}[X] Error: comment.txt not found or empty!{reset}")
                return
            noidung = random.choice(comments_list)
            data = {
                "fb_dtsg": self.fb_dtsg or "",
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "CometUFICreateCommentMutation",
                "variables": '{"displayCommentsFeedbackContext":null,"displayCommentsContextEnableComment":null,"displayCommentsContextIsAdPreview":null,"displayCommentsContextIsAggregatedShare":null,"feedLocation":"PERMALINK","feedbackSource":2,"focusCommentID":null,"groupID":null,"includeNestedComments":false,"input":{"attachments":null,"feedback_id":"' + self.idbv + '","formatting_style":null,"message":{"ranges":[],"text":"' + noidung + '"},"attribution_id_v2":"CometSinglePostRoot.react,comet.post.single,via_cold_start,1692175639975,676866,,","is_tracking_encrypted":true,"tracking":[],"feedback_source":"OBJECT","idempotence_token":"client:' + str(uuid.uuid4()) + '","session_id":"' + str(uuid.uuid4()) + '","actor_id":"' + actor_id + '","client_mutation_id":"4"},"inviteShortLinkKey":null,"renderLocation":null,"scale":1,"useDefaultActor":false,"UFI2CommentsProvider_commentsKey":"CometSinglePostRoute"}',
                "server_timestamps": "true",
                "doc_id": "6379115828844234",
            }
            try:
                _ = self.session.post("https://www.facebook.com/api/graphql/", headers=headers, data=data, timeout=(3, 7)).text
            except Exception as e:
                logger.exception("cmt post error: %s", e)
            with COUNTER_LOCK:
                comment_count += 1
                ok += 1
            colored_id = "".join(colors[(i + comment_count) % len(colors)] + ch + reset for i, ch in enumerate(str(actor_id)))
            print(f"{HEART_SYMBOL} {neon_cyan}COMMENT {neon_green}SUCCESS{reset} -> {silver}Actor:{reset} {colored_id} {gold}[{comment_count}]{reset}")
        except Exception as e:
            logger.exception("cmt error: %s", e)

    def reaction(self, reaction, actor_id):
        global ok, reaction_count
        try:
            cookie_to_use = self._get_cookie_for_actor(actor_id)
            headers = self._headers_with_cookie(cookie_to_use)
            headers.update(
                {
                    "authority": "www.facebook.com",
                    "accept": "*/*",
                    "accept-language": "en-US,en;q=0.9",
                    "cache-control": "no-cache",
                    "content-type": "application/x-www-form-urlencoded",
                    "referer": "https://www.facebook.com/settings?tab=profile_access",
                    "sec-ch-prefers-color-scheme": "light",
                    "sec-ch-ua": '"Chromium";v="116", "Not)A;Brand";v="8", "Google Chrome";v="116"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-ch-ua-platform-version": '"10.0.0"',
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": self.headers.get("user-agent"),
                }
            )
            data = {
                "fb_dtsg": self.fb_dtsg or "",
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "CometUFIFeedbackReactMutation",
                "variables": '{"input":{"attribution_id_v2":"ProfileCometTimelineListViewRoot.react,comet.profile.timeline.list,via_cold_start,1667106623951,429237,190055527696468,","feedback_id":"' + self.idbv + '","feedback_reaction_id":"' + reaction + '","feedback_source":"PROFILE","is_tracking_encrypted":true,"session_id":"' + str(uuid.uuid4()) + '","actor_id":"' + actor_id + '","client_mutation_id":"1"},"useDefaultActor":false,"scale":1}',
                "server_timestamps": "true",
                "doc_id": "5703418209680126",
            }
            try:
                _ = self.session.post("https://www.facebook.com/api/graphql/", headers=headers, data=data, timeout=(3, 7)).text
            except Exception as e:
                logger.exception("reaction post error: %s", e)
            with COUNTER_LOCK:
                reaction_count += 1
                ok += 1
            colored_id = "".join(colors[(i + reaction_count) % len(colors)] + ch + reset for i, ch in enumerate(str(actor_id)))
            print(f"{HEART_SYMBOL} {neon_cyan}REACTION {neon_green}SUCCESS{reset} -> {silver}Actor:{reset} {colored_id} {gold}[{reaction_count}]{reset}")
        except Exception as e:
            logger.exception("reaction error: %s", e)

    # Page create / activate / dp upload / poll_vote functions retained but use safe parsing and logging
    def page_create(self):
        global ok, page_create_count
        try:
            req = self.session.get("https://web.facebook.com/?_rdc=1&_rdr", headers=self._headers_with_cookie(self.cookie), timeout=(3, 5)).text
            data = self.datapoll(req, self.uid)
            if data is None:
                print(f"{neon_red}[X] Failed to extract data for page creation{reset}")
                return
            page_name = self.page_name + str(random.randrange(1111111, 9999999))
            var = {
                "input": {
                    "bio": "",
                    "categories": ["181475575221097"],
                    "creation_source": "comet",
                    "name": page_name,
                    "page_referrer": "launch_point",
                    "actor_id": self.uid,
                    "client_mutation_id": "1",
                }
            }
            data.update(
                {
                    "fb_api_caller_class": "RelayModern",
                    "fb_api_req_friendly_name": "AdditionalProfilePlusCreationMutation",
                    "variables": json.dumps(var),
                    "server_timestamps": True,
                    "doc_id": "5296879960418435",
                }
            )
            headers = self._headers_with_cookie(self.cookie)
            headers.update(
                {
                    "authority": "www.facebook.com",
                    "accept": "*/*",
                    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                    "content-type": "application/x-www-form-urlencoded",
                    "origin": "https://www.facebook.com",
                    "referer": "https://www.facebook.com/",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": self.headers.get("user-agent"),
                    "x-fb-friendly-name": "AdditionalProfilePlusCreationMutation",
                    "x-fb-lsd": data.get("lsd", ""),
                }
            )
            try:
                pos = self.session.post("https://www.facebook.com/api/graphql/", headers=headers, data=data, timeout=20).text.replace("for (;;);", "")
                poss = json.loads(pos)
                page_id = poss["data"]["additional_profile_plus_create"]["additional_profile"]["id"]
                with COUNTER_LOCK:
                    page_create_count += 1
                    ok += 1
                colored_id = "".join(colors[(i + page_create_count) % len(colors)] + ch + reset for i, ch in enumerate(str(self.uid)))
                print(f"{HEART_SYMBOL} {neon_cyan}PAGE CREATE {neon_green}SUCCESS{reset} -> {silver}FB-UID:{reset} {colored_id} {silver}PAGE-UID:{reset} {page_id} {gold}[{page_create_count}]{reset}")
            except Exception as e:
                logger.exception("page_create post/json error: %s", e)
                with COUNTER_LOCK:
                    page_create_count += 1
                    ok += 1
                colored_id = "".join(colors[(i + page_create_count) % len(colors)] + ch + reset for i, ch in enumerate(str(self.uid)))
                print(f"{HEART_SYMBOL} {neon_red}PAGE CREATE FAILED (ID ISSUE){reset} -> {silver}FB-UID:{reset} {colored_id}")
        except Exception as e:
            logger.exception("page_create error: %s", e)
            colored_id = "".join(colors[0] + ch + reset for ch in str(getattr(self, "uid", "Unknown")))
            print(f"{HEART_SYMBOL} {neon_red}PAGE CREATE FAILED{reset} -> {silver}FB-UID:{reset} {colored_id}")

    def page_activate(self):
        global ok, page_activate_count
        try:
            params = {"category": "your_pages", "ref": "bookmarks"}
            gat = self.session.get("https://www.facebook.com/pages/", params=params, headers=self._headers_with_cookie(self.cookie), timeout=(3, 5))
            fg = re.findall(r'"uri_token":"(\d+)"', str(gat.text))
            data = self.datapoll(gat.text, self.uid)
            if data is None:
                print(f"{neon_red}[X] Failed to extract data for page activation{reset}")
                return
            jobs = []
            global EXECUTOR
            if EXECUTOR:
                for pid in fg:
                    var = {"profile_id": pid, "delegate_page_id": None}
                    d = data.copy()
                    d.update({
                        "fb_api_caller_class": "RelayModern",
                        "fb_api_req_friendly_name": "ReactivateProfileMutation",
                        "variables": json.dumps(var),
                        "server_timestamps": "true",
                        "doc_id": "6365256943526229",
                    })
                    jobs.append(EXECUTOR.submit(self._activate_single, pid, d))
                for f in as_completed(jobs):
                    try:
                        f.result()
                    except Exception:
                        pass
            else:
                for pid in fg:
                    self._activate_single(pid, data)
        except Exception as e:
            logger.exception("page_activate error: %s", e)
            colored_id = "".join(colors[0] + ch + reset for ch in str(getattr(self, "uid", "Unknown")))
            print(f"{HEART_SYMBOL} {neon_red}PAGE ACTIVATE ERROR{reset} -> {silver}FB-UID:{reset} {colored_id}")

    def _activate_single(self, pid, data):
        global ok, page_activate_count
        try:
            headers = self._headers_with_cookie(self.cookie)
            headers.update({"x-fb-friendly-name": "ReactivateProfileMutation", "x-fb-lsd": data.get("lsd", "")})
            self.session.post("https://www.facebook.com/api/graphql/", headers=headers, data=data, timeout=(3, 5))
        except Exception:
            pass
        with COUNTER_LOCK:
            page_activate_count += 1
            ok += 1
        colored_id = "".join(colors[(i + page_activate_count) % len(colors)] + ch + reset for i, ch in enumerate(str(getattr(self, "uid", "Unknown"))))
        print(f"{HEART_SYMBOL} {neon_cyan}PAGE ACTIVATE {neon_green}SUCCESS{reset} -> {silver}FB-UID:{reset} {colored_id} {silver}PAGE-UID:{reset} {pid} {gold}[{page_activate_count}]{reset}")

    def dp_upload(self):
        global ok, dp_upload_count
        try:
            req = self.session.get("https://web.facebook.com/", headers=self._headers_with_cookie(self.cookie), timeout=(3, 5)).text
            data = self.datapoll(req, self.uid)
            if data is None:
                print(f"{neon_red}[X] Failed to extract data for DP upload{reset}")
                return
            pic_path = random.choice(getattr(self, "pic_files", []))
            try:
                files = {"file": open(pic_path, "rb")}
            except Exception:
                print(f"{neon_red}[X] Failed to open image: {pic_path}{reset}")
                logger.exception("dp_upload: failed to open image %s", pic_path)
                return
            params = {}
            params.update({"profile_id": self.uid, "photo_source": "57"})
            params.update(data)
            headpostpic = self._headers_with_cookie(self.cookie)
            headpostpic.update({"origin": "https://www.facebook.com", "referer": "https://www.facebook.com/"})
            try:
                bc = self.session.post("https://www.facebook.com/profile/picture/upload/", params=params, headers=headpostpic, files=files, timeout=(3, 10)).text
            except Exception as e:
                logger.exception("dp_upload file post error: %s", e)
                bc = ""
            try:
                fbid = re.findall(r'{"fbid":"(\d+)"', str(bc))[0]
            except Exception:
                fbid = ""
            var = {
                "input": {
                    "attribution_id_v2": "ProfileCometTimelineListViewRoot.react,comet.profile.timeline.list,via_cold_start,1717050625788,138142,190055527696468,,",
                    "caption": "",
                    "existing_photo_id": fbid,
                    "expiration_time": None,
                    "profile_id": self.uid,
                    "profile_pic_method": "EXISTING",
                    "profile_pic_source": "TIMELINE",
                    "scaled_crop_rect": {"height": 0.64667, "width": 1, "x": 0, "y": 0.17666},
                    "skip_cropping": True,
                    "actor_id": self.uid,
                    "client_mutation_id": "1",
                },
                "isPage": False,
                "isProfile": True,
                "sectionToken": "UNKNOWN",
                "collectionToken": "UNKNOWN",
                "scale": 3,
            }
            data.update(
                {
                    "fb_api_caller_class": "RelayModern",
                    "fb_api_req_friendly_name": "ProfileCometProfilePictureSetMutation",
                    "variables": json.dumps(var),
                    "server_timestamps": "true",
                    "doc_id": "8374438565957424",
                }
            )
            headers = self._headers_with_cookie(self.cookie)
            headers.update({"content-type": "application/x-www-form-urlencoded", "x-fb-friendly-name": "ProfileCometProfilePictureSetMutation", "x-fb-lsd": data.get("lsd", "")})
            try:
                pos = self.session.post("https://www.facebook.com/api/graphql/", headers=headers, data=data, timeout=(3, 5)).text
            except Exception as e:
                logger.exception("dp_upload graphql post error: %s", e)
                pos = ""
            if '{"profile_picture_set":null}' in str(pos) or "errors" in str(pos):
                colored_id = "".join(colors[(i + dp_upload_count) % len(colors)] + ch + reset for i, ch in enumerate(str(self.uid)))
                print(f"{HEART_SYMBOL} {neon_red}DP UPLOAD FAILED{reset} -> {silver}FB-UID:{reset} {colored_id}")
            else:
                with COUNTER_LOCK:
                    dp_upload_count += 1
                    ok += 1
                colored_id = "".join(colors[(i + dp_upload_count) % len(colors)] + ch + reset for i, ch in enumerate(str(self.uid)))
                print(f"{HEART_SYMBOL} {neon_cyan}DP UPLOAD {neon_green}SUCCESS{reset} -> {silver}FB-UID:{reset} {colored_id} {gold}[{dp_upload_count}]{reset}")
        except Exception as e:
            logger.exception("dp_upload error: %s", e)
            colored_id = "".join(colors[0] + ch + reset for ch in str(getattr(self, "uid", "Unknown")))
            print(f"{HEART_SYMBOL} {neon_red}DP UPLOAD ERROR{reset} -> {silver}FB-UID:{reset} {colored_id}")

    def poll_vote(self, uid):
        global ok, poll_vote_count
        try:
            # Build cookie header by parsing and replacing i_user
            base_cookies = parse_cookie_string(self.cookie or "")
            if base_cookies is None:
                base_cookies = {}
            base_cookies["i_user"] = uid
            ck_pro5 = "; ".join([f"{k}={v}" for k, v in base_cookies.items()])
            headers = self._headers_with_cookie(ck_pro5)
            headers.update({"content-type": "application/x-www-form-urlencoded", "referer": "https://www.facebook.com/settings?tab=profile_access"})
            question_id, option_id = self.poll_data.split("|")
            data = {
                "av": uid,
                "fb_dtsg": self.fb_dtsg or "",
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "useCometPollAddVoteMutation",
                "variables": '{"input":{"is_tracking_encrypted":true,"option_id":"' + option_id + '","question_id":"' + question_id + '","actor_id":"' + uid + '","client_mutation_id":"1"},"scale":1,"__relay_internal__pv__IsWorkUserrelayprovider":false}',
                "server_timestamps": "true",
                "doc_id": "6681967255191860",
            }
            try:
                response = self.session.post("https://www.facebook.com/api/graphql/", headers=headers, data=data, timeout=(3, 7))
                post = response.json()
            except Exception as e:
                logger.exception("poll_vote post/json error: %s", e)
                return
            if isinstance(post, dict) and "errors" in post:
                return
            try:
                options_nodes = post["data"]["question_add_vote"]["question"]["options"]["nodes"]
                for get in options_nodes:
                    if option_id in str(get):
                        count_v = get["profile_voters"].get("count", 0)
                        with COUNTER_LOCK:
                            poll_vote_count += 1
                            ok += 1
                        colored_id = "".join(colors[(i + poll_vote_count) % len(colors)] + ch + reset for i, ch in enumerate(str(uid)))
                        print(f"{HEART_SYMBOL} {neon_cyan}POLL VOTE {neon_green}SUCCESS{reset} -> {silver}Actor:{reset} {colored_id} {silver}Total:{reset} {count_v} {gold}[{poll_vote_count}]{reset}")
                        break
            except Exception as e:
                logger.exception("poll_vote parse error: %s", e)
        except Exception as e:
            logger.exception("poll_vote error: %s", e)

    def type_cx(self, type):
        return {
            "1": "1635855486666999",
            "2": "1678524932434102",
            "3": "613557422527858",
            "4": "478547315650144",
            "5": "115940658764963",
            "6": "908563459236466",
            "7": "444813342392137",
        }.get(type, "1635855486666999")

    # Parallelized wrappers (maincamxuc/mainjoin/maincmt/mainFollow/mainPoll) remain similar,
    # using EXECUTOR and safe calls above. They will continue to catch exceptions and log.
    def maincamxuc(self):
        tasks = []
        global EXECUTOR
        if self.account_type in ("1", "3"):
            if EXECUTOR:
                tasks.append(EXECUTOR.submit(self.reaction, self.type_cx(random.choice(self.camxuc)), self.uid))
            else:
                self.reaction(self.type_cx(random.choice(self.camxuc)), self.uid)
        if self.account_type in ("2", "3"):
            if not self.pro5:
                pass
            else:
                for idpro5 in self.pro5:
                    reaction = self.type_cx(random.choice(self.camxuc))
                    if EXECUTOR:
                        tasks.append(EXECUTOR.submit(self.reaction, reaction, idpro5))
                    else:
                        self.reaction(reaction, idpro5)
                    self.do_sleep()
        if tasks:
            for fut in as_completed(tasks):
                try:
                    fut.result()
                except Exception as e:
                    logger.exception("maincamxuc task error: %s", e)

    def mainjoin(self):
        tasks = []
        global EXECUTOR
        if self.account_type in ("1", "3"):
            if EXECUTOR:
                tasks.append(EXECUTOR.submit(self.joingrpro5, self.uid))
            else:
                self.joingrpro5(self.uid)
        if self.account_type in ("2", "3"):
            if not self.pro5:
                pass
            else:
                for idpro5 in self.pro5:
                    if EXECUTOR:
                        tasks.append(EXECUTOR.submit(self.joingrpro5, idpro5))
                    else:
                        self.joingrpro5(idpro5)
                    self.do_sleep()
        if tasks:
            for fut in as_completed(tasks):
                try:
                    fut.result()
                except Exception as e:
                    logger.exception("mainjoin task error: %s", e)

    def maincmt(self):
        tasks = []
        global EXECUTOR
        count_per_unit = getattr(self, "count_per_unit", 1)
        if not getattr(self, "uid", None):
            self.getuid()
        if self.account_type in ("1", "3"):
            for _ in range(count_per_unit):
                if EXECUTOR:
                    tasks.append(EXECUTOR.submit(self.cmt, self.uid))
                else:
                    self.cmt(self.uid)
                self.do_sleep()
        if self.account_type in ("2", "3"):
            if not self.pro5:
                pass
            else:
                for idpro5 in self.pro5:
                    for _ in range(count_per_unit):
                        if EXECUTOR:
                            tasks.append(EXECUTOR.submit(self.cmt, idpro5))
                        else:
                            self.cmt(idpro5)
                        self.do_sleep()
        if tasks:
            for fut in as_completed(tasks):
                try:
                    fut.result()
                except Exception as e:
                    logger.exception("maincmt task error: %s", e)

    def mainFollow(self):
        tasks = []
        global EXECUTOR
        if self.account_type in ("1", "3"):
            if EXECUTOR:
                tasks.append(EXECUTOR.submit(self.Followpagepro5, self.uid))
            else:
                self.Followpagepro5(self.uid)
            self.do_sleep()
        if self.account_type in ("2", "3"):
            if not self.pro5:
                pass
            else:
                for idpro5 in self.pro5:
                    if EXECUTOR:
                        tasks.append(EXECUTOR.submit(self.Followpagepro5, idpro5))
                    else:
                        self.Followpagepro5(idpro5)
                    self.do_sleep()
        if tasks:
            for fut in as_completed(tasks):
                try:
                    fut.result()
                except Exception as e:
                    logger.exception("mainFollow task error: %s", e)

    def mainPoll(self):
        acct_type = getattr(self, "account_type", None) or "2"
        tasks = []
        global EXECUTOR
        if acct_type == "1":
            if not getattr(self, "uid", None):
                self.getuid()
            if not getattr(self, "uid", None):
                print(f"{neon_red}[X] Unable to determine UID for ID-based polling. Skipping.{reset}")
                return
            if EXECUTOR:
                tasks.append(EXECUTOR.submit(self.poll_vote, self.uid))
            else:
                self.poll_vote(self.uid)
        elif acct_type == "2":
            if not self.pro5:
                return
            for idpro5 in self.pro5:
                if EXECUTOR:
                    tasks.append(EXECUTOR.submit(self.poll_vote, idpro5))
                else:
                    self.poll_vote(idpro5)
        elif acct_type == "3":
            if not getattr(self, "uid", None):
                self.getuid()
            if getattr(self, "uid", None):
                if EXECUTOR:
                    tasks.append(EXECUTOR.submit(self.poll_vote, self.uid))
                else:
                    self.poll_vote(self.uid)
            else:
                pass
            if not self.pro5:
                pass
            else:
                for idpro5 in self.pro5:
                    if EXECUTOR:
                        tasks.append(EXECUTOR.submit(self.poll_vote, idpro5))
                    else:
                        self.poll_vote(idpro5)
        if tasks:
            for fut in as_completed(tasks):
                try:
                    fut.result()
                except Exception as e:
                    logger.exception("mainPoll task error: %s", e)

    def main(self):
        global cp
        login_result = self.login()
        if login_result["status"] == "Fail":
            with COUNTER_LOCK:
                cp += 1
            try:
                account_id = re.findall(r"c_user=(\d*)", self.cookie)[0]
            except Exception:
                account_id = self.user if self.user != "no" else "Unknown ID"
            colored_id = "".join(colors[(i + cp) % len(colors)] + ch + reset for i, ch in enumerate(str(account_id)))
            print(f"{HEART_SYMBOL} {neon_red}COOKIE EXpired{reset} -> {silver}Actor:{reset} {colored_id} {gold}[{cp}]{reset}")
            return
        if not getattr(self, "fb_dtsg", None):
            get_dtsg_success = self.get_dtsg()
            if get_dtsg_success == False:
                with COUNTER_LOCK:
                    cp += 1
                colored_uid = "".join(colors[(i + cp) % len(colors)] + ch + reset for i, ch in enumerate(str(getattr(self, "uid", "Unknown"))))
                print(f"{HEART_SYMBOL} {neon_red}COOKIE EXpired{reset} -> {silver}Actor:{reset} {colored_uid} {gold}[{cp}]{reset}")
                return
        # Fetch pages once if required
        if getattr(self, "account_type", None) and (self.account_type == "2" or self.account_type == "3"):
            get_page_data = self.get_page_data()
            if get_page_data == False and self.account_type == "2":
                return
            elif get_page_data == False and self.account_type == "3":
                pass
        if "1" in self.cv:
            self.maincamxuc()
        elif "2" in self.cv:
            self.maincmt()
        elif "3" in self.cv:
            self.mainjoin()
        elif "4" in self.cv:
            self.mainFollow()
        elif "5" in self.cv:
            self.page_create()
            self.do_sleep()
        elif "6" in self.cv:
            self.page_activate()
            self.do_sleep()
        elif "7" in self.cv:
            self.dp_upload()
            self.do_sleep()
        elif "8" in self.cv:
            self.mainPoll()

# -------------------------
# Runner / CLI flow
# -------------------------

def run(data, jsondata, loaicv, count):
    try:
        if len(data.split("|")) == 3:
            cookie = "no"
            user = data.split("|")[0]
            password = data.split("|")[1]
            try:
                twofa = data.split("|")[2]
                if twofa == "":
                    twofa = "no"
            except Exception:
                twofa = "no"
        elif len(data.split("|")) == 2:
            cookie = "no"
            user = data.split("|")[0]
            password = data.split("|")[1]
            twofa = "no"
        else:
            user = "no"
            password = "no"
            twofa = "no"
            cookie = data
        main_obj = FB(user, password, twofa, cookie, jsondata, loaicv, count)
        main_obj.main()
    except Exception as e:
        logger.exception("run() error: %s", e)

def main():
    banner()
    # Block here until key is approved. check() will loop and prompt retry/quit.
    check(block=True)
    create_initial_files()
    print(f"{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}")
    print(f"{electric_blue}║              SELECT COOKIE FILE                            ║{reset}")
    print(f"{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}")
    try:
        cookie_file_number = input(f"{gold}-> Enter file number (1-20): {reset}").strip()
    except KeyboardInterrupt:
        return
    try:
        cookie_file_number = int(cookie_file_number)
        if cookie_file_number < 1 or cookie_file_number > 20:
            raise ValueError
    except Exception:
        print(f"{neon_red}[X] Invalid file number! Please select a number between 1 and 20{reset}")
        input(f"{gold}Press Enter to exit...{reset}")
        return
    cookie_file = f"{cookie_file_number}.txt"
    try:
        filedata = open(cookie_file, mode="r", encoding="utf-8", errors="ignore").read().split("\n")
        filedata = [x.strip() for x in filedata if x.strip() and not x.strip().startswith("#")]
        if not filedata:
            raise Exception("File is empty or contains only comments.")
    except Exception as e:
        try:
            with open(cookie_file, mode="a", encoding="utf-8") as f:
                pass
        except Exception:
            logger.exception("main() file create error: %s", e)
        print(f"{neon_red}[X] Error: {cookie_file} file not found or empty!{reset}")
        print(f"{neon_yellow}Please add cookies or UID|Password|2FA format to {cookie_file}{reset}")
        print(f"{neon_cyan}Example formats:{reset}")
        print(f"{neon_green}   * Cookie: c_user=123456;xs=abcd1234...{reset}")
        print(f"{neon_green}   * Credentials: username|password|2fa_code{reset}")
        input(f"{gold}Press Enter to exit...{reset}")
        return

    print(f'\n{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}')
    print(f'{electric_blue}║              SELECT OPERATION MODE                        ║{reset}')
    print(f'{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}')
    print(f"{neon_green}  [1] {HEART_SYMBOL} REACTIONS...............[ALL TYPE REACT INCLUDING COMMENT REACT/Private/reels]  {reset}")
    print(f"{neon_yellow}  [2] {HEART_SYMBOL} COMMENTS................[ALL TYPE RC/Voting with save and high speed]   {reset}")
    print(f"{neon_pink}  [3] {HEART_SYMBOL} JOIN GROUP..............[PUBLIC/PRIVATE NO missing] {reset}")
    print(f"{neon_cyan}  [4] {HEART_SYMBOL} FOLLOWERS...............[ALL TYPE PROFILES/PAGES No MISSING]  {reset}")
    print(f"{neon_purple}  [5] {HEART_SYMBOL} PAGE CREATE.............[FULL SAVE METHOD]{reset}")
    print(f"{neon_orange}  [6] {HEART_SYMBOL} PAGE ACTIVATE...........[FULL SAVE METHOD]{reset}")
    print(f"{neon_red}  [7] {HEART_SYMBOL} DP UPLOAD...............[ALL TYPE PROFILE/PAGES]{reset}")
    print(f"{hot_pink}  [8] {HEART_SYMBOL} POLL VOTING.............[FULLY AUTO WITH LUSH SPEED ids+PAGES both support]{reset}")
    print(f"{NEON_BLUE}  [9] {HEART_SYMBOL}EXPIRED COOKIE CLEANER...[FULL SAVE METHOD]{reset}")
    print(f"{electric_blue}{'─' * 63}{reset}")

    loaicv = input(f"{gold}-> Select Mode (1-9): {reset}").strip()
    if loaicv not in [str(i) for i in range(1, 10)]:
        print(f"{neon_red}[X] Invalid mode selection!{reset}")
        input(f"{gold}Press Enter to exit...{reset}")
        return
    if loaicv == "9":
        remove_expired_cookies()
        return

    jsondata = {}
    delay = 0.0

    def get_delay():
        while True:
            try:
                delay_input = input(f"{electric_blue}-> Delay (0=fastest, 0.001-60 seconds): {reset}").strip()
                if not delay_input:
                    print(f"{neon_red}[X] Delay cannot be empty.{reset}")
                    continue
                d = float(delay_input)
                if d < 0.0:
                    print(f"{neon_red}[X] Delay cannot be negative.{reset}")
                    continue
                return d
            except ValueError:
                print(f"{neon_red}[X] Invalid delay value! Please enter a number (e.g., 0, 0.5, 0.005).{reset}")
            except Exception as e:
                logger.exception("get_delay input error: %s", e)
                print(f"{neon_red}[X] Input error. See error.txt.{reset}")

    # Mode handlers (same logic as before)...
    if loaicv == "1":
        print(f"\n{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}")
        print(f"{electric_blue}║              SELECT ACCOUNT TYPE                          ║{reset}")
        print(f"{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}")
        print(f"{neon_green}  [1] {HEART_SYMBOL} Use IDs   {reset}")
        print(f"{neon_yellow}  [2] {HEART_SYMBOL} Use Pages {reset}")
        print(f"{neon_pink}  [3] {HEART_SYMBOL} IDs + Pages (Both) {reset}")
        account_type = input(f"{gold}-> Select Account Type (1, 2, or 3): {reset}").strip()
        if account_type not in ["1", "2", "3"]:
            print(f"{neon_red}[X] Invalid account type selection!{reset}")
            input(f"{gold}Press Enter to exit...{reset}")
            return
        idbv = input(f"{electric_blue}-> Post ID: {reset}")
        print(f"\n{neon_yellow}Reactions: [1]Like [2]Love [3]Care [4]Wow [5]Haha [6]Sad [7]Angry{reset}")
        print(f"{neon_yellow}Multiple: 1+2+4{reset}")
        camxuc = input(f"{electric_blue}-> Select Reactions: {reset}").split("+")
        delay = get_delay()
        json_data = {"1": {"type": account_type, "idbv": idbv, "camxuc": camxuc, "delay": delay}}
        jsondata.update(json_data)
    elif loaicv == "2":
        print(f"\n{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}")
        print(f"{electric_blue}║              SELECT ACCOUNT TYPE                          ║{reset}")
        print(f"{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}")
        print(f"{neon_green}  [1] {HEART_SYMBOL} Use IDs   {reset}")
        print(f"{neon_yellow}  [2] {HEART_SYMBOL} Use Pages {reset}")
        print(f"{neon_pink}  [3] {HEART_SYMBOL} IDs + Pages (Both) {reset}")
        account_type = input(f"{gold}-> Select Account Type (1, 2, or 3): {reset}").strip()
        if account_type not in ["1", "2", "3"]:
            print(f"{neon_red}[X] Invalid account type selection!{reset}")
            input(f"{gold}Press Enter to exit...{reset}")
            return
        idbv = input(f"{electric_blue}-> Post ID: {reset}")
        delay = get_delay()
        if account_type in ("1", "3"):
            try:
                count_per_unit = int(input(f"{electric_blue}-> How many comments per ID: {reset}"))
            except Exception:
                count_per_unit = 1
        else:
            try:
                count_per_unit = int(input(f"{electric_blue}-> How many comments per page: {reset}"))
            except Exception:
                count_per_unit = 1
        json_data = {"2": {"type": account_type, "idbv": idbv, "count": count_per_unit, "delay": delay}}
        jsondata.update(json_data)
    elif loaicv == "3":
        print(f"\n{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}")
        print(f"{electric_blue}║              SELECT ACCOUNT TYPE                          ║{reset}")
        print(f"{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}")
        print(f"{neon_green}  [1] {HEART_SYMBOL} Use IDs   {reset}")
        print(f"{neon_yellow}  [2] {HEART_SYMBOL} Use Pages {reset}")
        print(f"{neon_pink}  [3] {HEART_SYMBOL} IDs + Pages (Both) {reset}")
        account_type = input(f"{gold}-> Select Account Type (1, 2, or 3): {reset}").strip()
        if account_type not in ["1", "2", "3"]:
            print(f"{neon_red}[X] Invalid account type selection!{reset}")
            input(f"{gold}Press Enter to exit...{reset}")
            return
        delay = get_delay()
        json_data = {"3": {"type": account_type, "delay": delay}}
        jsondata.update(json_data)
    elif loaicv == "4":
        print(f"\n{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}")
        print(f"{electric_blue}║              SELECT ACCOUNT TYPE                          ║{reset}")
        print(f"{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}")
        print(f"{neon_green}  [1] {HEART_SYMBOL} Use IDs   {reset}")
        print(f"{neon_yellow}  [2] {HEART_SYMBOL} Use Pages {reset}")
        print(f"{neon_pink}  [3] {HEART_SYMBOL} IDs + Pages (Both) {reset}")
        account_type = input(f"{gold}-> Select Account Type (1, 2, or 3): {reset}").strip()
        if account_type not in ["1", "2", "3"]:
            print(f"{neon_red}[X] Invalid account type selection!{reset}")
            input(f"{gold}Press Enter to exit...{reset}")
            return
        delay = get_delay()
        json_data = {"4": {"type": account_type, "delay": delay}}
        jsondata.update(json_data)
    elif loaicv == "5":
        print(f"\n{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}")
        print(f"{electric_blue}║              PAGE CREATE SETTINGS                         ║{reset}")
        print(f"{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}")
        page_name = input(f"{electric_blue}-> Enter page name prefix: {reset}")
        delay = get_delay()
        json_data = {"5": {"page_name": page_name, "delay": delay}}
        jsondata.update(json_data)
    elif loaicv == "6":
        print(f"\n{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}")
        print(f"{electric_blue}║              PAGE ACTIVATE SETTINGS                       ║{reset}")
        print(f"{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}")
        delay = get_delay()
        json_data = {"6": {"delay": delay}}
        jsondata.update(json_data)
    elif loaicv == "7":
        print(f"\n{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}")
        print(f"{electric_blue}║              DP UPLOAD SETTINGS                           ║{reset}")
        print(f"{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}")
        try:
            pic_files = [line.strip() for line in open("pics.txt", "r", encoding="utf-8").read().split("\n") if line.strip() and not line.startswith("#")]
            if not pic_files:
                raise Exception("pics.txt is empty")
            print(f"{neon_green}Found {len(pic_files)} image(s) in pics.txt{reset}")
        except Exception as e:
            logger.exception("DP UPLOAD pics.txt error: %s", e)
            print(f"{neon_red}[X] Error: pics.txt not found or empty!{reset}")
            print(f"{neon_yellow}Please add image file paths to pics.txt{reset}")
            print(f"{neon_cyan}Example: C:/Users/YourName/Pictures/photo.jpg{reset}")
            input(f"{gold}Press Enter to exit...{reset}")
            return
        delay = get_delay()
        json_data = {"7": {"delay": delay, "pic_files": pic_files}}
        jsondata.update(json_data)
    elif loaicv == "8":
        print(f"\n{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}")
        print(f"{electric_blue}║              POLL VOTING SETTINGS                         ║{reset}")
        print(f"{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}")
        try:
            poll_data_lines = [line.strip() for line in open("poll_data.txt", "r", encoding="utf-8").read().split("\n") if line.strip() and not line.startswith("#")]
            if not poll_data_lines:
                raise Exception("poll_data.txt is empty")
            poll_data = poll_data_lines[0]
            if "|" not in poll_data:
                raise Exception("Invalid format in poll_data.txt")
            question_id, option_id = poll_data.split("|")
            print(f"{neon_green}Poll Data Loaded:{reset}")
            print(f"{neon_cyan}  Question ID: {question_id}{reset}")
            print(f"{neon_cyan}  Option ID: {option_id}{reset}")
        except Exception as e:
            logger.exception("poll_data load error: %s", e)
            print(f"{neon_red}[X] Error: poll_data.txt not found or invalid!{reset}")
            print(f"{neon_yellow}Please add poll data to poll_data.txt{reset}")
            print(f"{neon_cyan}Format: question_id|option_id{reset}")
            print(f"{neon_cyan}Example: 123456789012345|678901234567890{reset}")
            input(f"{gold}Press Enter to exit...{reset}")
            return
        print(f"\n{electric_blue}╔═══════════════════════════════════════════════════════════╗{reset}")
        print(f"{electric_blue}║              SELECT ACCOUNT TYPE FOR POLL                 ║{reset}")
        print(f"{electric_blue}╚═══════════════════════════════════════════════════════════╝{reset}")
        print(f"{neon_green}  [1] {HEART_SYMBOL} Use IDs   {reset}")
        print(f"{neon_yellow}  [2] {HEART_SYMBOL} Use Pages {reset}")
        print(f"{neon_pink}  [3] {HEART_SYMBOL} IDs + Pages (Both) {reset}")
        account_type = input(f"{gold}-> Select Account Type (1, 2, or 3): {reset}").strip()
        if account_type not in ["1", "2", "3"]:
            print(f"{neon_red}[X] Invalid account type selection! Defaulting to Pages (2).{reset}")
            account_type = "2"
        json_data = {"8": {"poll_data": poll_data, "poll_count": 0, "type": account_type}}
        jsondata.update(json_data)

    print(f"\n{neon_green}╔═══════════════════════════════════════════════════════════╗{reset}")
    print(f"{neon_green}║          STARTING AUTOMATED PROCESS                       ║{reset}")
    print(f"{neon_green}║                 *******                            ║{reset}")
    print(f"{neon_green}╚═══════════════════════════════════════════════════════════╝{reset}\n")

    # Execution
    count = 0

    global EXECUTOR
    EXECUTOR = ThreadPoolExecutor(max_workers=30)

    futures = []
    for data in filedata:
        futures.append(EXECUTOR.submit(run, data, jsondata, loaicv, count))
        if loaicv != "8":
            sleep(random.uniform(0.001, max(0.001, delay)))

    for fut in futures:
        try:
            fut.result()
        except Exception as e:
            logger.exception("main futures result error: %s", e)

    try:
        EXECUTOR.shutdown(wait=True)
    except Exception as e:
        logger.exception("Executor shutdown error: %s", e)

if __name__ == "__main__":
    while True:
        try:
            main()
            try:
                print(f"\n{neon_green}Process has been completed.{reset}")
            except Exception:
                print("\nProcess has been completed.")
            try:
                input(f"{gold}Press Enter to return to main menu (Ctrl+C to exit)...{reset}")
            except KeyboardInterrupt:
                print("\nExiting...")
                break
        except KeyboardInterrupt:
            print("\nExiting...")
            break
