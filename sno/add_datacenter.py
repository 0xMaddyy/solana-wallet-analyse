from sno.paths import RESULTS, SOURCES, LABELS, label_file, source_file, ROOT
"""Add data_center to backruns_oct8.csv from leader_ip via ip-api.com (org/AS)."""
import csv
import json
import re
import sys
import urllib.request
from collections import Counter

# Known Solana/hosting ASN or org substrings -> short data-center label.
# Checked against common validator colo names; unmatched rows keep the cleaned org.
ASN_DC = {
    "AS20473": "Choopa / Vultr",
    "AS16276": "OVH",
    "AS24940": "Hetzner",
    "AS14061": "DigitalOcean",
    "AS16509": "AWS",
    "AS14618": "AWS",
    "AS15169": "Google",
    "AS396982": "Google",
    "AS8075": "Microsoft Azure",
    "AS13335": "Cloudflare",
    "AS9009": "M247",
    "AS51167": "Contabo",
    "AS8560": "IONOS",
    "AS54825": "Packet / Equinix Metal",
    "AS399629": "Latitude.sh",
    "AS396356": "Latitude.sh",
    "AS31898": "Oracle Cloud",
    "AS62563": "Latency Networks",
    "AS60068": "CDN77",
    "AS212238": "Datacamp",
    "AS60087": "Mevspace",
    "AS29802": "HIVELOCITY",
    "AS36352": "ColoCrossing",
    "AS19318": "InterServer",
    "AS40160": "Equinix Metal",
    "AS54858": "Server Central",
    "AS64289": "MacStadium",
    "AS199524": "G-Core",
    "AS20454": "SSASN / SECURED SERVERS",
    "AS30633": "Leaseweb",
    "AS60781": "Leaseweb",
    "AS28753": "Leaseweb",
    "AS59253": "Leaseweb",
    "AS13213": "UK2 / iomart",
    "AS202053": "UpCloud",
    "AS63949": "Akamai / Linode",
    "AS63949": "Akamai / Linode",
    "AS63949": "Akamai / Linode",
    "AS63949": "Akamai / Linode",
}

ORG_DC = [
    (r"(?i)latitude", "Latitude.sh"),
    (r"(?i)teraswitch", "TeraSwitch"),
    (r"(?i)allnodes", "Allnodes"),
    (r"(?i)cherry.?servers?|ntt cherryservers", "Cherry Servers"),
    (r"(?i)servers\.?com", "Servers.com"),
    (r"(?i)equinix", "Equinix"),
    (r"(?i)hetzner", "Hetzner"),
    (r"(?i)\bovh\b", "OVH"),
    (r"(?i)digitalocean|digital ocean", "DigitalOcean"),
    (r"(?i)amazon|aws", "AWS"),
    (r"(?i)alibaba", "Alibaba Cloud"),
    (r"(?i)google", "Google"),
    (r"(?i)microsoft|azure", "Microsoft Azure"),
    (r"(?i)vultr|choopa", "Choopa / Vultr"),
    (r"(?i)contabo", "Contabo"),
    (r"(?i)leaseweb", "Leaseweb"),
    (r"(?i)m247", "M247"),
    (r"(?i)datacamp", "Datacamp"),
    (r"(?i)g-?core", "G-Core"),
    (r"(?i)akamai|linode", "Akamai / Linode"),
    (r"(?i)oracle", "Oracle Cloud"),
    (r"(?i)packet", "Equinix Metal"),
    (r"(?i)ionos|1&1", "IONOS"),
    (r"(?i)hivelocity", "HIVELOCITY"),
    (r"(?i)colocrossing", "ColoCrossing"),
    (r"(?i)upcloud", "UpCloud"),
    (r"(?i)server\.?central", "Server Central"),
    (r"(?i)cdn77", "CDN77"),
    (r"(?i)mevspace", "Mevspace"),
    (r"(?i)cloudflare", "Cloudflare"),
    (r"(?i)psychz", "Psychz"),
    (r"(?i)quadranet", "QuadraNet"),
    (r"(?i)softlayer|ibm cloud", "IBM Cloud"),
    (r"(?i)\bipxo\b", "IPXO"),
    (r"(?i)retn", "RETN"),
    (r"(?i)galaxy digital", "Galaxy Digital"),
    (r"(?i)twinstake", "Twinstake"),
    (r"(?i)dedicatednodes", "Dedicatednodes"),
    (r"(?i)butterfly research", "Butterfly Research"),
    (r"(?i)saveincloud", "Saveincloud"),
    (r"(?i)rtm networks", "RTM Networks"),
    (r"(?i)amarutu", "Amarutu"),
    (r"(?i)limestone", "Limestone Networks"),
    (r"(?i)webnx", "WebNX"),
    (r"(?i)c7 data", "C7 Data Centers"),
    (r"(?i)flexential", "Flexential"),
    (r"(?i)23m(?:edia|\.com)?", "23media"),
    (r"(?i)decentra", "Decentra Cloud"),
    (r"(?i)fiberstate", "Fiberstate"),
    (r"(?i)payward|waverly community", "Payward / Kraken"),
    (r"(?i)rockawayx", "RockawayX"),
    (r"(?i)\bvnet\b", "VNET"),
]


def label(g):
    if g.get("status") != "success":
        return "unknown"
    asn = (g.get("as") or "").split()[0] if g.get("as") else ""
    if asn in ASN_DC:
        return ASN_DC[asn]
    text = " ".join(filter(None, [g.get("org"), g.get("isp"), g.get("as")]))
    for pat, name in ORG_DC:
        if re.search(pat, text):
            return name
    org = (g.get("org") or g.get("isp") or g.get("as") or "unknown").strip()
    return org


path = sys.argv[1] if len(sys.argv) > 1 else "backruns_oct8.csv"
rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
ips = sorted({r["leader_ip"] for r in rows if r["leader_ip"]})
geo = {}
for i in range(0, len(ips), 100):
    chunk = ips[i:i + 100]
    body = json.dumps([{"query": ip, "fields": "query,status,country,city,org,isp,as,asname"} for ip in chunk]).encode()
    req = urllib.request.Request("http://ip-api.com/batch", data=body, headers={"Content-Type": "application/json"})
    for g in json.loads(urllib.request.urlopen(req, timeout=60).read()):
        geo[g["query"]] = g

# Place data_center after leader_region.
cols = list(rows[0])
if "data_center" in cols:
    cols.remove("data_center")
cols.insert(cols.index("leader_region") + 1, "data_center")

raw = Counter()
for r in rows:
    g = geo.get(r["leader_ip"], {})
    r["data_center"] = label(g)
    raw[(r["data_center"], g.get("org"), g.get("as"))] += 1

with open(path, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

print("data_center distribution:")
for k, v in Counter(r["data_center"] for r in rows).most_common():
    print(f"  {v:5d}  {k}")
print("\nunmatched orgs (kept raw):")
for (dc, org, asn), c in raw.most_common():
    if dc == org or dc.startswith("AS") or dc not in {x[1] for x in ORG_DC} and dc not in ASN_DC.values():
        if dc not in ("unknown",) and dc == (org or "").strip():
            print(f"  {c:5d}  {dc}  |  {asn}")
