# ============================================================
# Horta Comunitária Solar - Neighborhood Action Dashboard
# Global Solution 2026.2 - SERS (Energias Renováveis)
# Aluno: Rafael Meirelles Alves Ferreira - RM574688 - 1CCPB
#
# Como rodar:
#   pip install -r requirements.txt
#   streamlit run app.py
# ============================================================

import random
import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# 1) PREMISSAS (todas as fontes estão no README)
# ------------------------------------------------------------
AREA_M2 = 200            # área da horta (m²)
LAMINA_L_M2 = 5          # necessidade de água (L/m² por dia)
AGUA_DIA_L = AREA_M2 * LAMINA_L_M2   # 1000 L/dia

TARIFA = 1.00            # R$/kWh (Enel SP com impostos, aprox.)
MINIMO_KWH = 30          # custo de disponibilidade monofásico (kWh/mês)
FATOR_CO2 = 0.0385       # kg CO2 por kWh (MCTI, SIN 2023)
HSP = 4.5                # horas de sol pleno em São Paulo
RENDIMENTO = 0.75        # perdas do sistema solar (75% aproveitado)
DIAS = 30                # período de referência: 1 mês

# Alternativa A: convencional (rede elétrica + timer fixo)
# Preços: média de 2 lojas quando encontrado (ver README, seção 3)
A = {
    "nome": "A - Rede elétrica + timer",
    "potencia_w": 370,         # bomba periférica 1/2 cv
    "horas_dia": 1.0,          # timer liga 1 h todo dia
    "vazao_l_h": 1500,
    "custos": {
        "Bomba periférica 1/2 cv": 157.40,
        "Timer digital de tomada": 37.99,
        "Microaspersores + mangueira": 183.58,
        "Padrão de entrada monofásico (ligação nova)": 1926.30,
    },
}

# Alternativa B: solar off-grid + sensor de umidade + gotejamento
B = {
    "nome": "B - Solar + sensor (ESP32)",
    "potencia_w": 80,          # bomba DC 12 V 80 W (5,5 L/min)
    "vazao_l_h": 330,
    "controle_w": 1.0,         # ESP32 + sensores ligados 24 h
    "painel_w": 155,
    "custos": {
        "Painel solar 155 W": 412.42,
        "Controlador de carga PWM 20 A": 157.19,
        "Bateria estacionária 12 V 70 Ah": 625.40,
        "Bomba DC 12 V 80 W": 189.00,
        "ESP32": 48.34,
        "Sensores (umidade do solo, BME280) e relé": 120.00,
        "Gotejamento (fita, mangueira, conectores)": 457.26,
        "Cabos e suporte do painel": 150.00,
    },
}
A["custo_instalacao"] = round(sum(A["custos"].values()), 2)
B["custo_instalacao"] = round(sum(B["custos"].values()), 2)


# ------------------------------------------------------------
# 2) CÁLCULOS DE ENERGIA:  E (kWh) = P (W) x t (h) / 1000
# ------------------------------------------------------------
def energia_kwh(potencia_w, horas):
    return potencia_w * horas / 1000


# Simulação de 30 dias de clima (dados simulados)
# Em dia de chuva o sensor de umidade detecta solo úmido e a bomba B não liga.
random.seed(42)
dias = []
for d in range(1, DIAS + 1):
    choveu = random.random() < 0.30          # ~30% dos dias com chuva
    umidade = random.randint(60, 85) if choveu else random.randint(20, 45)

    # Alternativa A: timer fixo, liga sempre
    horas_a = A["horas_dia"]
    agua_a = horas_a * A["vazao_l_h"]

    # Alternativa B: só liga se o solo estiver seco (umidade < 50%)
    horas_b = AGUA_DIA_L / B["vazao_l_h"] if umidade < 50 else 0
    agua_b = horas_b * B["vazao_l_h"]

    dias.append({
        "dia": d,
        "chuva": "sim" if choveu else "não",
        "umidade_solo_%": umidade,
        "kWh_A": energia_kwh(A["potencia_w"], horas_a),
        "kWh_B": energia_kwh(B["potencia_w"], horas_b) + energia_kwh(B["controle_w"], 24),
        "agua_A_L": agua_a,
        "agua_B_L": agua_b,
        "horas_bomba_B": horas_b,
    })

df = pd.DataFrame(dias)

# Totais do mês
kwh_a = df["kWh_A"].sum()
kwh_b = df["kWh_B"].sum()
agua_a = df["agua_A_L"].sum()
agua_b = df["agua_B_L"].sum()

