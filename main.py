import json, os, sys, urllib.request, urllib.error

# 0x88 board. Pieces: 1 P 2 N 3 B 4 R 5 Q 6 K (white +, black -); 9 = off-board.
VAL = (0, 100, 320, 330, 500, 900, 20000)
KN = (-33, -31, -18, -14, 14, 18, 31, 33)
KG = (-17, -16, -15, -1, 1, 15, 16, 17)
RO = (-16, -1, 1, 16)
BI = (-17, -15, 15, 17)
# piece-square tables, white perspective, index = rank*8+file, rank 0 = 1st rank
PST = (
 (0, 0, 0, 0, 0, 0, 0, 0, 5, 10, 10, -20, -20, 10, 10, 5, 5, -5, -10, 0, 0, -10, -5, 5, 0, 0, 0, 20, 20, 0, 0, 0, 5, 5, 10, 25, 25, 10, 5, 5, 10, 10, 20, 30, 30, 20, 10, 10, 50, 50, 50, 50, 50, 50, 50, 50, 0, 0, 0, 0, 0, 0, 0, 0),
 (-50, -40, -30, -30, -30, -30, -40, -50, -40, -20, 0, 0, 0, 0, -20, -40, -30, 0, 10, 15, 15, 10, 0, -30, -30, 5, 15, 20, 20, 15, 5, -30, -30, 0, 15, 20, 20, 15, 0, -30, -30, 5, 10, 15, 15, 10, 5, -30, -40, -20, 0, 5, 5, 0, -20, -40, -50, -40, -30, -30, -30, -30, -40, -50),
 (-20, -10, -10, -10, -10, -10, -10, -20, -10, 0, 0, 0, 0, 0, 0, -10, -10, 0, 5, 10, 10, 5, 0, -10, -10, 5, 5, 10, 10, 5, 5, -10, -10, 0, 10, 10, 10, 10, 0, -10, -10, 10, 10, 10, 10, 10, 10, -10, -10, 5, 0, 0, 0, 0, 5, -10, -20, -10, -10, -10, -10, -10, -10, -20),
 (0, 0, 0, 0, 0, 0, 0, 0, 5, 10, 10, 10, 10, 10, 10, 5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, 0, 0, 0, 5, 5, 0, 0, 0),
 (-20, -10, -10, -5, -5, -10, -10, -20, -10, 0, 0, 0, 0, 0, 0, -10, -10, 0, 5, 5, 5, 5, 0, -10, -5, 0, 5, 5, 5, 5, 0, -5, 0, 0, 5, 5, 5, 5, 0, -5, -10, 5, 5, 5, 5, 5, 0, -10, -10, 0, 5, 0, 0, 0, 0, -10, -20, -10, -10, -5, -5, -10, -10, -20),
 (-30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30, -20, -30, -30, -40, -40, -30, -30, -20, -10, -20, -20, -20, -20, -20, -20, -10, 20, 20, 0, 0, 0, 0, 20, 20, 20, 30, 10, 0, 0, 10, 30, 20),
)
MATE = 100000
B = [9] * 128
SIDE = 1
CR = 0
EP = -1
KW = 4
KB = 116
N = 0
BUDGET = 60000
TT = {}
KILL = [[0, 0] for _ in range(64)]


def sqname(s):
    return "abcdefgh"[s & 7] + str((s >> 4) + 1)


def parse(fen):
    global B, SIDE, CR, EP, KW, KB
    B = [0 if not (s & 136) else 9 for s in range(128)]
    parts = fen.split()
    rows = parts[0].split("/")
    for r, row in enumerate(rows):
        rank = 7 - r
        f = 0
        for c in row:
            if c.isdigit():
                f += int(c)
            else:
                p = "PNBRQK".index(c.upper()) + 1
                if c.islower():
                    p = -p
                s = rank * 16 + f
                B[s] = p
                if abs(p) == 6:
                    if p > 0:
                        KW = s
                    else:
                        KB = s
                f += 1
    SIDE = 1 if parts[1] == "w" else -1
    CR = 0
    if len(parts) > 2:
        for c in parts[2]:
            CR |= {"K": 1, "Q": 2, "k": 4, "q": 8}.get(c, 0)
    EP = -1
    if len(parts) > 3 and parts[3] != "-":
        EP = (int(parts[3][1]) - 1) * 16 + (ord(parts[3][0]) - 97)


def attacked(s, by):
    for d in (-1, 1):
        t = s - 16 * by + d
        if not (t & 136) and B[t] == by:
            return True
    for d in KN:
        t = s + d
        if not (t & 136) and B[t] == 2 * by:
            return True
    for d in KG:
        t = s + d
        if not (t & 136) and B[t] == 6 * by:
            return True
    for d in RO:
        t = s
        while True:
            t += d
            if t & 136:
                break
            p = B[t]
            if p:
                if p == 4 * by or p == 5 * by:
                    return True
                break
    for d in BI:
        t = s
        while True:
            t += d
            if t & 136:
                break
            p = B[t]
            if p:
                if p == 3 * by or p == 5 * by:
                    return True
                break
    return False


