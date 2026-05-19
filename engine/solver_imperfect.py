from typing import Dict
from scipy.optimize import fsolve

def solve_imperfect(p: Dict[str, float], sigma: float = 0.4) -> Dict[str, float]:
    """
    Resuelve el equilibrio numéricamente con Movilidad Imperfecta (BP inclinada).
    Se asume tipo de cambio flexible por defecto para la resolución.
    BP: r = r* + (1/sigma)*NX
    """
    c0 = p["c0"]
    c1 = p["c1"]
    T = p["T"]
    I0 = p["I0"]
    G = p["G"]
    NX0 = p["NX0"]
    b = p["b"]
    x1 = p["x1"]
    k = p["k"]
    h = p["h"]
    M = p["M"]
    r_star = p["r_star"]
    m1 = p["m1"]

    A = c0 - c1*T + I0 + G + NX0
    mult = 1.0 / (1.0 - c1 + m1)

    print(f"[Imperfect] sigma={sigma}, BP_slope={1.0/sigma}")

    def equations(vars):
        Y, r, E = vars
        eq1 = Y - mult * (A + x1*E - b*r)
        eq2 = r - (k*Y - M)/h
        NX = NX0 + x1*E - m1*Y
        eq3 = r - (r_star + (1.0/sigma)*NX)
        return [eq1, eq2, eq3]

    Y_guess = (M + h*r_star)/k
    r_guess = r_star
    E_guess = ((1-c1+m1)*Y_guess + b*r_guess - A) / x1

    try:
        sol = fsolve(equations, [Y_guess, r_guess, E_guess])
        Y_opt, r_opt, E_opt = sol
    except Exception:
        Y_opt, r_opt, E_opt = Y_guess, r_guess, E_guess

    NX = NX0 + x1*E_opt - m1*Y_opt
    C = c0 + c1*(Y_opt - T)
    I_inv = I0 - b*r_opt

    return {
        "Y": round(Y_opt, 6),
        "r": round(r_opt, 6),
        "E_endo": round(E_opt, 6),
        "M": M,
        "NX": round(NX, 6),
        "C": round(C, 6),
        "I_inv": round(I_inv, 6),
        "mult": round(mult, 6),
        "BP_slope": round(1.0/sigma, 6)
    }