# Custo mensal: A paga no mínimo 30 kWh; B não paga energia (é off-grid)
custo_mes_a = max(kwh_a, MINIMO_KWH) * TARIFA
custo_mes_b = 0.0

# Dimensionamento solar (pior caso: bomba todo dia)
consumo_max_wh = B["potencia_w"] * (AGUA_DIA_L / B["vazao_l_h"]) + B["controle_w"] * 24
painel_min_w = consumo_max_wh / (HSP * RENDIMENTO)
geracao_mes_kwh = B["painel_w"] * HSP * RENDIMENTO * DIAS / 1000

# ------------------------------------------------------------
# 3) INDICADORES
# ------------------------------------------------------------
economia_kwh = kwh_a - 0              # energia da rede que deixa de ser usada
economia_rs = custo_mes_a - custo_mes_b
co2_evitado_ano = kwh_a * 12 * FATOR_CO2
agua_economizada = agua_a - agua_b
renovavel_pct = 100.0                 # B usa só energia solar

# ------------------------------------------------------------
# 4) DASHBOARD
# ------------------------------------------------------------
st.set_page_config(page_title="Horta Solar - Dashboard", layout="wide")
st.title("🌱 Horta Comunitária Solar")
st.caption("Neighborhood Action Dashboard · GS 2026.2 · SERS · "
           "Valores são projeções baseadas nas premissas (dados simulados).")

st.subheader("Indicadores (Alternativa B vs A, por mês)")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Energia da rede evitada", f"{economia_kwh:.1f} kWh/mês")
c2.metric("Economia na conta", f"R$ {economia_rs:.2f}/mês")
c3.metric("Energia renovável", f"{renovavel_pct:.0f} %")
c4.metric("Água economizada", f"{agua_economizada/1000:.1f} m³/mês")
c5.metric("CO₂ evitado", f"{co2_evitado_ano:.1f} kg/ano")

st.subheader("Comparação das alternativas (mesmo mês, mesma horta)")
tabela = pd.DataFrame({
    "Alternativa": [A["nome"], B["nome"]],
    "Consumo (kWh/mês)": [round(kwh_a, 1), round(kwh_b, 1)],
    "Energia da rede (kWh/mês)": [round(kwh_a, 1), 0],
    "Custo energia (R$/mês)": [round(custo_mes_a, 2), custo_mes_b],
    "Água usada (L/mês)": [int(agua_a), int(agua_b)],
    "Instalação (R$)": [A["custo_instalacao"], B["custo_instalacao"]],
})
st.dataframe(tabela, hide_index=True, width="stretch")

col_esq, col_dir = st.columns(2)
with col_esq:
    st.markdown("**Consumo de energia por dia (kWh)**")
    st.line_chart(df.set_index("dia")[["kWh_A", "kWh_B"]])
with col_dir:
    st.markdown("**Água usada por dia (L)**")
    st.bar_chart(df.set_index("dia")[["agua_A_L", "agua_B_L"]], stack=False)

# Custo acumulado em 5 anos (instalação + energia)
st.subheader("Custo acumulado em 5 anos (R$)")
meses = list(range(0, 61))
acumulado = pd.DataFrame({
    "mês": meses,
    "A - Rede": [A["custo_instalacao"] + custo_mes_a * m for m in meses],
    "B - Solar": [B["custo_instalacao"] + custo_mes_b * m for m in meses],
}).set_index("mês")
st.line_chart(acumulado)

st.subheader("Dimensionamento do sistema solar")
st.write(f"- Consumo máximo da alternativa B: **{consumo_max_wh:.0f} Wh/dia**")
st.write(f"- Painel mínimo: {consumo_max_wh:.0f} ÷ ({HSP} × {RENDIMENTO}) = "
         f"**{painel_min_w:.0f} W** → escolhido **1 painel de {B['painel_w']} W**")
st.write(f"- Geração estimada do painel de {B['painel_w']} W: **{geracao_mes_kwh:.1f} kWh/mês**")

with st.expander("Ver custos de instalação item a item"):
    for alt in (A, B):
        st.markdown(f"**{alt['nome']}** – total R$ {alt['custo_instalacao']:.2f}")
        st.dataframe(pd.DataFrame(list(alt["custos"].items()), columns=["Item", "R$"]),
                     hide_index=True, width="stretch")

with st.expander("Ver dados simulados dos 30 dias"):
    st.dataframe(df, hide_index=True, width="stretch")
