import streamlit as st
import pandas as pd
from config.dynamics import DYNAMICS_PARAMS
from config.scoring import calc_period_score
from engine.solver_fixed import solve_fixed
from engine.solver_flexible import solve_flexible
from engine.solver_imperfect import solve_imperfect

class SimStateManager:
    def __init__(self):
        if "sim_state" not in st.session_state:
            st.session_state["sim_state"] = {
                "t": 0,
                "regime": None,
                "history": [],
                "params_t0": None,
                "status": "init"
            }
        self.state = st.session_state["sim_state"]

    @property
    def t(self): return self.state["t"]

    @property
    def status(self): return self.state["status"]

    def calibrate(self, t0_params: dict):
        self.state["params_t0"] = t0_params.copy()
        self.state["t"] = 0
        self.state["status"] = "calibrated"
        self.state["history"] = []

    def start_simulation(self, regime: str):
        if self.state["t"] == 0 and self.state["status"] == "calibrated":
            self.state["regime"] = regime
            self.state["t"] = 1
            self.state["status"] = "running"
            self.step_forward({}, None, init_t=True)

    def step_forward(self, policy_changes: dict, shock_key: str = None, init_t: bool = False):
        if not init_t:
            if self.state["t"] >= 10:
                return
            self.state["t"] += 1

        t = self.state["t"]
        regime = self.state["regime"]

        if t == 1:
            params = self.state["params_t0"].copy()
        else:
            params = self.state["history"][-1]["params"].copy()

        for k, v in policy_changes.items():
            if k in params:
                params[k] = v

        from config.shocks_engine import apply_shocks_for_period
        params = apply_shocks_for_period(params, t, shock_key)

        if regime == "🏛️ TC Fijo":
            eq = solve_fixed(params)
            E_val = params["E"]
            M_val = eq["M_endo"]
        elif regime == "🌊 TC Flexible":
            eq = solve_flexible(params)
            E_val = eq["E_endo"]
            M_val = params["M"]
        else:
            eq = solve_imperfect(params, DYNAMICS_PARAMS["sigma_mobility"])
            E_val = eq.get("E_endo", params.get("E", 0))
            M_val = params["M"]

        Y = eq["Y"]
        r = eq["r"]

        Y_pot = DYNAMICS_PARAMS["Y_pot"]
        U_n = DYNAMICS_PARAMS["U_n"]

        if t == 1:
            gY = 0.0
        else:
            prev_Y = self.state["history"][-1]["Y"]
            gY = (Y - prev_Y) / max(prev_Y, 1e-6)

        U_t = max(0, U_n - DYNAMICS_PARAMS["gamma_okun"] * gY)
        pi_t = DYNAMICS_PARAMS["pi_0"] + DYNAMICS_PARAMS["alpha_inflation"] * gY

        # 🔵 ACOTAMIENTO LÓGICO (evita valores imposibles por shocks extremos)
        pi_t = max(-0.10, min(0.50, pi_t))  # Inflación entre -10% y 50%
        U_t  = max(0.01, min(0.99, U_t))    # Desempleo entre 1% y 99%

        T_val = params.get("T", 20)
        G_val = params.get("G", 20)
        def_pct = (G_val - T_val) / max(Y, 1e-6)

        if t == 1:
            R_t = DYNAMICS_PARAMS["R_0"]
            B_t = DYNAMICS_PARAMS["B_0"]
        else:
            prev = self.state["history"][-1]
            if regime == "🏛️ TC Fijo":
                NX = params["NX0"] + params["x1"] * E_val - params["m1"] * Y
                R_t = prev["R"] + NX
                print(f"[TC Fijo] t={t}, NX={NX:.2f}, Delta_R={NX:.2f}, R_t={R_t:.2f}")
            else:
                R_t = prev["R"]
            prev_B = prev["B"]
            B_t = prev_B * (1 + params.get("r_star", 5)/100) + (G_val - T_val)

        # Score con circuito de crisis
        score_t = calc_period_score(gY, U_t, pi_t, def_pct, R_t)

        self.state["history"].append({
            "t": t,
            "Y": round(Y, 4),
            "r": round(r, 4),
            "E": round(E_val, 4),
            "M": round(M_val, 4),
            "R": round(R_t, 4),
            "B": round(B_t, 1),
            "pi": round(pi_t, 4),
            "U": round(U_t, 4),
            "gY": round(gY, 2),
            "def": round(def_pct, 2),
            "score": score_t,
            "policy": str(policy_changes) if policy_changes else "Ninguna",
            "shock": shock_key if shock_key else "Ninguno",
            "params": params,
            "eq": eq
        })

    def get_history_df(self):
        if not self.state["history"]:
            return pd.DataFrame()

        data = []
        for h in self.state["history"]:
            data.append({
                "t": h["t"],
                "Y": h["Y"],
                "r": h["r"],
                "E/M": f"E={h['E']} / M={h['M']}",
                "R": h["R"],
                "B": h["B"],
                "pi": h["pi"],
                "U": h["U"],
                "score": h["score"],
                "policy": h["policy"],
                "shock": h["shock"]
            })
        return pd.DataFrame(data)

    def reset_to_calibration(self):
        self.state["t"] = 0
        self.state["status"] = "calibrated" if self.state["params_t0"] else "init"
        self.state["history"] = []
