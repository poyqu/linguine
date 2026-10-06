"""Check Steam for a new build of the game (no login needed) and post to a Discord webhook when it changes.

Run by .github/workflows/steam-watch.yml every few minutes. The last seen build ids live in state/last.json,
which the workflow carries from run to run in the Actions cache.

Source: Steam's public app info (the same data SteamDB shows), read through api.steamcmd.net; if that
service is down, the anonymous SteamCMD docker image is asked instead. Neither needs a Steam account.

Env: DISCORD_WEBHOOK (secret), DISCORD_PING (optional, e.g. <@123456789> to ping a user), TEST=1 sends a test post."""
import json, os, re, subprocess, sys, time, urllib.request

APP = "4368350"
STATE = os.path.join("state", "last.json")
UA = {"User-Agent": "linguine-steam-watch (github.com/poyqu/linguine)"}


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def branches_api():
    d = get_json(f"https://api.steamcmd.net/v1/info/{APP}")
    br = d["data"][APP]["depots"]["branches"]
    return {k: {"buildid": v.get("buildid"), "time": int(v.get("timeupdated") or 0), "pwd": "pwdrequired" in v}
            for k, v in br.items()}


def branches_steamcmd():
    out = subprocess.run(["docker", "run", "--rm", "steamcmd/steamcmd:latest", "+login", "anonymous",
                          "+app_info_update", "1", "+app_info_print", APP, "+quit"],
                         capture_output=True, text=True, timeout=300).stdout
    m = re.search(r'"branches"\s*\{(.*?)\n\t\t\}', out, re.S)
    if not m:
        raise RuntimeError("steamcmd: no branches block")
    res = {}
    for name, body in re.findall(r'"([^"]+)"\s*\{([^{}]*)\}', m.group(1)):
        bid = re.search(r'"buildid"\s+"(\d+)"', body)
        tu = re.search(r'"timeupdated"\s+"(\d+)"', body)
        if bid:
            res[name] = {"buildid": bid.group(1), "time": int(tu.group(1)) if tu else 0, "pwd": "pwdrequired" in body}
    return res


def latest_news():
    """Newest Steam announcement (title, url, time), or None."""
    try:
        d = get_json(f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={APP}&count=1&maxlength=300")
        it = d["appnews"]["newsitems"][0]
        return it["title"], it["url"], int(it["date"]), it.get("contents", "")
    except Exception:
        return None


def post(content, embed=None):
    hook = os.environ.get("DISCORD_WEBHOOK", "").strip()
    if not hook:
        print("DISCORD_WEBHOOK secret is not set; message would have been:\n" + content)
        return
    body = {"content": content, "username": "Linguine update watch",
            "allowed_mentions": {"parse": ["users", "roles"]}}
    if embed:
        body["embeds"] = [embed]
    req = urllib.request.Request(hook, data=json.dumps(body).encode(), method="POST",
                                 headers={**UA, "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30).read()


def main():
    try:
        br = branches_api()
        src = "api.steamcmd.net"
    except Exception as e:
        print("api.steamcmd.net failed:", e)
        br = branches_steamcmd()
        src = "steamcmd (anonymous)"
    if "public" not in br:
        sys.exit("no public branch in the reply")
    print(src, json.dumps(br))

    old = json.load(open(STATE)) if os.path.exists(STATE) else None
    os.makedirs("state", exist_ok=True)
    json.dump(br, open(STATE, "w"))
    changed = old is not None and any(old.get(k, {}).get("buildid") != v["buildid"] for k, v in br.items())
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"save={'true' if changed or old is None else 'false'}\n")

    ping = os.environ.get("DISCORD_PING", "").strip()
    pub = br["public"]
    if os.environ.get("TEST") == "1":
        post(f"{ping} Test message: the watcher works. Live build is {pub['buildid']}.".strip())
        return
    if old is None:
        post(f"Watching Steam for game updates. Live build right now: {pub['buildid']}.")
        return
    if not changed:
        return

    lines = []
    for k, v in sorted(br.items(), key=lambda kv: kv[0] != "public"):
        was = old.get(k, {}).get("buildid")
        if was != v["buildid"]:
            label = "Public" if k == "public" else f"Branch `{k}`" + (" (password)" if v["pwd"] else "")
            lines.append(f"**{label}**: {was or 'new'} → **{v['buildid']}** (<t:{v['time']}:R>)")
    embed = {"title": "Silly Linguine Cat Simulator: new Steam build",
             "url": f"https://steamdb.info/app/{APP}/patchnotes/",
             "description": "\n".join(lines), "color": 0xF4A340,
             "footer": {"text": f"source: {src}"}}
    n = latest_news()
    if n and n[2] > time.time() - 12 * 3600:
        embed["fields"] = [{"name": "Latest Steam news", "value": f"[{n[0]}]({n[1]})"}]
    head = "New game build is live" if br["public"]["buildid"] != old.get("public", {}).get("buildid") \
        else "A Steam branch changed"
    post(f"{ping} {head}. Update the game, then run `python update_pipeline.py --force`.".strip(), embed)


if __name__ == "__main__":
    main()
