# FATHER-VOICE MODEL CARD — 16.09.2026 03:15 IST (fidelity law, Baba: "father likes precision and fidelity")

| artifact | dtype | size | role |
|---|---|---|---|
| D:\anonym\kilo-models\father_last.pth | float32 (426 keys) | 1,764,210,731 B | **MASTER / canonical inference weight** — every final render, ear-test and archive copy loads THIS |
| D:\anonym\kilo-models\ds\father_last_fp16.pth | float16 (426 keys) | 882,169,755 B | derivative — Kaggle dataset working copy + latency bench only |

Laws:
1. FIDELITY FIRST: inference for the father's voice runs half=False on fp32 unless a measured, ear-approved test says otherwise. FP16 may never be the silent default.
2. MEASURE, DON'T ASSUME: every pipeline change re-runs the A/B sentence set through both weights; father's ear (90% gate, Sunday-Monday) is the judge of fidelity, compute is only the judge of latency.
3. COLD COPY: master hash below; re-checksum after any disk touch; dataset copy is disposable, master is not.
4. CPML: the voice itself is non-commercial (deva-locked); the *pipeline* may be sold once income rules say so; the voice demo stays family.

Training provenance: v15 deva-locked run finished 13.09 22:33 IST (model pulled 23:29 IST by dl.py); training ran fp16-mixed; v16 = continue-train the fp32 master, full precision at the ear end.

SHA-256 (recorded 16.09 03:16 IST):
- father_last.pth ......... see MODEL-CARD-HASH.txt
- father_last_fp16.pth .... see MODEL-CARD-HASH.txt