def gen():
    ms = []
    s = SIDE
    for f in range(128):
        if f & 136:
            continue
        p = B[f]
        if p == 0 or p == 9 or (p > 0) != (s > 0):
            continue
        t = abs(p)
        if t == 1:
            d = 16 * s
            o = f + d
            if not (o & 136) and B[o] == 0:
                if o >> 4 in (0, 7):
                    for q in (5, 4, 3, 2):
                        ms.append(f | (o << 7) | (q << 14))
                else:
                    ms.append(f | (o << 7))
                    if (f >> 4) == (1 if s > 0 else 6) and B[o + d] == 0:
                        ms.append(f | ((o + d) << 7))
            for o in (f + d - 1, f + d + 1):
                if o & 136:
                    continue
                if B[o] != 0 and B[o] != 9 and (B[o] > 0) != (s > 0):
                    if o >> 4 in (0, 7):
                        for q in (5, 4, 3, 2):
                            ms.append(f | (o << 7) | (q << 14))
                    else:
                        ms.append(f | (o << 7))
                elif o == EP and EP >= 0:
                    ms.append(f | (o << 7))
        elif t == 2 or t == 6:
            for d in (KN if t == 2 else KG):
                o = f + d
                if o & 136:
                    continue
                if B[o] == 0 or (B[o] > 0) != (s > 0):
                    ms.append(f | (o << 7))
            if t == 6:
                if s > 0 and f == 4:
                    if (CR & 1) and B[5] == 0 and B[6] == 0 and B[7] == 4 and not attacked(4, -1) and not attacked(5, -1) and not attacked(6, -1):
                        ms.append(4 | (6 << 7))
                    if (CR & 2) and B[3] == 0 and B[2] == 0 and B[1] == 0 and B[0] == 4 and not attacked(4, -1) and not attacked(3, -1) and not attacked(2, -1):
                        ms.append(4 | (2 << 7))
                elif s < 0 and f == 116:
                    if (CR & 4) and B[117] == 0 and B[118] == 0 and B[119] == -4 and not attacked(116, 1) and not attacked(117, 1) and not attacked(118, 1):
                        ms.append(116 | (118 << 7))
                    if (CR & 8) and B[115] == 0 and B[114] == 0 and B[113] == 0 and B[112] == -4 and not attacked(116, 1) and not attacked(115, 1) and not attacked(114, 1):
                        ms.append(116 | (114 << 7))
        else:
            for d in (RO if t == 4 else BI if t == 3 else RO + BI):
                o = f
                while True:
                    o += d
                    if o & 136:
                        break
                    if B[o] == 0:
                        ms.append(f | (o << 7))
                    else:
                        if (B[o] > 0) != (s > 0):
                            ms.append(f | (o << 7))
                        break
    return ms


def make(m):
    global SIDE, CR, EP, KW, KB
    f = m & 127
    t = (m >> 7) & 127
    q = m >> 14
    p = B[f]
    cap = B[t]
    epcap = -1
    if abs(p) == 1 and t == EP and cap == 0:
        epcap = t - 16 * SIDE
        cap = B[epcap]
        B[epcap] = 0
    undo = (m, cap, CR, EP, epcap)
    B[t] = q * SIDE if q else p
    B[f] = 0
    if abs(p) == 6:
        if SIDE > 0:
            KW = t
        else:
            KB = t
        if t - f == 2:
            B[t - 1] = B[t + 1]
            B[t + 1] = 0
        elif f - t == 2:
            B[t + 1] = B[t - 2]
            B[t - 2] = 0
    if f == 4 or t == 4:
        CR &= ~3
    if f == 0 or t == 0:
        CR &= ~2
    if f == 7 or t == 7:
        CR &= ~1
    if f == 116 or t == 116:
        CR &= ~12
    if f == 112 or t == 112:
        CR &= ~8
    if f == 119 or t == 119:
        CR &= ~4
    EP = -1
    if abs(p) == 1 and abs(t - f) == 32:
        EP = (f + t) // 2
    SIDE = -SIDE
    return undo


def unmake(u):
    global SIDE, CR, EP, KW, KB
    m, cap, cr, ep, epcap = u
    f = m & 127
    t = (m >> 7) & 127
    q = m >> 14
    SIDE = -SIDE
    CR = cr
    EP = ep
    p = B[t]
    if abs(p) == 6:
        if SIDE > 0:
            KW = f
        else:
            KB = f
        if t - f == 2:
            B[t + 1] = B[t - 1]
            B[t - 1] = 0
        elif f - t == 2:
            B[t - 2] = B[t + 1]
            B[t + 1] = 0
    B[f] = SIDE if q else p
    B[t] = cap
    if epcap >= 0:
        B[epcap] = -SIDE
        B[t] = 0


