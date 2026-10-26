"""Turn-based challenge PvP with expiring challenges and transactional settlement."""
import random
import time

STAKE = 1000
CHALLENGE_TTL = 300

class DuelSystem:
    def __init__(self, db):
        self.db = db
        with db.connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS duels(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                stake INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                finished_at INTEGER,
                winner_id INTEGER,
                loser_id INTEGER,
                UNIQUE(id)
            )""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_duels_target_status ON duels(target_id,status,created_at)")
    def challenge(self, challenger_vk, target_vk):
        challenger_vk, target_vk = int(challenger_vk), int(target_vk)
        if challenger_vk == target_vk:
            return "❌ Нельзя вызвать на дуэль самого себя."
        now = int(time.time())
        with self.db.connect() as c:
            players = c.execute("SELECT vk_id,balance,level,banned FROM users WHERE vk_id IN (?,?)",(challenger_vk,target_vk)).fetchall()
            by_id = {int(r["vk_id"]):r for r in players}
            if challenger_vk not in by_id or target_vk not in by_id:
                return "❌ Один из игроков не найден. Сначала оба должны запустить бота."
            if by_id[challenger_vk]["banned"] or by_id[target_vk]["banned"]:
                return "❌ Дуэль недоступна для заблокированного игрока."
            if int(by_id[challenger_vk]["balance"]) < STAKE or int(by_id[target_vk]["balance"]) < STAKE:
                return f"❌ Для дуэли у обоих должно быть минимум {STAKE:,}$.".replace(",", " ")
            pending = c.execute("SELECT 1 FROM duels WHERE challenger_id=? AND target_id=? AND status='pending' AND created_at>?",(challenger_vk,target_vk,now-CHALLENGE_TTL)).fetchone()
            if pending:
                return "⏳ У тебя уже есть ожидающий вызов этому игроку."
            cur=c.execute("INSERT INTO duels(challenger_id,target_id,stake,created_at) VALUES(?,?,?,?)",(challenger_vk,target_vk,STAKE,now))
            return f"⚔️ Вызов на дуэль отправлен игроку {target_vk}. ID дуэли: {cur.lastrowid}. Ставка: {STAKE:,}$ с каждого. Принять: /duel accept {cur.lastrowid}".replace(",", " ")
    def accept(self, target_vk, duel_id):
        target_vk, duel_id = int(target_vk), int(duel_id)
        now=int(time.time())
        with self.db.connect() as c:
            duel=c.execute("SELECT * FROM duels WHERE id=?",(duel_id,)).fetchone()
            if not duel or duel["status"]!="pending":
                return "❌ Дуэль не найдена или уже завершена."
            if int(duel["target_id"]) != target_vk:
                return "⛔ Принять этот вызов может только приглашённый игрок."
            if now-int(duel["created_at"])>CHALLENGE_TTL:
                c.execute("UPDATE duels SET status='expired',finished_at=? WHERE id=? AND status='pending'",(now,duel_id))
                return "⌛ Время вызова истекло."
            rows=c.execute("SELECT vk_id,balance,level,banned FROM users WHERE vk_id IN (?,?)",(duel["challenger_id"],duel["target_id"])).fetchall()
            by_id={int(r["vk_id"]):r for r in rows}
            if len(by_id)!=2 or any(int(r["banned"]) for r in by_id.values()):
                c.execute("UPDATE duels SET status='cancelled',finished_at=? WHERE id=?",(now,duel_id))
                return "❌ Дуэль отменена: игрок недоступен."
            stake=int(duel["stake"])
            if any(int(r["balance"])<stake for r in by_id.values()):
                c.execute("UPDATE duels SET status='cancelled',finished_at=? WHERE id=?",(now,duel_id))
                return "❌ Дуэль отменена: у одного из игроков больше нет нужной суммы."
            # Claim the pending duel before touching balances. This prevents two
            # simultaneous accept requests from settling the same stake twice.
            c.execute("UPDATE duels SET status='settling' WHERE id=? AND status='pending'", (duel_id,))
            if c.execute("SELECT changes()").fetchone()[0] != 1:
                return "❌ Дуэль не найдена или уже обрабатывается."
            a=by_id[int(duel["challenger_id"])]
            b=by_id[int(duel["target_id"])]
            score_a=int(a["level"])*10+random.randint(1,100)
            score_b=int(b["level"])*10+random.randint(1,100)
            winner,loser=(int(a["vk_id"]),int(b["vk_id"])) if score_a>=score_b else (int(b["vk_id"]),int(a["vk_id"]))
            # Balance changes and the final status are committed in one transaction.
            c.execute("UPDATE users SET balance=balance-? WHERE vk_id=? AND balance>=?",(stake,loser,stake))
            if c.execute("SELECT changes()").fetchone()[0]!=1:
                c.execute("UPDATE duels SET status='cancelled',finished_at=? WHERE id=? AND status='settling'",(now,duel_id))
                return "❌ Дуэль отменена: баланс изменился."
            c.execute("UPDATE users SET balance=balance+? WHERE vk_id=?",(stake,winner))
            c.execute("UPDATE duels SET status='finished',finished_at=?,winner_id=?,loser_id=? WHERE id=? AND status='settling'",(now,winner,loser,duel_id))
            if c.execute("SELECT changes()").fetchone()[0] != 1:
                raise RuntimeError("Duel settlement state changed unexpectedly")
            return f"🏆 Дуэль завершена! Победитель: {winner}. Проигравший: {loser}. Передано: {stake:,}$.".replace(",", " ")
