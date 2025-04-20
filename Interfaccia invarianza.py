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
GOOGLE_MAPS_API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
DESTINATARIO = st.secrets["DESTINATARIO"]
EMAIL_MITTENTE = st.secrets["EMAIL_MITTENTE"]
PASSWORD_MITTENTE = st.secrets["PASSWORD_MITTENTE"]

if not GOOGLE_MAPS_API_KEY:
    st.error("API key non trovata")
    
file_path = "Comuni_criticita_idraulica.xlsx"
df_comuni = pd.read_excel(file_path)

# === SESSION STATE INIT ===
def init_session_state():
    defaults = {
        "check_portata": False,
        "perfect_LSPP": False,
        "second_form_submitted": False,
        "first_form_submitted": False,
        "method": "Cipolla",
        "method_2": "Cipolla",
        "regione": "Lombardia"
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
        # st.map({"lat": [lat], "lon": [lng]})
        mappa = folium.Map(location=[lat, lng], zoom_start=13)

        # Aggiungi un marker
        folium.Marker([lat, lng], popup="Posizione selezionata").add_to(mappa)

        # Mostra la mappa in Streamlit
        st_folium(mappa, width=700, height=500,returned_objects=[])
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

def crea_df_parametri(comune, a1, n, alpha, kappa, epsilon):
    df_parametri = pd.DataFrame({
        "Comune": [comune],
        "a1": [a1],
        "n": [n],
        "alpha": [alpha],
        "kappa": [kappa],
        "epsilon": [epsilon]
    })
    return df_parametri

# === APP ===
if st.button("🔄 Resetta tutto"):
    st.session_state.clear()
    init_session_state()

st.title("Calcolatore Superfici e Coordinate")

with st.form("form_dati"):
    st.subheader("📄 Informazioni lavoro")
    contatto = st.text_input("Contatto", placeholder="Mario Rossi")
    figura_contatto = st.text_input("Figura del contatto", placeholder="Progettista, Tecnico Comunale, etc.")

    st.subheader("📍 Ricerca Coordinate")
    comune = st.selectbox("Seleziona un Comune", df_comuni["Comune"].dropna().unique())
    indirizzo = st.text_input("Inserisci via e numero civico", placeholder="Via Roma 1")

    st.subheader("📐 Inserisci superfici")
    sup_imm = st.number_input("Superficie impermeabile (mq)", min_value=0.0, step=1.0)
    st.caption("Es: coperture, pavimentazioni, contine di strade, vialetti e parcheggi")
    # Riga orizzontale: semi permeabile e verde pensile
    col1, col2, col3 = st.columns([3, 1, 3])
    with col1:
        sup_semi = st.number_input("Superficie semi permeabile (mq)", min_value=0.0, step=1.0)
    with col2:
        st.markdown("<div style='text-align: center; padding-top: 2.5em;'>di cui</div>", unsafe_allow_html=True)
    with col3:
        sup_verde = st.number_input("Superficie verde pensile (mq)", min_value=0.0, step=1.0)
    st.caption("Es: giardini pensili, pavimentazioni dreananti o semipermeabili di strade, vialetti e parcheggi")
    sup_perm = st.number_input("Superficie permeabile (mq)", min_value=0.0, step=1.0)
    st.caption("Es: aree verdi. Da NON considerare aree ad uso agricolo e superfici incolte")
    check_portata = st.checkbox("**Portata massima ammissibile per ettaro nota**")
    perfect_LSPP = st.checkbox("**Se si vuole estrarre i parametri LSPP attuali**")
    submitted = st.form_submit_button("Calcola")

if submitted:
    # Controllo se il comune è presente nel dataframe
    dati_comune = df_comuni[df_comuni["Comune"] == comune]

    sup_tot = sup_imm + sup_semi + sup_perm
    if sup_tot == 0:
        st.error("La somma delle superfici non può essere zero.")
        st.stop()
    else:
        phi = calcola_valore_phi(sup_imm, sup_semi, sup_perm, sup_tot)
    if sup_semi < sup_verde:
        st.error("La superficie semi permeabile non può essere minore della superficie verde pensile.")
        st.stop()
    dati_comune = trova_dati_comune(comune, df_comuni)
    metodo = determina_modalita(phi, sup_tot, dati_comune["Criticità idraulica"])
    coeff_P = compute_coef_P(dati_comune)

    if not check_portata:
        mostra_coordinate(f"{st.session_state.regione}, {comune}, {indirizzo}")
        st.write(f"**Somma totale superfici:** {sup_tot} mq")
        st.write(f"**Coefficiente di deflusso medio ponderale:** {phi}")
        st.write("**Criticità idraulica:**", dati_comune["Criticità idraulica"])
        show_coef_P(dati_comune)
        st.markdown("**📊 Parametri LSPP**")
        st.table(crea_df_parametri(comune,
                                   dati_comune["a1"],
                                   dati_comune["n"],
                                   dati_comune["alpha"],
                                   dati_comune["kappa"],
                                   dati_comune["epsilon"]
                                   ))
        st.write(f"**Metodo da utilizzare per il calcolo dell'invaso:** {metodo}")
        ulim = calcola_valore_ULim(dati_comune["Criticità idraulica"])
        st.write(f"**Portata massima ammissibile :** {ulim} l/s per ettaro")


    # Salvataggio in sessione
    st.session_state.update({
        "contatto": contatto,
        "figura_contatto": figura_contatto,
        "comune": comune,
        "indirizzo": indirizzo,
        "first_form_submitted": True,
        "sup_tot": sup_tot,
        "sup_imm": sup_imm,
        "sup_semi": sup_semi,
        "sup_perm": sup_perm,
        "sup_verde": sup_verde,
        "phi": phi,
        "check_portata": check_portata,
        "dati_comune": dati_comune,
        "sup_verde": sup_verde,
        "method": metodo,
        "coeff_P": coeff_P,
        "perfect_LSPP": perfect_LSPP,
    })

    if not check_portata:
        st.session_state.ULim = ulim

if st.session_state.check_portata:
    with st.form("second_form"):
        ulim = st.number_input("Portata massima ammissibile per ettaro", min_value=0.0)
        st.session_state.second_form_submitted = st.form_submit_button("Calcola")

if st.session_state.second_form_submitted:
    mostra_coordinate(f"{st.session_state.regione}, {st.session_state.comune}, {st.session_state.indirizzo}")
    st.write(f"**Somma totale superfici:** {st.session_state.sup_tot} mq")
    st.write(f"**Coefficiente di deflusso medio ponderale:** {st.session_state.phi}")
    st.write("**Criticità idraulica:**", st.session_state.dati_comune["Criticità idraulica"])
    show_coef_P(st.session_state.dati_comune)
    st.markdown("**📊 Parametri LSPP**")
    st.table(crea_df_parametri(st.session_state.comune,
                                   st.session_state.dati_comune["a1"],
                                   st.session_state.dati_comune["n"],
                                   st.session_state.dati_comune["alpha"],
                                   st.session_state.dati_comune["kappa"],
                                   st.session_state.dati_comune["epsilon"]
                                   ))
    st.write(f"**Metodo da utilizzare per il calcolo dell'invaso:** {st.session_state.method}")
    st.write(f"**Portata massima ammissibile :** {ulim} l/s per ettaro")
    st.session_state.ULim = ulim

# === RISULTATI FINALI ===
if st.session_state.method == "Procedura dettagliata (art. 11 e Allegato G)":
    st.write("Richiedere supporto di un esperto")
    st.session_state.method_2 = "True"

elif st.session_state.method.startswith("Requisiti minimi"):
    volume = round(0.0001 * st.session_state.phi * st.session_state.sup_tot * invaso_minimo(st.session_state.method), 2)
    st.write(f"**Volume da laminare:** {volume} mc")
    st.write(f"**Altezza vasca laminazione:** {round(volume / st.session_state.sup_verde, 2)} cm")
    st.session_state.method_2 = "True"

elif st.session_state.method == "Metodo delle sole piogge (art. 11 e Allegato G)":
    st.write("---")
    if st.session_state.perfect_LSPP:
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
            st.caption("Es: 28.30")
            n = st.number_input("n", step=0.01)
            st.caption("Es: 0.31")
            alpha = st.number_input("α (alpha)", step=0.01)
            st.caption("Es: 0,29")
            k = st.number_input("k", step=0.01)
            st.caption("Es: -0,04")
            epsilon = st.number_input("ε (epsilon)", step=0.01)
            st.caption("Es: 0,82")
            T_ritorno = st.number_input("Tempo di ritorno", min_value=1, step=1)
            st.caption("Es: 50 e 100 anni")
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

                # Salvataggio in sessione
                st.session_state.update({
                    "T_ritorno": T_ritorno,
                    "volume": volume_minimo,
                    "altezza_vasca": round(volume_minimo / st.session_state.sup_verde, 2),
                })
            else:
                st.markdown("<div style='font-size:22px; margin-bottom:24px;'> Metodo utilizzato: <span style='color:red; font-weight:bold;'>Metodo delle sole piogge (art. 11 e Allegato G)</span></div>",
                    unsafe_allow_html=True
                )
                st.write(f"**Durata critica:** {TempoCritico} ore")
                st.write(f"**Volume da laminare:** {volume} mc")
                st.write(f"**Altezza vasca laminazione:** {round(volume / st.session_state.sup_verde, 2)} cm")

                # Salvataggio in sessione
                st.session_state.update({
                    "T_ritorno": T_ritorno,
                    "volume": volume,
                    "altezza_vasca": round(volume / st.session_state.sup_verde, 2),
                })

            st.session_state.method_2 = "True"
    else: 
        with st.form("form_lspp"):
            T_ritorno = st.number_input("Tempo di ritorno", min_value=1, step=1)
            st.caption("Es: 50 e 100 anni")
            submitted_2 = st.form_submit_button("Calcola")

        if submitted_2:
            # Ricava i parametri LSPP dal dataframe
            A1 = st.session_state.dati_comune["a1"]
            n = st.session_state.dati_comune["n"]
            alpha = st.session_state.dati_comune["alpha"]
            k = st.session_state.dati_comune["kappa"]
            epsilon = st.session_state.dati_comune["epsilon"]

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

                # Salvataggio in sessione
                st.session_state.update({
                    "T_ritorno": T_ritorno,
                    "volume": volume_minimo,
                    "altezza_vasca": round(volume_minimo / st.session_state.sup_verde, 2),
                })
            else:
                st.markdown("<div style='font-size:22px; margin-bottom:24px;'> Metodo utilizzato: <span style='color:red; font-weight:bold;'>Metodo delle sole piogge (art. 11 e Allegato G)</span></div>",
                    unsafe_allow_html=True
                )
                st.write(f"**Durata critica:** {TempoCritico} ore")
                st.write(f"**Volume da laminare:** {volume} mc")
                st.write(f"**Altezza vasca laminazione:** {round(volume / st.session_state.sup_verde, 2)} cm")

                # Salvataggio in sessione
                st.session_state.update({
                    "T_ritorno": T_ritorno,
                    "volume": volume,
                    "altezza_vasca": round(volume / st.session_state.sup_verde, 2),
                })

            st.session_state.method_2 = "True"

# === MANDARE UNA EMAIL ===
if st.session_state.method_2 != "Cipolla":
    st.title("Invio resoconto via mail")

    with st.form("email_form"):
        st.write("Salva dati")
        testo_aggiuntivo = st.text_area("Testo aggiuntivo da inserire (facoltativo):", height=150)
        submitted = st.form_submit_button("Salva")

        if submitted:
            ora_attuale = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            testo_email = f"""
            Buongiorno,

            di seguito si riportano i risultati del calcolo di invarianza idraulica effettuato in data {ora_attuale}.

            Informazioni contatto
            - Contatto: {st.session_state.contatto}
            - Figura del contatto: {st.session_state.figura_contatto}

            📍 **Locazione**
            - Regione: {st.session_state.regione}
            - Comune: {st.session_state.comune}
            - Indirizzo: {st.session_state.indirizzo}

            📐 **Dati superficiali**
            - Superficie totale: {st.session_state.sup_tot} m²
            - Superficie impermeabile: {st.session_state.sup_imm} m²
            - Superficie semi-permeabile: {st.session_state.sup_semi} m²
            - di cui verde pensile: {st.session_state.sup_verde} m²
            - Superficie permeabile: {st.session_state.sup_perm} m²

            🔎 **Parametri delle superfici**
            - Coefficiente di deflusso medio ponderale: {st.session_state.phi}
            - Criticità idraulica: {st.session_state.dati_comune["Criticità idraulica"]}
            - Coefficiente P: {st.session_state.coeff_P}
            - Metodo adottato per il calcolo dell’invaso: {st.session_state.method}
            - Portata massima ammissibile: {st.session_state.ULim} l/s/ha
            - Tempo di ritorno considerato: {st.session_state.T_ritorno} anni
            - Volume da laminare: {st.session_state.volume} m³
            - Altezza della vasca di laminazione: {st.session_state.altezza_vasca} cm

            Testo aggiuntivo: 
            {testo_aggiuntivo}
            """

            try:
                # Crea il messaggio email
                msg = EmailMessage()
                msg["Subject"] = "Resoconto incontro {ora_attuale}"
                msg["From"] = EMAIL_MITTENTE
                msg["To"] = DESTINATARIO
                msg.set_content(testo_email)

                # Invia la mail
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                    smtp.login(EMAIL_MITTENTE, PASSWORD_MITTENTE)
                    smtp.send_message(msg)

                st.success(f"Salvataggio effettuato con successo da {DESTINATARIO}!")

            except Exception as e:
                st.error(f"Errore nel salvataggio {e}")