def evaluate():
    sc = 0
    wb = 0
    bb = 0
    for s in range(128):
        if s & 136:
            continue
        p = B[s]
        if p == 0 or p == 9:
            continue
        a = abs(p)
        r = s >> 4
        fl = s & 7
        i = r * 8 + fl
        if p > 0:
            sc += VAL[a] + PST[a - 1][i]
            if a == 3:
                wb += 1
        else:
            sc -= VAL[a] + PST[a - 1][(7 - r) * 8 + fl]
            if a == 3:
                bb += 1
    if wb >= 2:
        sc += 30
    if bb >= 2:
        sc -= 30
    return sc if SIDE > 0 else -sc


def order(ms, ttmove, ply):
    k = KILL[ply] if ply < 64 else (0, 0)

    def key(m):
        t = (m >> 7) & 127
        cap = B[t]
        s = 0
        if m == ttmove:
            s = 1000000
        elif cap:
            s = 10000 + VAL[abs(cap)] * 10 - VAL[abs(B[m & 127])] // 10
        elif m == k[0]:
            s = 9000
        elif m == k[1]:
            s = 8000
        return -s
    ms.sort(key=key)
    return ms


class Done(Exception):
    pass


def qsearch(alpha, beta, ply):
    global N
    N += 1
    if N >= BUDGET:
        raise Done
    stand = evaluate()
    if stand >= beta:
        return beta
    if stand > alpha:
        alpha = stand
    for m in order([m for m in gen() if B[(m >> 7) & 127] != 0 or ((m >> 7) & 127) == EP], 0, ply):
        u = make(m)
        ks = KB if SIDE > 0 else KW
        legal = not attacked(ks, SIDE)
        if legal:
            sc = -qsearch(-beta, -alpha, ply + 1)
            unmake(u)
            if sc >= beta:
                return beta
            if sc > alpha:
                alpha = sc
        else:
            unmake(u)
    return alpha


def search(alpha, beta, depth, ply):
    global N
    N += 1
    if N >= BUDGET:
        raise Done
    if depth <= 0:
        return qsearch(alpha, beta, ply)
    key = (tuple(B), SIDE, CR, EP)
    ent = TT.get(key)
    ttmove = 0
    if ent and ent[0] >= depth:
        sc, fl, bm = ent[1], ent[2], ent[3]
        if fl == 0:
            return sc
        if fl == 1 and sc <= alpha:
            return sc
        if fl == 2 and sc >= beta:
            return sc
        ttmove = bm
    best = -MATE
    bestm = 0
    flag = 1
    ms = order(gen(), ttmove, ply)
    legal = 0
    for m in ms:
        u = make(m)
        ks = KB if SIDE > 0 else KW
        if attacked(ks, SIDE):
            unmake(u)
            continue
        legal += 1
        sc = -search(-beta, -alpha, depth - 1, ply + 1)
        unmake(u)
        if sc > best:
            best = sc
            bestm = m
        if sc > alpha:
            alpha = sc
            flag = 0
        if alpha >= beta:
            if B[(m >> 7) & 127] == 0 and ply < 64:
                if KILL[ply][0] != m:
                    KILL[ply][1] = KILL[ply][0]
                    KILL[ply][0] = m
            flag = 2
            break
    if legal == 0:
        ks = KW if SIDE > 0 else KB
        return -MATE + ply if attacked(ks, -SIDE) else 0
    TT[key] = (depth, best, flag, bestm)
    return best


def choose(fen, legal_uci):
    global N, BUDGET
    parse(fen)
    if len(legal_uci) == 1:
        return legal_uci[0]
    pmap = {"q": 5, "r": 4, "b": 3, "n": 2}
    roots = []
    for u in legal_uci:
        f = (int(u[1]) - 1) * 16 + (ord(u[0]) - 97)
        t = (int(u[3]) - 1) * 16 + (ord(u[2]) - 97)
        q = pmap.get(u[4], 0) if len(u) > 4 else 0
        roots.append(f | (t << 7) | (q << 14))
    N = 0
    TT.clear()
    best = roots[0]
    for depth in range(1, 12):
        try:
            alpha = -MATE
            beta = MATE
            cur = best
            curbest = -MATE
            for m in order(roots, best, 0):
                u = make(m)
                sc = -search(-beta, -alpha, depth - 1, 0)
                unmake(u)
                if sc > curbest:
                    curbest = sc
                    cur = m
                if sc > alpha:
                    alpha = sc
            best = cur
        except Done:
            break
        if N >= BUDGET:
            break
    return sqname(best & 127) + sqname((best >> 7) & 127) + ("nbrq"[(best >> 14) - 2] if best >> 14 else "")


U = os.environ.get("MAKEFUN_ENV_URL", "")


def post(path, body):
    req = urllib.request.Request(
        U + path,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"{path}: HTTP {e.code}")


if __name__ == "__main__":
    while True:
        g = post("/game", {})
        if g["status"] == "done":
            break
        while g["status"] == "your_move":
            g = post("/move", {"game": g["game"], "move": choose(g["fen"], g["legal_moves"])})
        print(f"game {g['game']}: {g['outcome']} by {g['reason']}", file=sys.stderr)
    print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)
