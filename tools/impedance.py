"""2D field solver for the board's outer-layer lines (finite differences, Laplace).

  python3 tools/impedance.py        (needs numpy and scipy)

Stack-up JLC04161H-7628 (JLCPCB 4 layers, 1.6 mm): L1 copper 0.035 mm over 0.2104 mm
of 7628 prepreg (er 4.4) above the L2 ground plane. Solder mask 0.015 mm, er 3.8.
Prints single-ended and differential (edge-coupled) impedances; the differential one
is twice the odd-mode impedance, computed as 1 / (c * sqrt(C * C_air)).
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl

D = 0.005                        # grid step, mm
H, T, ER = 0.2104, 0.035, 4.4    # prepreg, copper, prepreg permittivity
TM, ERM = 0.015, 3.8             # solder mask
C0 = 299792458.0
E0 = 8.8541878128e-12


def solve(w, s=None, mask=True, air=False):
    nx, ny = int(round(4.0 / D)), int(round(1.5 / D))
    jh, jt = int(round(H / D)), int(round((H + T) / D))
    xc = nx // 2
    wi = int(round(w / D))
    if s is None:
        spans = [(xc - wi // 2, xc - wi // 2 + wi, 1.0)]
    else:
        si = int(round(s / D))
        a = xc - si // 2
        spans = [(a - wi, a, 1.0), (a + si, a + si + wi, -1.0)]
    # cell permittivity (cells between nodes), rows 0..ny-1, cols 0..nx-1
    eps = np.ones((ny, nx))
    if not air:
        eps[:jh, :] = ER
        if mask:
            m = int(round(TM / D))
            eps[jh:jh + m, :] = ERM
            for x0, x1, _ in spans:
                eps[jh:jt + m, max(x0 - m, 0):x1 + m] = ERM
    # node potentials fixed: plane row 0 and outer box = 0, traces = ±1
    fixed = np.zeros((ny + 1, nx + 1), bool)
    val = np.zeros((ny + 1, nx + 1))
    fixed[0, :] = fixed[-1, :] = True
    fixed[:, 0] = fixed[:, -1] = True
    for x0, x1, v in spans:
        fixed[jh:jt + 1, x0:x1 + 1] = True
        val[jh:jt + 1, x0:x1 + 1] = v
    idx = -np.ones(fixed.shape, int)
    free = np.argwhere(~fixed)
    idx[~fixed] = np.arange(len(free))

    def edge(j, i, dj, di):          # permittivity of the edge from node (j,i) to its neighbour
        if dj:                        # vertical edge inside cell row min(j, j+dj)
            r = min(j, j + dj)
            return 0.5 * (eps[r, max(i - 1, 0)] + eps[r, min(i, nx - 1)])
        c = min(i, i + di)
        return 0.5 * (eps[max(j - 1, 0), c] + eps[min(j, ny - 1), c])

    rows, cols, data = [], [], []
    b = np.zeros(len(free))
    for k, (j, i) in enumerate(free):
        diag = 0.0
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            e = edge(j, i, dj, di)
            diag += e
            jj, ii = j + dj, i + di
            if fixed[jj, ii]:
                b[k] += e * val[jj, ii]
            else:
                rows.append(k); cols.append(idx[jj, ii]); data.append(-e)
        rows.append(k); cols.append(k); data.append(diag)
    A = sp.csr_matrix((data, (rows, cols)), shape=(len(free), len(free)))
    V = val.copy()
    V[~fixed] = spl.spsolve(A, b)
    # charge on the +1 conductor: flux through the edges leaving it
    x0, x1, _ = spans[0]
    q = 0.0
    for j in range(jh, jt + 1):
        for i in range(x0, x1 + 1):
            for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                jj, ii = j + dj, i + di
                if not (jh <= jj <= jt and x0 <= ii <= x1):
                    q += edge(j, i, dj, di) * (1.0 - V[jj, ii])
    return q * E0                    # F/m (grid step cancels in 2D)


def z(w, s=None, mask=True):
    c, ca = solve(w, s, mask), solve(w, s, mask, air=True)
    zz = 1.0 / (C0 * np.sqrt(c * ca))
    return zz * 2 if s is not None else zz, c / ca


if __name__ == "__main__":
    print("single-ended (check, 50 ohm expected near w 0.35 mm):")
    for w in (0.30, 0.35, 0.40):
        print(f"  w {w:.2f}: {z(w)[0]:5.1f} ohm (mask), {z(w, mask=False)[0]:5.1f} ohm (no mask)")
    print("differential, edge-coupled on L1 over L2:")
    for w, s in ((0.20, 0.10), (0.18, 0.10), (0.16, 0.10), (0.20, 0.15), (0.18, 0.15), (0.20, 0.20)):
        print(f"  w {w:.2f} gap {s:.2f}: {z(w, s)[0]:5.1f} ohm (mask), {z(w, s, mask=False)[0]:5.1f} ohm (no mask)")
