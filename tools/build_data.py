"""Build a compact Tokyo-area rail graph from MLIT station data.

Times are ESTIMATES: distance-based (avg ~38 km/h incl. stops) + dwell,
transfers 4 min within same-name station groups, walking links for nearby stations.
"""
import json, math, sys
from collections import defaultdict
import pykakasi

src = sys.argv[1]
out = sys.argv[2]
stations = json.load(open(f"{src}/stations.json"))

def inbox(x):
    return 35.1 < x["lat"] < 36.2 and 138.9 < x["lng"] < 140.5

BAD = ("新幹線", "ケーブル", "ロープウェ", "鋼索")
stations = [x for x in stations if inbox(x) and not any(b in x["line"] for b in BAD)]

def km(a, b):
    R = 6371
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(d))

# platform nodes: (line, name)
nodes = []
idx = {}
for x in stations:
    key = (x["line"], x["name"])
    if key in idx:
        continue
    idx[key] = len(nodes)
    nodes.append({"name": x["name"], "line": x["line"], "op": x["operator"], "lat": x["lat"], "lng": x["lng"]})

byline = defaultdict(list)
for i, n in enumerate(nodes):
    byline[n["line"]].append(i)

edges = {}  # (a,b) -> (minutes, km, opIndex or -1 for transfer/walk)
ops = sorted(set(n["op"] for n in nodes))
opi = {o: i for i, o in enumerate(ops)}

def add(a, b, t, d, o):
    k = (min(a, b), max(a, b))
    if k not in edges or edges[k][0] > t:
        edges[k] = (t, d, o)

def speed(op):
    if "旅客鉄道" in op: return 68
    if op in ("東京地下鉄", "東京都", "横浜市"): return 33
    if "モノレール" in op or "新交通" in op or "ゆりかもめ" in op: return 30
    return 48

LOOPS = {"大江戸線", "山手線"}
for line, ids in byline.items():
    if len(ids) < 2:
        continue
    # Prim MST over stations of the line
    pts = [(nodes[i]["lat"], nodes[i]["lng"]) for i in ids]
    n = len(ids)
    intree = [False]*n; best = [1e9]*n; par = [-1]*n; best[0] = 0
    deg = [0]*n
    for _ in range(n):
        u = min((i for i in range(n) if not intree[i]), key=lambda i: best[i])
        intree[u] = True
        if par[u] >= 0:
            d = km(pts[u], pts[par[u]])
            if d < 12:
                t = d / speed(nodes[ids[u]]["op"]) * 60 + 0.5
                add(ids[u], ids[par[u]], t, d, opi[nodes[ids[u]]["op"]])
                deg[u] += 1; deg[par[u]] += 1
        for v in range(n):
            if not intree[v]:
                d = km(pts[u], pts[v])
                if d < best[v]:
                    best[v] = d; par[v] = u
    if any(l in line for l in LOOPS):
        leaves = [i for i in range(n) if deg[i] == 1]
        if len(leaves) == 2:
            d = km(pts[leaves[0]], pts[leaves[1]])
            if d < 4:
                add(ids[leaves[0]], ids[leaves[1]], d/speed(nodes[ids[leaves[0]]]["op"])*60+0.5, d, opi[nodes[ids[leaves[0]]]["op"]])

# transfers & walking links
grid = defaultdict(list)
for i, n in enumerate(nodes):
    grid[(round(n["lat"]*100), round(n["lng"]*100))].append(i)
for i, n in enumerate(nodes):
    gx, gy = round(n["lat"]*100), round(n["lng"]*100)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for j in grid[(gx+dx, gy+dy)]:
                if j <= i:
                    continue
                m = nodes[j]
                if m["line"] == n["line"]:
                    continue
                d = km((n["lat"], n["lng"]), (m["lat"], m["lng"]))
                if m["name"] == n["name"] and d < 0.8:
                    add(i, j, 4.0, 0, -1)
                elif d < 0.35:
                    add(i, j, 3 + d*1000/80, 0, -1)

# station groups (what users pick): same name within 1 km
groups = []
gid = [-1]*len(nodes)
for i, n in enumerate(nodes):
    if gid[i] >= 0:
        continue
    g = len(groups)
    members = [i]
    gid[i] = g
    for j in range(i+1, len(nodes)):
        if gid[j] < 0 and nodes[j]["name"] == n["name"] and km((n["lat"], n["lng"]), (nodes[j]["lat"], nodes[j]["lng"])) < 1.0:
            gid[j] = g; members.append(j)
    groups.append(members)

kks = pykakasi.kakasi()
def romaji(s):
    r = "".join(x["hepburn"] for x in kks.convert(s))
    for a, b in (("ou", "o"), ("oo", "o"), ("uu", "u")):
        r = r.replace(a, b)
    return r[:1].upper() + r[1:]

lines_used = sorted(set(n["line"] for n in nodes))
li = {l: i for i, l in enumerate(lines_used)}
G = []
for g, members in enumerate(groups):
    n = nodes[members[0]]
    lat = sum(nodes[m]["lat"] for m in members)/len(members)
    lng = sum(nodes[m]["lng"] for m in members)/len(members)
    G.append([n["name"], romaji(n["name"]), round(lat, 5), round(lng, 5), sorted(set(li[nodes[m]["line"]] for m in members))])

data = {
    "note": "Estimated times from MLIT station locations (国土数値情報 N02). Not timetable-accurate.",
    "ops": ops,
    "lines": lines_used,
    "groups": G,
    "nodeGroup": gid,
    "nodeLine": [li[n["line"]] for n in nodes],
    "edges": [[a, b, round(t, 1), round(d, 2), o] for (a, b), (t, d, o) in edges.items()],
}
json.dump(data, open(out, "w"), ensure_ascii=False, separators=(",", ":"))
print("nodes", len(nodes), "groups", len(groups), "edges", len(edges), "lines", len(lines_used))
