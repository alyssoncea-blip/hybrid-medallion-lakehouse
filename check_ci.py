import yaml, sys, base64, urllib.request, json

headers = {"Accept": "application/vnd.github+json", "User-Agent": "opencode-ci"}
url = "https://api.github.com/repos/alyssoncea-blip/hybrid-medallion-lakehouse/contents/.github/workflows/ci.yml"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.load(resp)
content = base64.b64decode(data["content"]).decode("utf-8")
parsed = yaml.safe_load(content)
jobs = list(parsed["jobs"].keys())
print(f"Jobs ({len(jobs)}): {jobs}")
print(f"Unique: {len(set(jobs)) == len(jobs)}")
if len(set(jobs)) != len(jobs):
    from collections import Counter
    dupes = [k for k,v in Counter(jobs).items() if v > 1]
    print(f"DUPLICATES: {dupes}")