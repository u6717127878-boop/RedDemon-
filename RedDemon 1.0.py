#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RED DEMON - Multitool OSINT (usage légal uniquement)
Dépendance : pip install requests
Lancer     : python red_demon.py
"""
import os, sys, re, ssl, json, time, socket, base64, hashlib, secrets, string, random
from datetime import datetime, timezone
import ipaddress, uuid, hmac
from urllib.parse import quote, urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
except ImportError:
    print("Installe requests :  pip install requests")
    sys.exit(1)

os.system("")  # active les couleurs ANSI sur Windows
W, G, D, X = "\033[97m", "\033[90m", "\033[2m", "\033[0m"
R = DR = ""

# ---- Thèmes de couleur (modifiables via le menu Settings) ----
CONFIG = os.path.join(os.path.expanduser("~"), ".red_demon_config.json")
OLD_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "red_demon_config.json")
DEFAULT_RGB = (255, 36, 0)  # écarlate
THEMES = {
    "Écarlate": (255, 36, 0), "Rouge": (255, 0, 0), "Cramoisi": (220, 20, 60),
    "Rouge sang": (160, 8, 8), "Orange": (255, 120, 0), "Jaune": (255, 215, 0),
    "Vert": (0, 220, 70), "Cyan": (0, 220, 220), "Bleu": (30, 120, 255),
    "Violet": (160, 60, 255), "Rose": (255, 60, 160), "Blanc": (240, 240, 240),
}

def rgb_code(c):
    return f"\033[38;2;{c[0]};{c[1]};{c[2]}m"

def set_theme(c, save=False):
    global R, DR
    R = rgb_code(c)
    DR = rgb_code(tuple(int(v * 0.65) for v in c))
    if not save:
        return True
    done = False
    for path in (CONFIG, OLD_CONFIG):  # on écrit aux deux endroits pour être sûr
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"rgb": list(c)}, f)
            done = True
        except OSError:
            pass
    return done

def load_theme():
    c, found = DEFAULT_RGB, []
    for path in (CONFIG, OLD_CONFIG):
        try:
            with open(path, encoding="utf-8") as f:
                v = json.load(f)["rgb"]
            if len(v) == 3 and all(isinstance(x, int) and 0 <= x <= 255 for x in v):
                found.append((os.path.getmtime(path), tuple(v)))
        except Exception:
            continue
    if found:
        c = max(found)[1]  # le plus récent gagne
    set_theme(c)

load_theme()
UA = {"User-Agent": "Mozilla/5.0 (RedDemon OSINT)"}
TIMEOUT = 10

BANNER = r"""
█ ██▀███  ▓█████ ▓█████▄    ▓█████▄ ▓█████  ███▄ ▄███▓ ▒█████   ███▄    █ 
▓██ ▒ ██▒▓█   ▀ ▒██▀ ██▌   ▒██▀ ██▌▓█   ▀ ▓██▒▀█▀ ██▒▒██▒  ██▒ ██ ▀█   █ 
▓██ ░▄█ ▒▒███   ░██   █▌   ░██   █▌▒███   ▓██    ▓██░▒██░  ██▒▓██  ▀█ ██▒
▒██▀▀█▄  ▒▓█  ▄ ░▓█▄   ▌   ░▓█▄   ▌▒▓█  ▄ ▒██    ▒██ ▒██   ██░▓██▒  ▐▌██▒
░██▓ ▒██▒░▒████▒░▒████▓    ░▒████▓ ░▒████▒▒██▒   ░██▒░ ████▓▒░▒██░   ▓██░
░ ▒▓ ░▒▓░░░ ▒░ ░ ▒▒▓  ▒     ▒▒▓  ▒ ░░ ▒░ ░░ ▒░   ░  ░░ ▒░▒░▒░ ░ ▒░   ▒ ▒ 
  ░▒ ░ ▒░ ░ ░  ░ ░ ▒  ▒     ░ ▒  ▒  ░ ░  ░░  ░      ░  ░ ▒ ▒░ ░ ░░   ░ ▒░
  ░░   ░    ░    ░ ░  ░     ░ ░  ░    ░   ░      ░   ░ ░ ░ ▒     ░   ░ ░ 
   ░        ░  ░   ░          ░       ░  ░       ░       ░ ░           ░ """
DRIPS = [
    "  ║   │    ╽      │   ║     │      ╽    │     ║      │    ╽    │   ║  ",
    "  ●   ║    ●      ╽   ●     ║      ●    ╽     ●      ║    ●    ╽   ●  ",
    "      ●           ●         ●           ●            ●        ●       ",
]

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def banner():
    clear()
    print(R + BANNER + X)
    for i, d in enumerate(DRIPS):
        print((R if i == 0 else DR) + d + X)
    print(f"{W}  Red Demon v1.4 {G}| {W}OSINT Multitool {G}| {R}github.com/redemon{X}\n")

def title(t):
    print(f"\n{R}┌─[ {W}{t}{R} ]{X}")

def line(k, v, w=18):
    print(f"{R}│ {W}{k:<{w}}{R}: {X}{v}")

def prompt(msg):
    return input(f"{R}├─ {W}{msg}{R} ➜ {X}").strip()

def ok(m):  print(f"{R}[{W}+{R}] {W}{m}{X}")
def err(m): print(f"{R}[{W}!{R}] {m}{X}")

def snowflake_date(sid):
    ts = ((int(sid) >> 22) + 1420070400000) / 1000
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")

def get_json(url, **kw):
    r = requests.get(url, headers=UA, timeout=kw.pop("timeout", TIMEOUT), **kw)
    return r

def clean_domain(s):
    s = s.strip()
    if "://" in s:
        s = urlparse(s).netloc
    return s.split("/")[0].split(":")[0]

# ─────────────────────────── GÉNÉRATEURS ───────────────────────────
def ask_count():
    c = prompt("Combien en générer ? [1] un seul  [10] dix")
    return 10 if c == "10" else 1

def gen_password():
    title("GÉNÉRATEUR DE MOT DE PASSE")
    n = ask_count()
    try:
        length = int(prompt("Longueur (défaut 16)") or 16)
    except ValueError:
        length = 16
    length = max(4, min(length, 128))
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+?"
    for i in range(n):
        while True:
            p = "".join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.islower() for c in p) and any(c.isupper() for c in p)
                    and any(c.isdigit() for c in p) and any(c in "!@#$%^&*()-_=+?" for c in p)):
                break
        line(f"#{i+1}", p, 4)

EMAIL_PROVIDERS = ["gmail.com", "outlook.com", "yahoo.fr", "proton.me", "icloud.com", "hotmail.com", "live.fr", "gmx.com"]

def choose_provider():
    print(f"{R}│ {W}Choisis le fournisseur :{X}")
    for n, d in enumerate(EMAIL_PROVIDERS, 1):
        print(f"{R}│ {R}[{W}{n}{R}] {W}{d}{X}")
    print(f"{R}│ {R}[{W}A{R}] {W}Aléatoire   {R}[{W}C{R}] {W}Domaine perso{X}")
    c = prompt("Ton choix").lower()
    if c.isdigit() and 1 <= int(c) <= len(EMAIL_PROVIDERS):
        return EMAIL_PROVIDERS[int(c) - 1]
    if c == "c":
        d = clean_domain(prompt("Domaine (ex: monsite.fr)")).lower()
        if re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", d):
            return d
        err("Domaine invalide, choix aléatoire à la place.")
    return None  # aléatoire

def gen_email():
    title("GÉNÉRATEUR D'EMAIL (aléatoire, fictif)")
    provider = choose_provider()
    n = ask_count()
    letters, chars = string.ascii_lowercase, string.ascii_lowercase + string.digits
    for i in range(n):
        size = random.randint(8, 12)
        local = secrets.choice(letters) + "".join(secrets.choice(chars) for _ in range(size - 1))
        line(f"#{i+1}", f"{local}@{provider or random.choice(EMAIL_PROVIDERS)}", 4)
    print(f"{G}│ Lettres et chiffres uniquement, aucun caractère spécial. Adresses fictives, non créées.{X}")

def gen_pseudo():
    title("GÉNÉRATEUR DE PSEUDO")
    n = ask_count()
    adj = ["Dark", "Silent", "Crimson", "Shadow", "Toxic", "Frozen", "Wild", "Lucky", "Cyber", "Ghost", "Neon", "Savage"]
    noun = ["Wolf", "Demon", "Tiger", "Phantom", "Raven", "Viper", "Hunter", "Falcon", "Ninja", "Reaper", "Fox", "Dragon"]
    for i in range(n):
        style = random.choice([0, 1, 2])
        a, b, num = random.choice(adj), random.choice(noun), random.randint(0, 999)
        p = [f"{a}{b}{num}", f"{a.lower()}_{b.lower()}", f"xX{a}{b}Xx"][style]
        line(f"#{i+1}", p, 4)

# (nom, indicatif, préfixes mobiles, longueur du numéro national, préfixe local, groupes d'affichage)
PHONE_COUNTRIES = [
    ("France", "33", ["6", "7"], 9, "0", [2, 2, 2, 2, 2]),
    ("Belgique", "32", ["470", "471", "472", "473", "474", "475", "476", "477", "478", "479", "485", "486", "487", "488", "489", "491", "492", "493", "494", "495", "496", "497", "498", "499"], 9, "0", [4, 2, 2, 2]),
    ("Suisse", "41", ["75", "76", "77", "78", "79"], 9, "0", [3, 3, 2, 2]),
    ("Luxembourg", "352", ["621", "628", "661", "671", "691"], 9, "", [3, 3, 3]),
    ("Royaume-Uni", "44", ["71", "72", "73", "74", "75", "77", "78", "79"], 10, "0", [5, 6]),
    ("Allemagne", "49", ["151", "152", "157", "160", "162", "170", "171", "172", "175", "176", "179"], 10, "0", [4, 7]),
    ("Espagne", "34", ["6", "71", "72", "73", "74"], 9, "", [3, 2, 2, 2]),
    ("Italie", "39", ["32", "33", "34", "35", "36", "37", "38", "39"], 10, "", [3, 3, 4]),
    ("Portugal", "351", ["91", "92", "93", "96"], 9, "", [3, 3, 3]),
    ("Maroc", "212", ["6", "7"], 9, "0", [2, 2, 2, 2, 2]),
    ("Algérie", "213", ["5", "6", "7"], 9, "0", [4, 2, 2, 2]),
    ("Tunisie", "216", ["2", "4", "5", "9"], 8, "", [2, 3, 3]),
    ("États-Unis / Canada", "1", None, 10, "", None),
]

def _group(digits, sizes):
    out, i = [], 0
    for g in sizes:
        out.append(digits[i:i + g]); i += g
    return " ".join(out)

def _rand_digits(n):
    return "".join(secrets.choice(string.digits) for _ in range(n))

def make_phone(country, prefixes=None):
    name, dial, pref, length, trunk, groups = country
    if pref is None:  # plan nord-américain : (AAA) EEE-LLLL
        while True:
            area = secrets.choice("23456789") + _rand_digits(2)
            if area[1:] != "11":
                break
        nsn = area + secrets.choice("23456789") + _rand_digits(2) + _rand_digits(4)
        return f"({nsn[0:3]}) {nsn[3:6]}-{nsn[6:]}", f"+1{nsn}"
    p = secrets.choice(prefixes or pref)
    nsn = p + _rand_digits(length - len(p))
    return _group(trunk + nsn, groups), f"+{dial}{nsn}"

def gen_phone():
    title("GÉNÉRATEUR DE NUMÉRO DE TÉLÉPHONE")
    print(f"{R}│ {W}Choisis le pays (Entrée = France) :{X}")
    half = (len(PHONE_COUNTRIES) + 1) // 2
    for i in range(half):
        l = PHONE_COUNTRIES[i]
        row = f"{R}│ {R}[{W}{i+1:02}{R}] {W}{l[0] + ' +' + l[1]:<26}{X}"
        j = i + half
        if j < len(PHONE_COUNTRIES):
            r = PHONE_COUNTRIES[j]
            row += f"{R}[{W}{j+1:02}{R}] {W}{r[0] + ' +' + r[1]}{X}"
        print(row)
    c = prompt("Ton choix")
    country = PHONE_COUNTRIES[int(c) - 1] if c.isdigit() and 1 <= int(c) <= len(PHONE_COUNTRIES) else PHONE_COUNTRIES[0]
    prefixes = None
    if country[0] == "France":
        print(f"{R}│ {R}[{W}1{R}] {W}06   {R}[{W}2{R}] {W}07   {R}[{W}3{R}] {W}Les deux (aléatoire){X}")
        prefixes = {"1": ["6"], "2": ["7"]}.get(prompt("Ton choix"))
    n = ask_count()
    line("Pays", f"{country[0]} (+{country[1]})", 6)
    for i in range(n):
        local, intl = make_phone(country, prefixes)
        line(f"#{i+1}", f"{local}   {G}({intl}){X}", 4)
    print(f"{G}│ Numéros tirés au hasard : ils peuvent exister par coïncidence, ne les appelle pas.{X}")

def gen_pin():
    title("GÉNÉRATEUR DE CODE PIN")
    n = ask_count()
    try:
        length = int(prompt("Nombre de chiffres (défaut 4)") or 4)
    except ValueError:
        length = 4
    length = max(3, min(length, 12))
    for i in range(n):
        line(f"#{i+1}", "".join(secrets.choice(string.digits) for _ in range(length)), 4)

# ─────────────────────────── IP / RÉSEAU ───────────────────────────
def my_ip():
    title("VIEW MY IP")
    try:
        ip = get_json("https://api.ipify.org?format=json").json()["ip"]
        line("IP publique", ip)
        try:
            line("Hostname", socket.gethostbyaddr(ip)[0])
        except Exception:
            pass
        d = get_json(f"https://ipwho.is/{ip}").json()
        if d.get("success"):
            line("Pays", f"{d['country']} ({d['country_code']})")
            line("Ville", f"{d['city']}, {d['region']}")
            line("FAI", d["connection"].get("isp", "?"))
    except Exception as e:
        err(f"Erreur : {e}")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); line("IP locale", s.getsockname()[0]); s.close()
    except Exception:
        pass

def ip_info():
    title("IP INFO")
    ip = prompt("IP ou domaine")
    if not ip:
        return
    try:
        d = get_json(f"https://ipwho.is/{clean_domain(ip)}").json()
        if not d.get("success"):
            return err(d.get("message", "IP invalide"))
        line("IP", d["ip"]); line("Type", d["type"])
        line("Continent", d["continent"]); line("Pays", f"{d['country']} ({d['country_code']})")
        line("Région / Ville", f"{d['region']} / {d['city']}"); line("Code postal", d.get("postal", "?"))
        line("Coordonnées", f"{d['latitude']}, {d['longitude']}")
        line("Maps", f"https://www.google.com/maps?q={d['latitude']},{d['longitude']}")
        c = d.get("connection", {})
        line("ASN", c.get("asn", "?")); line("Organisation", c.get("org", "?")); line("FAI", c.get("isp", "?"))
        line("Fuseau horaire", d.get("timezone", {}).get("id", "?"))
    except Exception as e:
        err(f"Erreur : {e}")

def whois_raw(server, q):
    with socket.create_connection((server, 43), timeout=TIMEOUT) as s:
        s.sendall((q + "\r\n").encode())
        data = b""
        while True:
            c = s.recv(4096)
            if not c:
                break
            data += c
    return data.decode(errors="ignore")

def whois():
    title("WHOIS (domaine ou IP)")
    q = clean_domain(prompt("Domaine ou IP"))
    if not q:
        return
    try:
        res = whois_raw("whois.iana.org", q)
        m = re.search(r"^refer:\s*(\S+)", res, re.M | re.I)
        if m:
            res = whois_raw(m.group(1), q)
            m2 = re.search(r"Registrar WHOIS Server:\s*(\S+)", res, re.I)
            if m2 and m2.group(1).lower() != m.group(1).lower():
                try: res = whois_raw(m2.group(1), q)
                except Exception: pass
        keys = ("domain name", "registrar", "creation date", "updated date", "expir", "name server",
                "status", "registrant", "org", "country", "netname", "inetnum", "cidr", "descr", "abuse")
        shown = set()
        for l in res.splitlines():
            if ":" in l and any(k in l.lower() for k in keys) and l.strip() not in shown:
                shown.add(l.strip())
                k, v = l.split(":", 1)
                if v.strip():
                    line(k.strip()[:24], v.strip(), 24)
        if not shown:
            print(res[:1500])
    except Exception as e:
        err(f"Erreur : {e}")

def dns_lookup():
    title("DNS LOOKUP")
    d = clean_domain(prompt("Domaine"))
    if not d:
        return
    for t in ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]:
        try:
            j = get_json(f"https://dns.google/resolve?name={d}&type={t}").json()
            for a in j.get("Answer", []):
                line(t, a["data"][:100], 6)
        except Exception as e:
            err(f"{t}: {e}")

def reverse_dns():
    title("REVERSE DNS")
    ip = prompt("Adresse IP")
    try:
        line("Hostname", socket.gethostbyaddr(ip)[0])
    except Exception:
        err("Aucun enregistrement PTR.")

def website_lookup():
    title("LOOKUP SITE WEB")
    u = prompt("URL ou domaine")
    if not u:
        return
    if "://" not in u:
        u = "https://" + u
    host = urlparse(u).netloc.split(":")[0]
    try:
        r = requests.get(u, headers=UA, timeout=TIMEOUT)
        line("URL finale", r.url); line("Statut", r.status_code)
        line("Temps réponse", f"{r.elapsed.total_seconds():.2f}s")
        try: line("IP", socket.gethostbyname(host))
        except Exception: pass
        m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.I | re.S)
        if m: line("Titre", m.group(1).strip()[:80])
        for h in ["Server", "X-Powered-By", "Content-Type", "Content-Length", "Last-Modified",
                  "Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options", "Set-Cookie"]:
            if h in r.headers:
                line(h, r.headers[h][:80])
        line("Redirections", " → ".join(x.url for x in r.history) or "aucune")
        try:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
                s.settimeout(TIMEOUT); s.connect((host, 443)); c = s.getpeercert()
            line("SSL émis par", dict(x[0] for x in c["issuer"]).get("organizationName", "?"))
            line("SSL valide de", c["notBefore"]); line("SSL expire le", c["notAfter"])
        except Exception:
            pass
        for f in ("robots.txt", "sitemap.xml"):
            try:
                rr = requests.get(f"{urlparse(r.url).scheme}://{host}/{f}", headers=UA, timeout=6)
                line(f, "présent" if rr.status_code == 200 else "absent")
            except Exception:
                pass
    except Exception as e:
        err(f"Erreur : {e}")

def http_headers():
    title("HTTP HEADERS")
    u = prompt("URL")
    if "://" not in u:
        u = "https://" + u
    try:
        r = requests.get(u, headers=UA, timeout=TIMEOUT)
        for k, v in r.headers.items():
            line(k[:26], v[:90], 26)
    except Exception as e:
        err(f"Erreur : {e}")

def subdomains():
    title("SOUS-DOMAINES (crt.sh)")
    d = clean_domain(prompt("Domaine"))
    if not d:
        return
    print(f"{G}│ Recherche dans les certificats publics (peut prendre du temps)...{X}")
    try:
        j = get_json(f"https://crt.sh/?q=%25.{d}&output=json", timeout=40).json()
        subs = sorted({n.strip().lstrip("*.") for e in j for n in e["name_value"].split("\n")})
        for s in subs[:80]:
            print(f"{R}│ {W}{s}{X}")
        ok(f"{len(subs)} sous-domaine(s) trouvé(s)" + (" (80 affichés)" if len(subs) > 80 else ""))
    except Exception as e:
        err(f"Erreur : {e}")

def wayback():
    title("WAYBACK MACHINE")
    u = prompt("URL")
    try:
        j = get_json(f"https://archive.org/wayback/available?url={quote(u)}").json()
        s = j.get("archived_snapshots", {}).get("closest")
        if s:
            line("Dernier snapshot", s["timestamp"]); line("Lien", s["url"])
        else:
            err("Aucune archive trouvée.")
    except Exception as e:
        err(f"Erreur : {e}")

def email_check():
    title("VÉRIFICATEUR D'EMAIL (format + MX)")
    e = prompt("Adresse email")
    okf = re.match(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$", e) is not None
    line("Format", "valide" if okf else "invalide")
    if okf:
        dom = e.split("@")[1]
        try:
            j = get_json(f"https://dns.google/resolve?name={dom}&type=MX").json()
            mx = [a["data"] for a in j.get("Answer", [])]
            line("Serveurs MX", ", ".join(mx) if mx else "aucun (domaine ne reçoit pas de mails)")
        except Exception as ex:
            err(f"{ex}")
        gh = hashlib.md5(e.strip().lower().encode()).hexdigest()
        line("Gravatar", f"https://www.gravatar.com/avatar/{gh}?d=404")

# ─────────────────────────── DISCORD ───────────────────────────
def discord_server():
    title("DISCORD SERVER INFO")
    q = prompt("Lien d'invitation, code ou ID du serveur")
    if not q:
        return
    try:
        if q.isdigit():
            line("ID", q); line("Créé le", snowflake_date(q))
            r = get_json(f"https://discord.com/api/guilds/{q}/widget.json")
            if r.status_code == 200:
                j = r.json()
                line("Nom", j.get("name")); line("Membres en ligne", j.get("presence_count"))
                if j.get("instant_invite"): line("Invitation", j["instant_invite"])
            else:
                print(f"{G}│ Widget désactivé : seule la date de création est disponible.{X}")
            return
        code = q.rstrip("/").split("/")[-1]
        r = get_json(f"https://discord.com/api/v10/invites/{code}?with_counts=true&with_expiration=true")
        if r.status_code != 200:
            return err("Invitation invalide ou expirée.")
        j = r.json(); g = j.get("guild", {})
        line("Nom", g.get("name")); line("ID", g.get("id"))
        line("Créé le", snowflake_date(g["id"]))
        if g.get("description"): line("Description", g["description"][:100])
        line("Membres", j.get("approximate_member_count")); line("En ligne", j.get("approximate_presence_count"))
        line("Vérification", g.get("verification_level")); line("Boosts", g.get("premium_subscription_count", 0))
        line("Salon d'invitation", (j.get("channel") or {}).get("name"))
        if g.get("vanity_url_code"): line("URL perso", f"discord.gg/{g['vanity_url_code']}")
        if g.get("features"): line("Features", ", ".join(g["features"])[:100])
        if g.get("icon"):
            line("Icône", f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png?size=1024")
        if g.get("banner"):
            line("Bannière", f"https://cdn.discordapp.com/banners/{g['id']}/{g['banner']}.png?size=1024")
        inv = j.get("inviter")
        if inv:
            line("Invité par", f"{inv.get('global_name') or inv['username']} ({inv['id']})")
        line("Expire le", j.get("expires_at") or "jamais")
    except Exception as e:
        err(f"Erreur : {e}")

def discord_user():
    title("DISCORD LOOKUP ID")
    uid = prompt("ID utilisateur Discord")
    if not uid.isdigit():
        return err("ID invalide (uniquement des chiffres).")
    line("ID", uid); line("Compte créé le", snowflake_date(uid))
    token = os.environ.get("DISCORD_BOT_TOKEN") or prompt("Token de TON bot Discord (Entrée pour ignorer)")
    if not token:
        print(f"{G}│ Sans token de bot, Discord ne donne pas le nom/avatar (limite de l'API officielle).{X}")
        line("Avatar par défaut", f"https://cdn.discordapp.com/embed/avatars/{(int(uid) >> 22) % 6}.png")
        return
    try:
        r = requests.get(f"https://discord.com/api/v10/users/{uid}",
                         headers={"Authorization": f"Bot {token}", **UA}, timeout=TIMEOUT)
        if r.status_code != 200:
            return err(f"Erreur API {r.status_code} (token ou ID invalide).")
        j = r.json()
        line("Nom d'utilisateur", j["username"]); line("Nom d'affichage", j.get("global_name") or "aucun")
        line("Bot", "oui" if j.get("bot") else "non")
        if j.get("avatar"):
            ext = "gif" if j["avatar"].startswith("a_") else "png"
            line("Photo de profil", f"https://cdn.discordapp.com/avatars/{uid}/{j['avatar']}.{ext}?size=1024")
        else:
            line("Photo de profil", "aucune (avatar par défaut)")
        if j.get("banner"):
            ext = "gif" if j["banner"].startswith("a_") else "png"
            line("Bannière", f"https://cdn.discordapp.com/banners/{uid}/{j['banner']}.{ext}?size=1024")
        if j.get("accent_color") is not None: line("Couleur", f"#{j['accent_color']:06x}")
    except Exception as e:
        err(f"Erreur : {e}")

def snowflake_tool():
    title("DÉCODEUR SNOWFLAKE DISCORD")
    s = prompt("ID (utilisateur, serveur, message, salon...)")
    if s.isdigit():
        line("Créé le", snowflake_date(s))
        line("Worker / Process", f"{(int(s) >> 17) & 31} / {(int(s) >> 12) & 31}")
    else:
        err("ID invalide.")

# ─────────────────────────── USERNAME / PROFILS ───────────────────────────
SITES = {
    "GitHub": "https://github.com/{}", "GitLab": "https://gitlab.com/{}", "Bitbucket": "https://bitbucket.org/{}/",
    "Reddit": "https://www.reddit.com/user/{}", "TikTok": "https://www.tiktok.com/@{}",
    "YouTube": "https://www.youtube.com/@{}", "Twitch": "https://www.twitch.tv/{}",
    "Pinterest": "https://www.pinterest.com/{}/", "SoundCloud": "https://soundcloud.com/{}",
    "Medium": "https://medium.com/@{}", "DeviantArt": "https://www.deviantart.com/{}",
    "Dev.to": "https://dev.to/{}", "Keybase": "https://keybase.io/{}", "Patreon": "https://www.patreon.com/{}",
    "Vimeo": "https://vimeo.com/{}", "Flickr": "https://www.flickr.com/people/{}",
    "About.me": "https://about.me/{}", "Behance": "https://www.behance.net/{}",
    "Dribbble": "https://dribbble.com/{}", "Pastebin": "https://pastebin.com/u/{}",
    "Replit": "https://replit.com/@{}", "npm": "https://www.npmjs.com/~{}", "PyPI": "https://pypi.org/user/{}/",
    "CodePen": "https://codepen.io/{}", "Spotify": "https://open.spotify.com/user/{}",
    "Snapchat": "https://www.snapchat.com/add/{}", "Linktree": "https://linktr.ee/{}",
    "Gravatar": "https://gravatar.com/{}", "Chess.com": "https://www.chess.com/member/{}",
    "Lichess": "https://lichess.org/@/{}", "Wattpad": "https://www.wattpad.com/user/{}",
    "Last.fm": "https://www.last.fm/user/{}", "Imgur": "https://imgur.com/user/{}",
    "Kaggle": "https://www.kaggle.com/{}", "LeetCode": "https://leetcode.com/{}/",
    "HackerRank": "https://www.hackerrank.com/{}", "Docker Hub": "https://hub.docker.com/u/{}",
    "Ko-fi": "https://ko-fi.com/{}", "Buy Me a Coffee": "https://www.buymeacoffee.com/{}",
    "Tumblr": "https://{}.tumblr.com", "WordPress": "https://{}.wordpress.com",
    "Telegram": "https://t.me/{}", "Steam": "https://steamcommunity.com/id/{}",
    "Roblox": "https://www.roblox.com/user.aspx?username={}", "Mastodon.social": "https://mastodon.social/@{}",
    "HackerOne": "https://hackerone.com/{}", "Product Hunt": "https://www.producthunt.com/@{}",
}

def username_tracker():
    title("USERNAME TRACKER")
    u = prompt("Pseudo à rechercher")
    if not u:
        return
    print(f"{G}│ Scan de {len(SITES)} plateformes...{X}")
    found = []

    def check(item):
        name, url = item
        url = url.format(u)
        try:
            r = requests.get(url, headers=UA, timeout=8, allow_redirects=True)
            return name, url, r.status_code == 200 and u.lower() in r.url.lower()
        except Exception:
            return name, url, None

    with ThreadPoolExecutor(max_workers=20) as ex:
        for name, url, res in ex.map(check, SITES.items()):
            if res:
                found.append((name, url)); print(f"{R}[{W}+{R}] {W}{name:<16}{X}{url}")
            elif res is False:
                print(f"{D}{G}[-] {name}{X}")
    ok(f"{len(found)} profil(s) probable(s) trouvé(s)")
    print(f"{G}│ Certains sites répondent 200 même sans compte : vérifie les liens.{X}")

def github_lookup():
    title("GITHUB LOOKUP")
    u = prompt("Nom d'utilisateur GitHub")
    try:
        r = get_json(f"https://api.github.com/users/{quote(u)}")
        if r.status_code != 200:
            return err("Utilisateur introuvable.")
        j = r.json()
        for k, lab in [("login", "Pseudo"), ("id", "ID"), ("name", "Nom"), ("company", "Société"),
                       ("location", "Lieu"), ("blog", "Site"), ("bio", "Bio"), ("public_repos", "Dépôts"),
                       ("followers", "Followers"), ("following", "Suivis"), ("created_at", "Créé le"),
                       ("avatar_url", "Avatar"), ("html_url", "Profil")]:
            if j.get(k) is not None:
                line(lab, j[k])
        ev = get_json(f"https://api.github.com/users/{quote(u)}/events/public").json()
        emails = {c["author"]["email"] for e in ev if e.get("type") == "PushEvent"
                  for c in e["payload"].get("commits", []) if "noreply" not in c["author"]["email"]}
        if emails: line("Emails publics (commits)", ", ".join(emails), 24)
    except Exception as e:
        err(f"Erreur : {e}")

# ─────────────────────────── UTILITAIRES ───────────────────────────
def hash_tool():
    title("GÉNÉRATEUR DE HASH")
    t = prompt("Texte à hasher")
    for a in ["md5", "sha1", "sha256", "sha512"]:
        line(a.upper(), hashlib.new(a, t.encode()).hexdigest(), 8)

def b64_tool():
    title("BASE64 / URL ENCODE-DECODE")
    t = prompt("Texte")
    line("Base64 encodé", base64.b64encode(t.encode()).decode(), 16)
    try: line("Base64 décodé", base64.b64decode(t, validate=True).decode(errors="replace"), 16)
    except Exception: pass
    line("URL encodé", quote(t), 16)

# ─────────────────────────── OUTILS SUPPLÉMENTAIRES ───────────────────────────
def norm_url(u):
    return u if "://" in u else "https://" + u

def hash_identify():
    title("IDENTIFICATEUR DE HASH")
    h = prompt("Hash").strip()
    by_len = {32: "MD5 / NTLM", 40: "SHA-1", 56: "SHA-224", 64: "SHA-256", 96: "SHA-384", 128: "SHA-512"}
    line("Longueur", len(h))
    if h.startswith(("$2a$", "$2b$", "$2y$")): line("Type probable", "bcrypt")
    elif h.startswith("$6$"): line("Type probable", "SHA-512 crypt")
    elif h.startswith("$1$"): line("Type probable", "MD5 crypt")
    elif re.fullmatch(r"[0-9a-fA-F]+", h) and len(h) in by_len: line("Type probable", by_len[len(h)])
    else: err("Type inconnu.")

def extract_links():
    title("EXTRACTEUR DE LIENS")
    u = norm_url(prompt("URL de la page"))
    try:
        r = requests.get(u, headers=UA, timeout=TIMEOUT)
        links = sorted({urljoin(r.url, l) for l in re.findall(r'href=["\'](.*?)["\']', r.text)
                        if not l.startswith(("#", "javascript:", "mailto:"))})
        for l in links[:60]: print(f"{R}│ {W}{l}{X}")
        ok(f"{len(links)} lien(s)" + (" (60 affichés)" if len(links) > 60 else ""))
    except Exception as e:
        err(f"Erreur : {e}")

def extract_emails():
    title("EXTRACTEUR D'EMAILS (page publique)")
    u = norm_url(prompt("URL de la page"))
    try:
        t = requests.get(u, headers=UA, timeout=TIMEOUT).text
        mails = sorted(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+\w", t)))
        for m in mails: print(f"{R}│ {W}{m}{X}")
        ok(f"{len(mails)} email(s) trouvé(s)")
    except Exception as e:
        err(f"Erreur : {e}")

def robots_view():
    title("ROBOTS.TXT")
    u = urlparse(norm_url(prompt("Domaine")))
    try:
        r = requests.get(f"{u.scheme}://{u.netloc}/robots.txt", headers=UA, timeout=TIMEOUT)
        if r.status_code != 200: return err(f"Introuvable ({r.status_code}).")
        for l in r.text.splitlines()[:50]: print(f"{R}│ {W}{l}{X}")
    except Exception as e:
        err(f"Erreur : {e}")

def sitemap_view():
    title("SITEMAP.XML")
    u = urlparse(norm_url(prompt("Domaine")))
    try:
        r = requests.get(f"{u.scheme}://{u.netloc}/sitemap.xml", headers=UA, timeout=TIMEOUT)
        if r.status_code != 200: return err(f"Introuvable ({r.status_code}).")
        locs = re.findall(r"<loc>(.*?)</loc>", r.text)
        for l in locs[:50]: print(f"{R}│ {W}{l}{X}")
        ok(f"{len(locs)} URL(s)")
    except Exception as e:
        err(f"Erreur : {e}")

def tech_detect():
    title("DÉTECTEUR DE TECHNOLOGIES WEB")
    u = norm_url(prompt("URL"))
    sigs = {"WordPress": "wp-content", "Shopify": "cdn.shopify.com", "Wix": "wixstatic.com",
            "Squarespace": "squarespace", "React": "data-reactroot", "Next.js": "__NEXT_DATA__",
            "Vue.js": "vue", "Angular": "ng-version", "jQuery": "jquery", "Bootstrap": "bootstrap",
            "Tailwind": "tailwind", "Google Analytics": "google-analytics.com", "Google Tag Manager": "googletagmanager",
            "Cloudflare": "cloudflare", "Drupal": "drupal", "Joomla": "joomla", "PrestaShop": "prestashop"}
    try:
        r = requests.get(u, headers=UA, timeout=TIMEOUT)
        blob = (r.text + str(r.headers) + str(r.cookies.get_dict())).lower()
        found = [n for n, s in sigs.items() if s.lower() in blob]
        for h in ("Server", "X-Powered-By", "Via"):
            if h in r.headers: found.append(f"{h}: {r.headers[h]}")
        if "csrftoken" in blob: found.append("Django (probable)")
        if "laravel_session" in blob: found.append("Laravel")
        for f in found: print(f"{R}[{W}+{R}] {W}{f}{X}")
        if not found: err("Rien détecté.")
    except Exception as e:
        err(f"Erreur : {e}")

def unshorten():
    title("UNSHORTENER (suivi de redirections)")
    u = norm_url(prompt("Lien raccourci"))
    try:
        r = requests.get(u, headers=UA, timeout=TIMEOUT, stream=True)
        for i, h in enumerate(r.history): line(f"Étape {i+1}", f"{h.status_code} → {h.headers.get('Location', '')[:90]}", 8)
        line("Destination", r.url, 12)
        r.close()
    except Exception as e:
        err(f"Erreur : {e}")

def site_status():
    title("SITE UP OR DOWN")
    u = norm_url(prompt("URL"))
    try:
        t = time.time(); r = requests.get(u, headers=UA, timeout=TIMEOUT)
        line("État", f"EN LIGNE ({r.status_code})"); line("Temps", f"{time.time() - t:.2f}s")
    except Exception as e:
        line("État", "HORS LIGNE ou injoignable"); line("Détail", str(e)[:80])

def cidr_calc():
    title("CALCULATEUR CIDR")
    try:
        n = ipaddress.ip_network(prompt("Réseau (ex: 192.168.1.0/24)"), strict=False)
        line("Réseau", n.network_address); line("Masque", n.netmask)
        line("Broadcast", n.broadcast_address if n.version == 4 else "n/a")
        line("Nb d'adresses", n.num_addresses)
        line("Première IP", n.network_address + 1 if n.num_addresses > 2 else n.network_address)
        line("Dernière IP", n.broadcast_address - 1 if n.version == 4 and n.num_addresses > 2 else n.broadcast_address)
        line("Privé", "oui" if n.is_private else "non")
    except Exception as e:
        err(f"Erreur : {e}")

def ip_convert():
    title("CONVERTISSEUR D'IP")
    try:
        ip = ipaddress.ip_address(prompt("Adresse IP"))
        line("Décimal", int(ip)); line("Hexadécimal", hex(int(ip)))
        line("Binaire", bin(int(ip))[2:].zfill(32 if ip.version == 4 else 128), 12)
        line("Privée", "oui" if ip.is_private else "non"); line("Loopback", "oui" if ip.is_loopback else "non")
    except Exception as e:
        err(f"Erreur : {e}")

def jwt_decode():
    title("DÉCODEUR JWT (sans vérification)")
    t = prompt("Token JWT")
    try:
        for name, part in zip(("Header", "Payload"), t.split(".")[:2]):
            data = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
            line(name, json.dumps(data, ensure_ascii=False))
            for k in ("iat", "exp", "nbf"):
                if k in data: line(f"  {k}", datetime.fromtimestamp(data[k], timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC"))
    except Exception:
        err("Token invalide.")

def text_convert():
    title("TEXTE ⇄ HEX / BINAIRE")
    t = prompt("Texte")
    line("Hex", t.encode().hex()); line("Binaire", " ".join(f"{b:08b}" for b in t.encode()))
    try: line("Hex → texte", bytes.fromhex(t.replace(" ", "")).decode(errors="replace"))
    except Exception: pass

def caesar():
    title("CÉSAR / ROT13")
    t = prompt("Texte")
    def sh(s, k):
        return "".join(chr((ord(c) - (65 if c.isupper() else 97) + k) % 26 + (65 if c.isupper() else 97)) if c.isalpha() and c.isascii() else c for c in s)
    line("ROT13", sh(t, 13))
    for k in range(1, 26):
        if k != 13: print(f"{R}│ {G}+{k:<2}{X} {sh(t, k)}")

def timestamp_tool():
    title("TIMESTAMP UNIX")
    t = prompt("Timestamp (Entrée = maintenant)")
    if t.isdigit():
        v = int(t) / (1000 if len(t) > 11 else 1)
        line("Date UTC", datetime.fromtimestamp(v, timezone.utc).strftime("%d/%m/%Y %H:%M:%S"))
    else:
        line("Maintenant", int(time.time())); line("Date UTC", datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S"))

def gen_uuid():
    title("GÉNÉRATEUR D'UUID")
    for i in range(ask_count()): line(f"#{i+1}", uuid.uuid4(), 4)

def fake_iban():
    bank, branch = f"{random.randint(0, 99999):05}", f"{random.randint(0, 99999):05}"
    acc = f"{random.randint(0, 10**11 - 1):011}"
    key = 97 - ((89 * int(bank) + 15 * int(branch) + 3 * int(acc)) % 97)
    bban = f"{bank}{branch}{acc}{key:02}"
    check = 98 - (int(bban + "152700") % 97)  # F=15 R=27, "00" -> 152700
    iban = f"FR{check:02}{bban}"
    return " ".join(iban[i:i + 4] for i in range(0, len(iban), 4))

def fake_identity():
    title("GÉNÉRATEUR D'IDENTITÉ FICTIVE")
    fn = ["Lucas", "Emma", "Hugo", "Léa", "Noah", "Chloé", "Louis", "Manon", "Jules", "Alice"]
    ln = ["Martin", "Bernard", "Dubois", "Petit", "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Girard"]
    city = ["Paris", "Lyon", "Lille", "Nantes", "Toulouse", "Bordeaux", "Marseille", "Rennes"]
    strip = lambda s: "".join(c for c in __import__("unicodedata").normalize("NFD", s.lower()) if c.isalpha())
    for i in range(ask_count()):
        f, l = random.choice(fn), random.choice(ln)
        line("Nom", f"{f} {l}", 14)
        line("Naissance", f"{random.randint(1, 28):02}/{random.randint(1, 12):02}/{random.randint(1965, 2003)}", 14)
        line("Ville", random.choice(city), 14)
        line("Téléphone", "06 " + " ".join(f"{random.randint(0, 99):02}" for _ in range(4)), 14)
        line("Email", f"{strip(f)}{strip(l)}{random.randint(10, 9999)}@{random.choice(EMAIL_PROVIDERS)}", 14)
        line("IP", f"{random.choice(['192.0.2', '198.51.100', '203.0.113'])}.{random.randint(1, 254)}", 14)
        line("IBAN", fake_iban(), 14)
        print(f"{R}│{X}")
    print(f"{G}│ Données générées au hasard : l'email n'est pas créé (il peut exister par coïncidence),{X}")
    print(f"{G}│ IP en plages de documentation (RFC 5737), IBAN de format valide mais sans compte réel. Tests uniquement.{X}")

def ua_gen():
    title("GÉNÉRATEUR DE USER-AGENT")
    uas = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
           "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
           "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
           "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"]
    for i in range(ask_count()): line(f"#{i+1}", random.choice(uas)[:110], 4)

def exif_read():
    title("MÉTADONNÉES EXIF D'UNE IMAGE")
    try:
        from PIL import Image, ExifTags
    except ImportError:
        return err("Installe Pillow :  pip install pillow")
    p = prompt("Chemin de l'image").strip('"')
    try:
        im = Image.open(p); ex = im.getexif()
        line("Format", f"{im.format} {im.size[0]}x{im.size[1]}")
        if not ex: return err("Aucune donnée EXIF.")
        for k, v in ex.items():
            print(f"{R}│ {W}{ExifTags.TAGS.get(k, k)!s:<22}{R}: {X}{str(v)[:70]}")
        gps = ex.get_ifd(0x8825)
        if gps: line("GPS (brut)", {ExifTags.GPSTAGS.get(k, k): str(v) for k, v in gps.items()})
    except Exception as e:
        err(f"Erreur : {e}")

def gravatar_lookup():
    title("GRAVATAR LOOKUP (par email)")
    e = prompt("Email")
    h = hashlib.md5(e.strip().lower().encode()).hexdigest()
    try:
        r = requests.get(f"https://gravatar.com/{h}.json", headers=UA, timeout=TIMEOUT)
        if r.status_code != 200: return err("Aucun profil Gravatar public.")
        j = r.json()["entry"][0]
        line("Pseudo", j.get("preferredUsername")); line("Nom affiché", j.get("displayName"))
        line("Lieu", j.get("currentLocation") or "?"); line("À propos", (j.get("aboutMe") or "?")[:80])
        line("Avatar", j.get("thumbnailUrl"))
        for u in j.get("urls", []): line("Lien", u.get("value"))
        for a in j.get("accounts", []): line(a.get("shortname", "compte"), a.get("url"))
    except Exception as ex:
        err(f"Erreur : {ex}")

def passphrase_gen():
    title("GÉNÉRATEUR DE PHRASE DE PASSE")
    words = ("lune soleil arbre fleuve nuage pierre foret plage neige orage vent feu terre ciel etoile "
             "montagne vallee pont tour jardin marche livre stylo table chaise porte fenetre route train "
             "avion bateau velo moto cafe the pain fromage pomme poire fraise citron miel sucre sel "
             "chat chien loup renard aigle cheval tigre lion ours singe requin dauphin baleine hibou "
             "rouge bleu vert jaune noir blanc gris rose").split()
    try:
        n = max(3, min(int(prompt("Nombre de mots (défaut 5)") or 5), 10))
    except ValueError:
        n = 5
    for i in range(ask_count()):
        p = "-".join(secrets.choice(words) for _ in range(n)) + "-" + str(secrets.randbelow(100))
        line(f"#{i+1}", p, 4)
    line("Entropie ~", f"{n * len(words).bit_length() * 0.99:.0f} bits (liste de {len(words)} mots)", 10)

def pwd_strength():
    import math
    title("FORCE D'UN MOT DE PASSE (local)")
    p = prompt("Mot de passe à tester")
    if not p:
        return
    pool = 0
    pool += 26 if any(c.islower() for c in p) else 0
    pool += 26 if any(c.isupper() for c in p) else 0
    pool += 10 if any(c.isdigit() for c in p) else 0
    pool += 32 if any(not c.isalnum() for c in p) else 0
    bits = len(p) * math.log2(pool or 1)
    common = {"password", "123456", "azerty", "qwerty", "motdepasse", "admin", "letmein", "111111"}
    if p.lower() in common:
        bits = 5
    note = "très faible" if bits < 28 else "faible" if bits < 40 else "moyen" if bits < 60 else "fort" if bits < 80 else "très fort"
    line("Longueur", len(p)); line("Entropie", f"{bits:.0f} bits"); line("Niveau", note)
    print(f"{G}│ Le mot de passe reste sur ta machine, rien n'est envoyé.{X}")

def mac_vendor():
    title("MAC VENDOR LOOKUP")
    m = prompt("Adresse MAC (ex: 00:1A:2B:3C:4D:5E)")
    try:
        r = requests.get(f"https://api.macvendors.com/{quote(m)}", headers=UA, timeout=TIMEOUT)
        line("Fabricant", r.text.strip() if r.status_code == 200 else "introuvable")
    except Exception as e:
        err(f"Erreur : {e}")

def sec_headers():
    title("AUDIT DES HEADERS DE SÉCURITÉ")
    u = norm_url(prompt("URL"))
    try:
        r = requests.get(u, headers=UA, timeout=TIMEOUT)
        heads = ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options",
                 "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy"]
        score = 0
        for h in heads:
            has = h in r.headers
            score += has
            print(f"{R}│ {W}{h:<28}{R}: {X}{'présent' if has else 'ABSENT'}")
        ok(f"Score : {score}/{len(heads)}")
    except Exception as e:
        err(f"Erreur : {e}")

def reverse_ip():
    title("REVERSE IP LOOKUP (sites sur la même IP)")
    q = clean_domain(prompt("IP ou domaine"))
    try:
        r = requests.get(f"https://api.hackertarget.com/reverseiplookup/?q={quote(q)}", headers=UA, timeout=20)
        t = r.text.strip()
        if "error" in t.lower() or "no records" in t.lower() or "API count" in t:
            return err(t[:100])
        for d in t.splitlines()[:60]: print(f"{R}│ {W}{d}{X}")
    except Exception as e:
        err(f"Erreur : {e}")

def settings():
    while True:
        banner()
        print(f"{R}┌─[ {W}SETTINGS : COULEUR DU PANEL{R} ]{X}")
        print(f" {G}Sauvegarde : {CONFIG}{X}")
        names = list(THEMES)
        for n, name in enumerate(names, 1):
            print(f" {rgb_code(THEMES[name])}[{n:02}] ████████ {W}{name}{X}")
        print(f"\n {R}[{W}C{R}]{W} Couleur perso (hex, ex: #FF2400)   {R}[{W}D{R}]{W} Par défaut (écarlate)   {R}[{W}0{R}]{W} Retour{X}\n")
        c = prompt("Choix").lower()
        if c == "0":
            return
        saved = None
        if c == "d":
            saved = set_theme(DEFAULT_RGB, save=True)
        elif c == "c":
            h = prompt("Code hex").lstrip("#")
            if re.fullmatch(r"[0-9a-fA-F]{6}", h):
                saved = set_theme((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)), save=True)
            else:
                err("Code invalide (6 caractères, ex: FF2400)."); time.sleep(1.2)
        elif c.isdigit() and 1 <= int(c) <= len(names):
            saved = set_theme(THEMES[names[int(c) - 1]], save=True)
        if saved is True:
            ok("Couleur sauvegardée, elle restera au prochain lancement."); time.sleep(1)
        elif saved is False:
            err(f"Impossible de sauvegarder dans {CONFIG}"); time.sleep(2.5)

# ─────────────────────────── COMPTES (local) ───────────────────────────
USERS_FILE = os.path.join(os.path.expanduser("~"), ".red_demon_users.json")

def load_users():
    try:
        with open(USERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f)
        return True
    except OSError:
        return False

def hash_pw(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex(), h.hex()

def register():
    title("S'INSCRIRE")
    users = load_users()
    name = prompt("Identifiant (3-20 lettres, chiffres ou _)")
    if not re.fullmatch(r"\w{3,20}", name):
        return err("Identifiant invalide.")
    if name.lower() in {u.lower() for u in users}:
        return err("Cet identifiant existe déjà.")
    pw = prompt("Mot de passe (8 caractères min)")
    if len(pw) < 8:
        return err("Mot de passe trop court (8 caractères minimum).")
    salt, h = hash_pw(pw)
    users[name] = {"salt": salt, "hash": h, "created": datetime.now().strftime("%d/%m/%Y %H:%M")}
    if save_users(users):
        ok(f"Compte « {name} » créé. Tu peux te connecter.")
        return name
    err(f"Impossible d'enregistrer le compte dans {USERS_FILE}")

def login():
    title("SE CONNECTER")
    users = load_users()
    name = prompt("Identifiant")
    for attempt in range(3):
        pw = prompt("Mot de passe")
        u = users.get(name)
        if u:
            _, h = hash_pw(pw, bytes.fromhex(u["salt"]))
            good = hmac.compare_digest(h, u["hash"])
        else:
            hash_pw(pw)  # même temps de calcul si le compte n'existe pas
            good = False
        if good:
            ok(f"Bienvenue, {name} !"); time.sleep(0.8)
            return name
        err(f"Identifiant ou mot de passe incorrect ({attempt + 1}/3).")
    time.sleep(1.5)
    return None

def auth_screen():
    while True:
        banner()
        print(f"{R}┌─[ {W}ACCÈS À RED DEMON{R} ]{X}")
        print(f" {R}[{W}1{R}] {W}Se connecter      {R}[{W}2{R}] {W}S'inscrire      {R}[{W}0{R}] {W}Quitter{X}\n")
        c = prompt("Choix")
        if c == "0":
            return None
        if c == "1":
            u = login()
            if u:
                return u
        elif c == "2":
            register(); time.sleep(1.5)

# ─────────────────────────── MENUS ───────────────────────────
PAGES = [
    ("PAGE 1/2 : L'ESSENTIEL", [
        ("Username Tracker", username_tracker), ("View my IP", my_ip), ("IP Info", ip_info),
        ("Whois", whois), ("Discord Server Info", discord_server), ("Discord Lookup ID", discord_user),
        ("Lookup site web", website_lookup), ("GitHub Lookup", github_lookup),
        ("DNS Lookup", dns_lookup), ("Vérificateur d'email", email_check),
        ("Générateur de mot de passe", gen_password), ("Générateur d'email", gen_email),
        ("Générateur de pseudo", gen_pseudo), ("Générateur de code PIN", gen_pin),
        ("Générateur de num. de tél", gen_phone), ("Générateur d'identité fictive", fake_identity),
    ]),
    ("PAGE 2/2 : 30 OUTILS", [
        ("Générateur d'UUID", gen_uuid), ("Générateur de User-Agent", ua_gen),
        ("Générateur de hash", hash_tool), ("Identificateur de hash", hash_identify),
        ("Phrase de passe", passphrase_gen), ("Force d'un mot de passe", pwd_strength),
        ("Base64 / URL", b64_tool), ("Texte <-> Hex / Binaire", text_convert),
        ("César / ROT13", caesar), ("Timestamp Unix", timestamp_tool), ("Décodeur JWT", jwt_decode),
        ("Décodeur Snowflake Discord", snowflake_tool), ("Reverse DNS", reverse_dns),
        ("Reverse IP Lookup", reverse_ip), ("Sous-domaines (crt.sh)", subdomains),
        ("HTTP Headers", http_headers), ("Audit headers sécurité", sec_headers),
        ("Wayback Machine", wayback), ("Extracteur de liens", extract_links),
        ("Extracteur d'emails", extract_emails), ("Robots.txt", robots_view),
        ("Sitemap.xml", sitemap_view), ("Technologies web", tech_detect),
        ("Unshortener (redirections)", unshorten), ("Site up or down", site_status),
        ("Calculateur CIDR", cidr_calc), ("Convertisseur d'IP", ip_convert),
        ("MAC Vendor Lookup", mac_vendor), ("EXIF image", exif_read), ("Gravatar Lookup", gravatar_lookup),
    ]),
]

def run_tool(fn):
    while True:
        banner()
        fn()
        print(f"{R}└{'─' * 40}{X}")
        c = prompt("[1] Relancer   [0] Retour")
        if c != "1":
            break

def main():
    page = 0
    user = auth_screen()
    if not user:
        print(f"{R}À bientôt 😈{X}"); return
    while True:
        banner()
        name, tools = PAGES[page]
        base = 1 if page == 0 else len(PAGES[0][1]) + 1
        print(f"{R}┌─[ {W}{name}{R} ]{X}  {G}connecté : {W}{user}{X}")
        half = (len(tools) + 1) // 2
        for i in range(half):
            l = f"{R}[{W}{base + i:02}{R}] {W}{tools[i][0]:<32}{X}"
            r = ""
            if i + half < len(tools):
                r = f"{R}[{W}{base + i + half:02}{R}] {W}{tools[i + half][0]}{X}"
            print(f" {l}{r}")
        nav = f"{R}[{W}N{R}]{W} Page suivante" if page == 0 else f"{R}[{W}P{R}]{W} Page précédente"
        print(f"\n {nav}     {R}[{W}S{R}]{W} Settings     {R}[{W}L{R}]{W} Déconnexion     {R}[{W}0{R}]{W} Quitter{X}\n")
        c = input(f"{R}┌──({W}red{R}㉿{W}demon{R})-[{W}~{R}]\n└─{W}${X} ").strip().lower()
        if c == "0":
            print(f"{R}À bientôt 😈{X}"); break
        if c == "s": settings(); continue
        if c == "l":
            user = auth_screen()
            if not user:
                print(f"{R}À bientôt 😈{X}"); break
            page = 0; continue
        if c == "n" and page == 0: page = 1; continue
        if c == "p" and page == 1: page = 0; continue
        if c.isdigit() and 0 <= int(c) - base < len(tools):
            run_tool(tools[int(c) - base][1])

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{R}Fermeture de Red Demon.{X}")
