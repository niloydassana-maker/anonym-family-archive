import os, json, time, urllib.request
KEY = os.environ.get("NVIDIA_API_KEY","").strip()
if not KEY:
    try:
        j=json.load(open(r"C:\Users\Admin\.config\crush\crush.json"))
        KEY=j["providers"]["nvidiafree"]["api_key"]
    except Exception as e:
        print("NO_KEY", e); raise SystemExit(1)
BASE="https://integrate.api.nvidia.com/v1/chat/completions"
IMG="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
CANDIDATES=[
 "meta/llama-3.2-11b-vision-instruct",
 "meta/llama-3.2-90b-vision-instruct",
 "microsoft/phi-3-vision-128k-instruct",
 "microsoft/kosmos-2",
 "nvidia/neva-22b",
 "nvidia/vila",
 "adept/fuyu-8b",
 "moonshotai/kimi-k3",
 "deepseek-ai/deepseek-v4.1-flash",
 "google/gemma-3-12b-it",
 "google/gemma-3-4b-it",
 "z-ai/glm-5.3-flash",
 "z-ai/glm-5.3",
 "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
 "nvidia/nemotron-3.5-lightning-30b-a3b",
 "nvidia/nemotron-3-super-120b-a12b",
 "nvidia/nemotron-3-ultra-550b-a55b",
]
def call(model, messages, max_tokens=20, timeout=120):
    body=json.dumps({"model":model,"messages":messages,"max_tokens":max_tokens,"temperature":0}).encode()
    req=urllib.request.Request(BASE, data=body, headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json"}, method="POST")
    t0=time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j=json.load(r)
        dt=(time.time()-t0)*1000
        txt=j["choices"][0]["message"]["content"]
        return True, dt, txt[:200].replace("\n"," ")
    except Exception as e:
        dt=(time.time()-t0)*1000
        return False, dt, (type(e).__name__+": "+str(e))[:200]
print("MODEL | TEXT | VISION", flush=True)
results=[]
for m in CANDIDATES:
    ok1,ms1,t1=call(m,[{"role":"user","content":"reply with the single word PONG"}], max_tokens=5, timeout=120)
    msgs=[{"role":"user","content":[
        {"type":"text","text":"What color is this pixel? Reply one word."},
        {"type":"image_url","image_url":{"url":"data:image/png;base64,"+IMG}}]}]
    ok2,ms2,t2=call(m,msgs,max_tokens=20,timeout=120)
    print(f"{m} | TEXT ok={ok1} {ms1:.0f}ms [{t1[:60]}] | VIS ok={ok2} {ms2:.0f}ms [{t2[:80]}]", flush=True)
    results.append({"model":m,"text_ok":ok1,"text_ms":round(ms1),"text":t1,"vis_ok":ok2,"vis_ms":round(ms2),"vis":t2})
    open(r"D:\anonym\delivery\kilo-bridge-setup\bench-nvidia-vision.json","w").write(json.dumps(results,indent=1))
print("SAVED bench-nvidia-vision.json")
