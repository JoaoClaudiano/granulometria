import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
from scipy.interpolate import interp1d

st.set_page_config(page_title="Geotecnia Pro - NBR 7181", layout="wide")

# --- LÓGICA DE INTERPOLAÇÃO PARA Cu E Cc ---
def calcular_diametros(df):
    """Interpola os diâmetros D10, D30 e D60 da curva granulométrica"""
    try:
        # Filtra valores únicos e ordena para a interpolação funcionar
        df_sorted = df.sort_values('Abertura (mm)')
        x = df_sorted['% Passante'].values
        y = df_sorted['Abertura (mm)'].values
        
        # Criamos uma função de interpolação logarítmica para os diâmetros
        f = interp1d(x, np.log10(y), bounds_error=False, fill_value="extrapolate")
        
        d10 = 10**f(10)
        d30 = 10**f(30)
        d60 = 10**f(60)
        
        cu = d60 / d10 if d10 > 0 else 0
        cc = (d30**2) / (d60 * d10) if (d60 * d10) > 0 else 0
        
        return round(cu, 2), round(cc, 2), round(d10, 3)
    except:
        return 0, 0, 0

# --- LÓGICAS DE CLASSIFICAÇÃO ---
def classificar_sucs(p200, ll, ip, pedregulho, areia, cu, cc):
    if p200 < 50:
        pref = "G" if pedregulho > areia else "S"
        if p200 < 5:
            # Bem graduado vs Mal graduado
            grad = "W" if (pref=="G" and cu > 4 and 1 <= cc <= 3) or (pref=="S" and cu > 6 and 1 <= cc <= 3) else "P"
            return f"SUCS: {pref}{grad} – {'Pedregulho' if pref=='G' else 'Areia'} bem/mal graduada"
        elif p200 > 12:
            suf = "C" if ip > 7 and ip >= (0.73*(ll-20)) else "M"
            return f"SUCS: {pref}{suf} – {'Pedregulho' if pref=='G' else 'Areia'} {'argilosa' if suf=='C' else 'siltosa'}"
        else:
            return f"SUCS: {pref}W-{pref}M – Classificação Dupla (ASTM D2487)"
    else:
        tipo = "C" if ip > 7 and ip >= (0.73*(ll-20)) else "M"
        comp = "L" if ll < 50 else "H"
        return f"SUCS: {tipo}{comp} – {'Argila' if tipo=='C' else 'Silte'} de {'baixa' if comp=='L' else 'alta'} plasticidade"

# --- INTERFACE ---
st.title("🔬 Caracterização de Solos Profissional")
st.caption("NBR 7181 | ASTM D2487 | AASHTO M 145 | MCT")

# Barra Lateral para Importação
with st.sidebar:
    st.header("📂 Importar Dados")
    arquivo_subido = st.file_uploader("Arraste CSV ou Excel", type=['csv', 'xlsx'])
    st.info("O arquivo deve conter as colunas: 'Abertura (mm)' e 'Peso Retido (g)'")

col1, col2 = st.columns([1, 1.6])

with col1:
    st.subheader("📥 Entrada de Dados")
    
    with st.expander("Massa e Atterberg", expanded=True):
        massa_total = st.number_input("Massa Total Seca (g)", value=1000.0)
        ll = st.number_input("LL (%)", value=35.0)
        lp = st.number_input("LP (%)", value=20.0)
        ip = ll - lp

    with st.expander("Tabela de Peneiramento", expanded=True):
        if arquivo_subido is not None:
            if arquivo_subido.name.endswith('.csv'):
                df_base = pd.read_csv(arquivo_subido)
            else:
                df_base = pd.read_excel(arquivo_subido)
        else:
            df_base = pd.DataFrame({
                'Abertura (mm)': [50.8, 25.4, 9.5, 4.75, 2.0, 0.42, 0.075],
                'Peso Retido (g)': [0.0, 0.0, 50.0, 100.0, 200.0, 350.0, 150.0]
            })
        
        df_edit = st.data_editor(df_base, num_rows="dynamic")
        
        # --- ALERTA DE CONFERÊNCIA AUTOMÁTICA ---
        soma_frações = df_edit['Peso Retido (g)'].sum()
        erro_massa = abs(soma_frações - massa_total)
        
        if erro_massa > (massa_total * 0.02): # Alerta se erro > 2%
            st.error(f"⚠️ Erro de Massa: Soma ({soma_frações:.1f}g) difere da Massa Total ({massa_total}g)!")
        else:
            st.success(f"✅ Massa conferida: {soma_frações:.1f}g")

with col2:
    if st.button("🚀 PROCESSAR ANÁLISE COMPLETA", use_container_width=True):
        # Cálculos de porcentagem
        df_edit['% Ret Acum'] = (df_edit['Peso Retido (g)'].cumsum() / massa_total) * 100
        df_edit['% Passante'] = 100 - df_edit['% Ret Acum']
        
        # Gráfico
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(df_edit['Abertura (mm)'], df_edit['% Passante'], 's-', color='#1a5276', lw=2)
        ax.set_xscale('log')
        ax.invert_xaxis()
        ax.grid(True, which="both", alpha=0.3)
        ax.set_title("CURVA GRANULOMÉTRICA (NBR 7181)")
        st.pyplot(fig)

        # Coeficientes Cu e Cc
        cu, cc, d10 = calcular_diametros(df_edit)
        
        # Extração para classificação
        def get_p(m): return df_edit[df_edit['Abertura (mm)'] <= m]['% Passante'].iloc[0] if any(df_edit['Abertura (mm)'] <= m) else 0
        
        p200, p4.75 = get_p(0.075), get_p(4.75)
        pedregulho = 100 - p4.75
        areia = p4.75 - p200

        # Resultados
        st.subheader("🏁 Resultados Normativos")
        res_sucs = classificar_sucs(p200, ll, ip, pedregulho, areia, cu, cc)
        
        st.success(f"**{res_sucs}**")
        
        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("Cu (Uniformidade)", cu)
        col_res2.metric("Cc (Curvatura)", cc)
        col_res3.metric("D10 (mm)", d10)

        with st.container():
            st.markdown("### 🧠 Critério Aplicado")
            st.write(f"- **Erro de Balança:** {(soma_frações - massa_total):.2f}g (Conferência automática)")
            if p200 < 50:
                st.write(f"- **Graduação:** {'Bem graduado' if (cu > 4 and 1<=cc<=3) else 'Mal graduado'} (Baseado em Cu/Cc)")
            st.write(f"- **Finos:** {p200:.1f}% passando na peneira #200")
