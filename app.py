import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
from scipy.interpolate import interp1d
import io

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Geotecnia Pro - Normativo v3.4", layout="wide")

# --- 1. CÁLCULO DE DIÂMETROS (INTERPOLAÇÃO LOG-LINEAR) ---
def calcular_diametros_seguro(df):
    try:
        df_sorted = df.sort_values('Abertura (mm)')
        df_sorted = df_sorted[df_sorted['Abertura (mm)'] > 0]
        
        x = df_sorted['% Passante'].values
        y = df_sorted['Abertura (mm)'].values
        
        min_p, max_p = x.min(), x.max()
        
        def interp(pct):
            if pct < min_p or pct > max_p: return None
            f = interp1d(x, np.log10(y), kind='linear')
            return 10 ** f(pct)

        d10, d30, d60 = interp(10), interp(30), interp(60)
        
        cu = (d60 / d10) if (d10 and d60) else None
        cc = ((d30**2) / (d60 * d10)) if (d10 and d30 and d60) else None
        return d10, d30, d60, cu, cc
    except Exception as e:
        return None, None, None, None, None

# --- 2. SUCS REFINADO (ASTM D2487) - CORRIGIDO (C-M REMOVIDO) ---
def classificar_sucs_refinado(p200, p4, ll, ip, cu, cc):
    if ip < 0: ip = 0
    linha_a = 0.73 * (ll - 20)
    
    # SOLOS GROSSOS (< 50% passa na #200)
    if p200 < 50:
        pedregulho = 100 - p4
        areia = p4 - p200
        pref = "G" if pedregulho > areia else "S"
        
        if p200 < 5:
            if cu is None or cc is None: return f"{pref} (Dados Insuficientes)"
            if pref == "G":
                grad = "W" if (cu >= 4 and 1 <= cc <= 3) else "P"
            else: 
                grad = "W" if (cu >= 6 and 1 <= cc <= 3) else "P"
            return f"{pref}{grad}"
            
        elif p200 > 12:
            suf = "C" if (ip > 7 and ip >= linha_a) else "M"
            # --- CORREÇÃO: REMOVIDO O TRECHO QUE CRIAVA "C-M" ---
            return f"{pref}{suf}"
            
        else: # 5% a 12%
            if cu is None or cc is None: return f"{pref}-DUPLA (Falta Cu/Cc)"
            if pref == "G":
                grad = "W" if (cu >= 4 and 1 <= cc <= 3) else "P"
            else:
                grad = "W" if (cu >= 6 and 1 <= cc <= 3) else "P"
            
            suf = "C" if (ip > 7 and ip >= linha_a) else "M"
            # --- CORREÇÃO: REMOVIDO O TRECHO QUE CRIAVA "C-M" ---
            return f"{pref}{grad}-{pref}{suf}"

    # SOLOS FINOS (>= 50% passa na #200)
    else:
        if ll < 50: 
            if ip > 7 and ip >= linha_a: return "CL"
            elif ip < 4 or ip < linha_a: return "ML"
            else: return "CL-ML"
        else: 
            return "CH" if ip >= linha_a else "MH"

# --- 3. AASHTO M 145 - CORRIGIDO (IP NEGATIVO TRATADO, A-3 EXIGE IP=0) ---
def classificar_aashto_final(p10, p40, p200, ll, ip):
    # --- CORREÇÃO DE SEGURANÇA: IP nunca é negativo na lógica de decisão ---
    ip_eff = max(0, ip)   # IP negativo vira 0 (equivalente a NP)
    # -----------------------------------------------------------------------
    
    grupo = "Indeterminado"
    if p200 <= 35:
        if p10 <= 50 and p40 <= 30 and p200 <= 15 and ip_eff <= 6:
            grupo = "A-1-a"
        elif p40 <= 50 and p200 <= 25 and ip_eff <= 6:
            grupo = "A-1-b"
        # --- CORREÇÃO DEFINITIVA PARA A-3: IP DEVE SER ZERO (NP REAL) ---
        elif p40 >= 51 and p200 <= 10 and ip_eff == 0:
            grupo = "A-3"
        # ----------------------------------------------------------------
        else:
            if ll <= 40:
                grupo = "A-2-4" if ip_eff <= 10 else "A-2-6"
            else:
                grupo = "A-2-5" if ip_eff <= 10 else "A-2-7"
    else:
        if ll <= 40:
            grupo = "A-4" if ip_eff <= 10 else "A-6"
        else:
            if ip_eff <= 10:
                grupo = "A-5"
            else:
                grupo = "A-7-5" if ip_eff <= (ll - 30) else "A-7-6"
    
    # --- Cálculo do IG (agora com ip_eff, sem necessidade de novo tratamento) ---
    t1 = max(0, (p200 - 35) * (0.2 + 0.005 * (ll - 40)))
    t2 = max(0, 0.01 * (p200 - 15) * (ip_eff - 10))
    
    if grupo in ["A-1-a", "A-1-b", "A-3", "A-2-4", "A-2-5"]:
        ig = 0
    elif grupo in ["A-2-6", "A-2-7"]:
        ig = t2
    else:
        ig = t1 + t2
    
    return f"{grupo} ({int(round(ig))})", t1, t2

# --- 4. GERADOR DE PDF ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'RELATÓRIO GEOTÉCNICO', 0, 1, 'C')
        self.ln(5)

