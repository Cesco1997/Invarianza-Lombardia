import streamlit as st
import requests
import os
import pandas as pd 
import numpy as np 
#import base64

# Layout pagina 
st.set_page_config(
    page_title="Calcolo invarianza Lombardia",
    page_icon="💧",  # qualsiasi emoji va bene
    layout="centered"
)

#def set_background(image_file_path):
#    with open(image_file_path, "rb") as image_file:
#        encoded = base64.b64encode(image_file.read()).decode()
#
#    st.markdown(
#        f"""
#        <style>
#        body {{
#            background-image: url("data:image/jpg;base64,{encoded}");
#             background-size: cover;
#            background-position: center;
#            background-repeat: no-repeat;
#            background-attachment: fixed;
#        }}
#        </style>
#        """,
#        unsafe_allow_html=True
#    )
#
#set_background("background.jpg")  

# === CONFIG ===
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not api_key:
    st.error("API key non trovata")
    
file_path = "Comuni_criticita_idraulica.xlsx"
df_comuni = pd.read_excel(file_path)

# === SESSION STATE INIT ===
def init_session_state():
    defaults = {
        "check_portata": False,
        "second_form_submitted": False,
        "first_form_submitted": False,
        "method": "Cipolla"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# === FUNZIONI ===
def get_coordinates(address):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json()["results"]
        if results:
            location = results[0]["geometry"]["location"]
            return location["lat"], location["lng"]
    return None, None

def mostra_coordinate(indirizzo):
    lat, lng = get_coordinates(indirizzo)
    if lat and lng:
        st.map({"lat": [lat], "lon": [lng]})
    else:
        st.error("Indirizzo non trovato.")

def calcola_valore_phi(sup_imm, sup_semi, sup_perm, somma):
    phi = sup_imm / somma + 0.7 * sup_semi / somma + 0.3 * sup_perm / somma
    return round(phi, 2)

def trova_dati_comune(nome_comune, df):
    return df[df["Comune"] == nome_comune].iloc[0]

def calcola_valore_ULim(criticita):
    return 10  if criticita == "A" else 20 

def compute_coef_P(dati_comune):
    if dati_comune["Coefficiente P"] == 0.8:
        return 0.8
    else:
        return 1

def show_coef_P(dati_comune):
    if dati_comune["Criticità idraulica"] == "A":
        if dati_comune["Coefficiente P"] == 0.8:
            st.write("**Coefficiente P:** 0.8")
        else:
            st.write("**Coefficiente P:** 1")

def determina_modalita(phi, superficie, area):
    if superficie <= 300:
        return "Requisiti minimi (art. 12, comma 1)"
    elif 300 < superficie <= 1000:
        if phi <= 0.4:
            return "Requisiti minimi (art. 12, comma 2)"
        elif area != "C":
            return "Metodo delle sole piogge (art. 11 e Allegato G)"
        else:
            return "Requisiti minimi (art. 12, comma 2)"
    elif 1000 < superficie <= 10000:
        return "Requisiti minimi (art. 12, comma 2)" if area == "C" else "Metodo delle sole piogge (art. 11 e Allegato G)"
    elif 10000 < superficie <= 100000:
        if phi <= 0.4:
            return "Requisiti minimi (art. 12, comma 2)" if area == "C" else "Metodo delle sole piogge (art. 11 e Allegato G)"
        else:
            return "Requisiti minimi (art. 12, comma 2)" if area == "C" else "Procedura dettagliata (art. 11 e Allegato G)"
    else:
        return "Requisiti minimi (art. 12, comma 2)" if area == "C" else "Procedura dettagliata (art. 11 e Allegato G)"

def invaso_minimo(area):
    return 800 if area == "A" else 500 if area == "B" else 400

# === APP ===
if st.button("🔄 Resetta tutto"):
    st.session_state.clear()

st.title("Calcolatore Superfici e Coordinate")

with st.form("form_dati"):
    st.subheader("📍 Ricerca Coordinate")
    indirizzo = st.text_input("Inserisci indirizzo o luogo")
    comune = st.selectbox("Seleziona un Comune", df_comuni["Comune"].dropna().unique())

    st.subheader("📐 Inserisci superfici")
    sup_imm = st.number_input("Superficie impermeabile (mq)", min_value=0.0, step=1.0)
    sup_semi = st.number_input("Superficie semi permeabile (mq)", min_value=0.0, step=1.0)
    sup_verde = st.number_input("Superficie verde pensile (mq)", min_value=0.0, step=1.0)
    sup_perm = st.number_input("Superficie permeabile (mq)", min_value=0.0, step=1.0)
    check_portata = st.checkbox("**Portata massima ammissibile per ettaro nota**")
    submitted = st.form_submit_button("Calcola")

if submitted:
    sup_tot = sup_imm + sup_semi + sup_perm
    phi = calcola_valore_phi(sup_imm, sup_semi, sup_perm, sup_tot)
    dati_comune = trova_dati_comune(comune, df_comuni)
    metodo = determina_modalita(phi, sup_tot, dati_comune["Criticità idraulica"])
    coeff_P = compute_coef_P(dati_comune)

    if not check_portata:
        mostra_coordinate(indirizzo)
        st.write(f"**Somma totale superfici:** {sup_tot} mq")
        st.write(f"**Coefficiente di deflusso medio ponderale:** {phi}")
        st.write("**Criticità idraulica:**", dati_comune["Criticità idraulica"])
        show_coef_P(dati_comune)
        st.write(f"**Metodo da utilizzare per il calcolo dell'invaso:** {metodo}")
        ulim = calcola_valore_ULim(dati_comune["Criticità idraulica"])
        st.write(f"**Portata massima ammissibile :** {ulim} l/s per ettaro")

    # Salvataggio in sessione
    st.session_state.update({
        "indirizzo": indirizzo,
        "first_form_submitted": True,
        "sup_tot": sup_tot,
        "phi": phi,
        "check_portata": check_portata,
        "dati_comune": dati_comune,
        "sup_verde": sup_verde,
        "method": metodo,
        "coeff_P": coeff_P
    })
    if not check_portata:
        st.session_state.ULim = ulim

if st.session_state.check_portata:
    with st.form("second_form"):
        ulim = st.number_input("Portata massima ammissibile per ettaro", min_value=0.0)
        st.session_state.second_form_submitted = st.form_submit_button("Calcola")

if st.session_state.second_form_submitted:
    mostra_coordinate(st.session_state.indirizzo)
    st.write(f"**Somma totale superfici:** {st.session_state.sup_tot} mq")
    st.write(f"**Coefficiente di deflusso medio ponderale:** {st.session_state.phi}")
    st.write("**Criticità idraulica:**", st.session_state.dati_comune["Criticità idraulica"])
    show_coef_P(st.session_state.dati_comune)
    st.write(f"**Metodo da utilizzare per il calcolo dell'invaso:** {st.session_state.method}")
    st.write(f"**Portata massima ammissibile :** {ulim} l/s per ettaro")
    st.session_state.ULim = ulim

# === RISULTATI FINALI ===
if st.session_state.method == "Procedura dettagliata (art. 11 e Allegato G)":
    st.write("Richiedere supporto di un esperto")

elif st.session_state.method.startswith("Requisiti minimi"):
    volume = round(0.0001 * st.session_state.phi * st.session_state.sup_tot * invaso_minimo(st.session_state.method), 2)
    st.write(f"**Volume da laminare:** {volume} mc")
    st.write(f"**Altezza vasca laminazione:** {round(volume / st.session_state.sup_verde, 2)} cm")

elif st.session_state.method == "Metodo delle sole piogge (art. 11 e Allegato G)":
    st.write("---")
    st.write("## 🌧️ Parametri LSPP")
    st.markdown(
    '''
    <div style="text-align: center; font-size: 24px; margin-bottom: 24px;">
        <a href="https://iris.arpalombardia.it/gisINM/common/webgis_central.php?TYPE=guest" target="_blank">
            👉 Apri la mappa ARPA Lombardia in una nuova scheda
        </a>
    </div>
    ''',
    unsafe_allow_html=True
    )

    with st.form("form_lspp"):
        A1 = st.number_input("A1", step=0.01)
        n = st.number_input("n", step=0.01)
        alpha = st.number_input("α (alpha)", step=0.01)
        k = st.number_input("k", step=0.01)
        epsilon = st.number_input("ε (epsilon)", step=0.01)
        T_ritorno = st.number_input("Tempo di ritorno", min_value=1, step=1)
        submitted_2 = st.form_submit_button("Calcola")

    if submitted_2:
        wT = epsilon + alpha / k * (1 - (np.log(T_ritorno / (T_ritorno - 1))) ** k)
        TempoCritico = round(st.session_state.ULim / (2.78 * st.session_state.phi * wT * A1 * n) ** (1 / (n - 1)), 2)
        Precipitazione = wT * A1 * TempoCritico ** n
        volume = round(0.0001 * (10 * st.session_state.sup_tot * st.session_state.phi * wT * TempoCritico ** n - 3.6 * st.session_state.sup_tot * st.session_state.ULim * TempoCritico), 2)
        volume_minimo = round(0.0001 * st.session_state.coeff_P * (st.session_state.phi * st.session_state.sup_tot * invaso_minimo(st.session_state.method)), 2)

        if volume_minimo > volume:
            st.markdown("<div style='font-size:22px; margin-bottom:24px;'> Metodo utilizzato: <span style='color:red; font-weight:bold;'>Requisiti minimi (art. 12, comma 2)</span></div>",
                unsafe_allow_html=True
            )
            st.write(f"**Volume da laminare:** {volume_minimo} mc")
            st.write(f"**Altezza vasca laminazione:** {round(volume_minimo / st.session_state.sup_verde, 2)} cm")
        else:
            st.markdown("<div style='font-size:22px; margin-bottom:24px;'> Metodo utilizzato: <span style='color:red; font-weight:bold;'>Metodo delle sole piogge (art. 11 e Allegato G)</span></div>",
                unsafe_allow_html=True
            )
            st.write(f"**Durata critica:** {TempoCritico} ore")
            st.write(f"**Volume da laminare:** {volume} mc")
            st.write(f"**Altezza vasca laminazione:** {round(volume / st.session_state.sup_verde, 2)} cm")




# import streamlit as st
# import requests
# import pandas as pd 
# import numpy as np 

# # === CONFIG ===
# GOOGLE_MAPS_API_KEY = "AIzaSyCgCQIXGAonp2_HnF091U5Iw5WrfUUN08k"
# file_path = "C:/Users/Francesco/Daku 2025/Invarianza/1-Lombardia/Comuni_criticita_idraulica.xlsx"
# df = pd.read_excel(file_path)
# if "check_portata" not in st.session_state:
#     st.session_state.check_portata = False

# if "second_form_submitted" not in st.session_state:
#     st.session_state.second_form_submitted = False

# if "first_form_submitted" not in st.session_state:
#     st.session_state.first_form_submitted = False
# if "method" not in st.session_state:
#     st.session_state.method = False

# # === FUNZIONI ===
# def get_coordinates(address):
#     url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_MAPS_API_KEY}"
#     response = requests.get(url)
#     if response.status_code == 200:
#         results = response.json()["results"]
#         if results:
#             location = results[0]["geometry"]["location"]
#             return location["lat"], location["lng"]
#     return None, None

# def mostra_coordinate(indirizzo):
#     lat, lng = get_coordinates(indirizzo)
#     if lat and lng:
#         st.map({"lat": [lat], "lon": [lng]})
#     else:
#         st.error("Indirizzo non trovato.")
    
# def cerca_oggetto(lista, nome):
#     for oggetto in lista:
#         if oggetto["nome"].lower() == nome.lower():
#             return oggetto
#     return None

# def calcola_valore_phi(sup_imm,sup_semi,sup_perm,somma):
#     phi = sup_imm/somma + 0.7*sup_semi/somma + 0.3*sup_perm/somma
#     return round(phi,2) 

# def trova_dati_comune(comune_scelto,df):
#     riga = df[df["Comune"] == comune_scelto].iloc[0]
#     return riga

# def calcola_valore_ULim(coef_crit,coef_P):
#     if coef_crit == "A":
#         return 10*coef_P
#     else:
#         return 20*coef_P
    
# def mostra_coef_P(dati_comune):
#     if dati_comune["Coefficiente P"] == 0.8:
#         st.write("**Coefficiente P:** 0.8")
#         return 0.8
#     else:
#         st.write("**Coefficiente P:** 1")
#         return 1
    
# def determina_modalita(coefficiente_deflusso, superficie_intervento_mq,area_intervento):
#     if superficie_intervento_mq <= 300:
#         return "Requisiti minimi (art. 12, comma 1)"
#     elif 300 < superficie_intervento_mq <= 1000:
#         if coefficiente_deflusso <= 0.4:
#             return "Requisiti minimi (art. 12, comma 2)"
#         elif area_intervento != "C":
#             return "Metodo delle sole piogge (art. 11 e Allegato G)"
#         else: 
#             return "Requisiti minimi (art. 12, comma 2)"
#     elif 1000 < superficie_intervento_mq <= 10000:
#         if area_intervento == "C":
#             return "Requisiti minimi (art. 12, comma 2)"
#         else: 
#             return "Metodo delle sole piogge (art. 11 e Allegato G)"
#     elif 10000 < superficie_intervento_mq <= 100000:
#         if coefficiente_deflusso <= 0.4:
#             if area_intervento == "C":
#                 return "Requisiti minimi (art. 12, comma 2)"
#             else:
#                 return "Metodo delle sole piogge (art. 11 e Allegato G)"
#         else:
#             if area_intervento == "C":
#                 return "Requisiti minimi (art. 12, comma 2)"
#             else:
#                 return "Procedura dettagliata (art. 11 e Allegato G)"
#     else:  # > 100000
#         if area_intervento == "C":
#             return "Requisiti minimi (art. 12, comma 2)"
#         else:
#             return "Procedura dettagliata (art. 11 e Allegato G)"
    
# def invaso_minimo(area_intervento):
#     if area_intervento == "A":
#         return 800
#     elif area_intervento == "B":
#         return 500
#     else:
#         return 400



# # === STREAMLIT APP ===

# if st.button("🔄 Resetta tutto"):
#     st.session_state.clear()  # ⚠️ elimina tutto!
#     #st.experimental_rerun()   # aggiorna la pagina

# st.title("Calcolatore Superfici e Coordinate")

# with st.form("form_dati"):
#     st.subheader("📍 Ricerca Coordinate")
#     indirizzo = st.text_input("Inserisci indirizzo o luogo")
#     comune_scelto = st.selectbox("Seleziona un prodotto", df["Comune"].dropna().unique())

#     st.subheader("📐 Inserisci superfici")
#     sup_imm = st.number_input("Superficie impermeabile (mq)", min_value=0.0, step=1.0)
#     sup_semi = st.number_input("Superficie semi permeabile (mq)", min_value=0.0, step=1.0)
#     sup_verde = st.number_input("Superficie verde pensile (mq)",
#                                 min_value=0.0,
#                                 step=1.0)
#     sup_perm = st.number_input("Superficie permeabile (mq)", min_value=0.0, step=1.0)

#     check_portata = st.checkbox("**Portata massima ammissibile per ettaro nota**")

#     submitted = st.form_submit_button("Calcola")

# # === RISULTATI ===
# if submitted:
#     # Calcoli 
#     sup_tot = sup_imm + sup_semi + sup_perm
#     Phi = calcola_valore_phi(sup_imm,sup_semi,sup_perm,sup_tot)
#     dati_comune = trova_dati_comune(comune_scelto,df)
#     modalita_da_usare = determina_modalita(Phi,
#                                             sup_tot,
#                                             dati_comune["Criticità idraulica"])
    
#     if not check_portata:
#         # Scrittura
#         mostra_coordinate(indirizzo)
#         st.write(f"**Somma totale superfici:** {sup_tot} mq")
#         st.write(f"**Coefficiente di deflusso medio ponderale:** {Phi}")
#         st.write("**Criticità idraulica:**", dati_comune["Criticità idraulica"])
#         st.write(f"**Metodo da utilizzare per il calcolo dell'invaso:** {modalita_da_usare}") 
#         coef_P = mostra_coef_P(dati_comune)       
#         # Calcoli e scrittura Ulim
#         ULim = calcola_valore_ULim(dati_comune["Criticità idraulica"],coef_P)
#         st.write(f"**Portata massima ammissibile :** {ULim} l/s per ettaro")

#     # Save data
#     st.session_state.indirizzo = indirizzo
#     st.session_state.first_form_submitted = True
#     st.session_state.sup_tot = sup_tot
#     st.session_state.Phi = Phi
#     st.session_state.check_portata = check_portata
#     st.session_state.dati_comune= dati_comune
#     st.session_state.Sup_verde = sup_verde
#     st.session_state.method = modalita_da_usare
#     if not check_portata:
#         st.session_state.ULim = ULim 

# ## Seconda forma
# if st.session_state.check_portata == True:
#     with st.form("Mettere massima portata nota"):
#         ULim = st.number_input("Portata massima ammissibile per ettaro", min_value=0.0)
#         st.session_state.second_form_submitted = st.form_submit_button("Calcola")

# if st.session_state.second_form_submitted: 
#     mostra_coordinate(st.session_state.indirizzo)
#     st.write(f"**Somma totale superfici:** {st.session_state.sup_tot} mq")
#     st.write(f"**Coefficiente di deflusso medio ponderale:** {st.session_state.Phi}")
#     st.write("**Criticità idraulica:**", st.session_state.dati_comune["Criticità idraulica"])
#     st.write(f"**Metodo da utilizzare per il calcolo dell'invaso:** {st.session_state.method}") 
#     coef_P = mostra_coef_P(st.session_state.dati_comune)
#     st.write(f"**Portata massima ammissibile :** {ULim} l/s per ettaro")
#     st.session_state.ULim = ULim 

# ## Terza forma
# if st.session_state.method == "Procedura dettagliata (art. 11 e Allegato G)":
#     st.write("Richiedere supporto di un esperto")
# elif st.session_state.method == "Requisiti minimi (art. 12, comma 2)" or st.session_state.method == "Requisiti minimi (art. 12, comma 1)":
#     GrandezzaInvaso = round(0.0001*st.session_state.Phi*\
#         st.session_state.sup_tot*invaso_minimo(st.session_state.method),2)
#     st.write(f"**Volume da laminare:** {GrandezzaInvaso} mc")
#     st.write(f"**Altezza vasca laminazione:** {round(GrandezzaInvaso/st.session_state.Sup_verde,2)} cm")
# elif st.session_state.method == "Metodo delle sole piogge (art. 11 e Allegato G)":
#     # === BOTTONE ARPA ===
#     st.write("---")
#     st.write("## 🌧️ Parametri LSPP")
#     #components.iframe("https://iris.arpalombardia.it/gisINM/common/webgis_central.php?TYPE=guest",
#     #                   height=600
#     #                   )
#     st.markdown(
#         '<a href="https://iris.arpalombardia.it/gisINM/common/webgis_central.php?TYPE=guest" target="_blank">'
#         '👉 Apri la mappa ARPA Lombardia in una nuova scheda</a>',\
#         unsafe_allow_html=True
#         )
#     #st.write("Cliccare su LSPP e ricavare i parametri da inserire nel programma.")

#     with st.form("parametri"):
#         A1 = st.number_input("A1", step=0.01)
#         n = st.number_input("n", step=0.01)
#         alpha = st.number_input("α (alpha)", step=0.01)
#         k = st.number_input("k", step=0.01)
#         epsilon = st.number_input("ε (epsilon)", step=0.01)
#         T_ritorno = st.number_input("Tempo di ritorno",
#                                     min_value = 0,
#                                     step=1)

#         submitted_2 = st.form_submit_button("Calcola")

#     if submitted_2:
#         wT = epsilon + alpha/k * (1 - (np.log(T_ritorno/(T_ritorno-1)))**(k))
#         TempoCritico = round(st.session_state.ULim/(2.78*st.session_state.Phi*wT*A1*n)**(1/(n-1)),2)
#         Precipitazione = wT*A1*TempoCritico**(n)
#         GrandezzaInvaso = round(.0001*(10*st.session_state.sup_tot*st.session_state.Phi*wT*
#                                 TempoCritico**(n)-3.6*st.session_state.sup_tot*
#                                 st.session_state.ULim*TempoCritico),2)
        
#         GrandezzaInvasoMinima = round(0.0001*(st.session_state.Phi*\
#         st.session_state.sup_tot*invaso_minimo(st.session_state.method)),2)

#         if GrandezzaInvasoMinima > GrandezzaInvaso:
#             st.write("**Si sono utilizzati i Requisiti minimi (art. 12, comma 2)**")
#             st.write(f"**Volume da laminare:** {GrandezzaInvasoMinima} mc")
#             st.write(f"**Altezza vasca laminazione:** {round(GrandezzaInvasoMinima/st.session_state.Sup_verde,2)} cm")
#         else:
#             st.write("**Si è usato il volume calcolato con il Metodo delle sole piogge (art. 11 e Allegato G)**")
#             st.write(f"**Durata critica:** {TempoCritico} ore")
#             st.write(f"**Volume da laminare:** {GrandezzaInvaso} mc")
#             st.write(f"**Altezza vasca laminazione:** {round(GrandezzaInvaso/st.session_state.Sup_verde,2)} cm")
