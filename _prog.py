import sqlite3
c = sqlite3.connect("file:leads.db?mode=ro", uri=True)
tot, alive, dead, pend = c.execute(
    "SELECT COUNT(*), SUM(alive=1), SUM(alive=0), SUM(alive IS NULL OR alive=-1) FROM wa_seed").fetchone()
print("SEED total=%s alive=%s dead=%s pending=%s  (%.1f%% alive of probed)" %
      (tot, alive, dead, pend, (100.0 * (alive or 0) / max(1, (alive or 0) + (dead or 0)))))
print("ALIVE rows carrying a phone:",
      c.execute("SELECT COUNT(*) FROM wa_seed WHERE alive=1 AND COALESCE(phones,'')<>''").fetchone()[0])
print("ALIVE India hosts:",
      c.execute("SELECT COUNT(DISTINCT host) FROM wa_seed WHERE alive=1").fetchone()[0])
