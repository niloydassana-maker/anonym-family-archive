import json, urllib.request, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
u = ("https://www.naukri.com/jobapi/v3/search?noOfResults=20&urlType=search_by_key_loc"
     "&searchType=adv&keyword=genai%20engineer&pageNo=1&location=India")
req = urllib.request.Request(u, headers={"appid":"109","systemid":"Naukri",
    "Accept":"application/json","User-Agent":"Mozilla/5.0"})
try:
    d = json.loads(urllib.request.urlopen(req, timeout=35).read().decode())
    print("API OK  total found:", d.get("jobSearchCount",{}).get("jobSearchCount"))
    for j in d.get("jobDetails",[])[:8]:
        print("  %-46s | %-24s | %s | id=%s" % (j.get("title","")[:46], j.get("companyName","")[:24],
              str(j.get("experience",""))[:18], j.get("jobId")))
except Exception as e:
    print("API FAIL:", type(e).__name__, str(e)[:200])