def gerar_pdf(d):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. RESULTADOS", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"SUCS: {d['sucs']}", ln=True)
    pdf.cell(0, 8, f"AASHTO: {d['aashto']}", ln=True)
    pdf.cell(0, 8, f"MCT: {d['mct']}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE ---
st.title("🔬 Geotecnia Pro - DashBoard Normativo")
st.markdown("---")

col_in, col_out = st.columns([1, 1.5])

with col_in:
    st.subheader("📥 Dados de Laboratório")
    m_seca = st.number_input("Massa Seca Total (g)", value=1000.0)
    c_ll, c_lp = st.columns(2)
    ll = c_ll.number_input("LL (%)", value=42.0)
    lp = c_lp.number_input("LP (%)", value=26.0)
    ip = ll - lp
    st.info(f"Índice de Plasticidade (IP): {ip:.1f}%")
    
    # Campo MCT com orientação manual
    st.markdown("**Classificação MCT**")
    mct_man = st.text_input(
        "Insira a classe (Manual)", 
        value="LG'",
        help="Informe o resultado obtido via ensaios Mini-MCV e Perda de Massa por Imersão."
    )
    st.caption("ℹ️ Este campo não é calculado automaticamente. Insira o dado de laboratório.")
    
    df = pd.DataFrame({
        'Abertura (mm)': [50.8, 19.1, 4.75, 2.0, 0.42, 0.075],
        'Peso Retido (g)': [0.0, 50.0, 100.0, 150.0, 400.0, 250.0]
    })
    df_edit = st.data_editor(df, num_rows="dynamic", hide_index=True)

with col_out:
    if st.button("🚀 PROCESSAR ANÁLISE", type="primary", use_container_width=True):
        # Limpeza de dados vazios ou zeros na abertura
        df_proc = df_edit[df_edit['Abertura (mm)'] > 0].copy()
        
        if df_proc.empty:
            st.error("Insira dados válidos de granulometria.")
        else:
            # --- Validação de extrapolação (peneiras críticas) ---
            min_user_d = df_proc['Abertura (mm)'].min()
            max_user_d = df_proc['Abertura (mm)'].max()
            
            missing_sieves = []
            if max_user_d < 2.0: missing_sieves.append("#10 (2.0mm)")
            if max_user_d < 0.42 and min_user_d > 0.42: missing_sieves.append("#40 (0.42mm)")
            if min_user_d > 0.075: missing_sieves.append("#200 (0.075mm)")
            
            if missing_sieves:
                st.warning(
                    f"⚠️ **Atenção: Extrapolação Detectada!**\n\n"
                    f"A sua curva granulométrica não abrange as peneiras: {', '.join(missing_sieves)}.\n"
                    "O sistema assumirá 0% ou 100% para estes valores, o que pode distorcer a classificação. "
                    "Sugestão: Adicione peneiras para cobrir toda a faixa."
                )
            
            # --- Processamento granulométrico ---
            df_proc['% Passante'] = 100 - (df_proc['Peso Retido (g)'].cumsum() / m_seca * 100)
            df_proc['% Passante'] = df_proc['% Passante'].clip(0, 100)
            
            # Interpolação logarítmica para peneiras críticas
            def get_p_log(diametro_alvo):
                if diametro_alvo > df_proc['Abertura (mm)'].max(): return 100.0
                if diametro_alvo < df_proc['Abertura (mm)'].min(): return 0.0
                f_log = interp1d(np.log10(df_proc['Abertura (mm)']), df_proc['% Passante'], kind='linear')
                return float(f_log(np.log10(diametro_alvo)))

            p10 = get_p_log(2.0)
            p40 = get_p_log(0.42)
            p200 = get_p_log(0.075)
            p4 = get_p_log(4.75)

            d10, d30, d60, cu, cc = calcular_diametros_seguro(df_proc)
            
            # --- Classificações (já com as correções aplicadas) ---
            sucs = classificar_sucs_refinado(p200, p4, ll, ip, cu, cc)
            aashto, t1, t2 = classificar_aashto_final(p10, p40, p200, ll, ip)
            
            # Gráfico
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.axvspan(0.001, 0.075, color='#e6f2ff', alpha=0.5, label='Finos')
            ax.axvspan(0.075, 4.75, color='#fff9c4', alpha=0.5, label='Areia')
            ax.axvspan(4.75, 100, color='#ffe0b2', alpha=0.5, label='Pedregulho')
            ax.plot(df_proc['Abertura (mm)'], df_proc['% Passante'], 'o-k')
            ax.set_xscale('log')
            ax.invert_xaxis()
            ax.grid(True, which="both", alpha=0.3)
            ax.legend()
            st.pyplot(fig)
            
            # Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("SUCS", sucs)
            c2.metric("AASHTO", aashto)
            c3.metric("MCT", mct_man)
            
            # Botão PDF
            dados_pdf = {
                'sucs': sucs, 'aashto': aashto, 'mct': mct_man,
                'll': ll, 'ip': ip, 'f200': p200, 'd10': d10, 'cu': cu, 'cc': cc
            }
            st.download_button(
                "📥 Baixar PDF",
                data=gerar_pdf(dados_pdf),
                pdf.cell(0, 8, f"Nota IG: O solo apresenta Índice de Grupo {int(round(ig))}, indicando um comportamento...", ln=True)
                file_name="relatorio.pdf",
                mime="application/pdf"
            )
