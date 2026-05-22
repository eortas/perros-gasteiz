import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from telegram_bot import notify_new_dogs, notify_missing_dogs

# Cargar .env si existe (para ejecución local)
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()

BASE_URL = "https://www.vitoria-gasteiz.org"
LIST_URL = f"{BASE_URL}/g06-02w/animal/list?especie.id=1&idioma=es"
IMG_DIR = "fotos_perros"
CSV_FILE = "perros_vitoria_historico.csv"

os.makedirs(IMG_DIR, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_soup(url):
    """Realiza la petición GET y devuelve un objeto BeautifulSoup."""
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code != 200:
        print(f"  Error HTTP {response.status_code} en {url}")
        return None
    return BeautifulSoup(response.text, "html.parser")


def parse_dog_card(card):
    """Extrae los datos de un perro desde un <li class='gallery__item'>."""
    # --- ID (título) ---
    title_el = card.find("div", class_="gallery__item-title")
    if not title_el:
        return None
    dog_id = title_el.get_text(strip=True)
    if not dog_id.isdigit():
        return None

    # --- Textos (Raza, Sexo, Tamaño, Edad) ---
    text_divs = card.find_all("div", class_="gallery__item-text")
    data = {"id": dog_id, "raza": None, "sexo": None, "tamano": None, "edad": None}
    for div in text_divs:
        # Normalizar whitespace: cualquier secuencia de \n\r\t espacios -> un solo espacio
        raw = ' '.join(div.get_text(strip=False).split())
        # El texto viene como "Raza : Sabueso Español" -> separar por ":"
        if ":" in raw:
            key, _, valor = raw.partition(":")
            key = key.strip()
            valor = valor.strip()
            mapping = {"Raza": "raza", "Sexo": "sexo", "Tamaño": "tamano", "Edad": "edad"}
            if key in mapping:
                data[mapping[key]] = valor

    # Si no tiene raza, descartamos
    if not data["raza"]:
        return None

    # --- Nota ---
    foot_divs = card.find_all("div", class_="gallery__item-foot")
    notas = []
    for fd in foot_divs:
        txt = fd.get_text(strip=True)
        if txt.startswith("Nota"):
            nota_val = txt[len("Nota"):].lstrip(":").strip()
            notas.append(nota_val)
    data["nota"] = "; ".join(notas) if notas else None

    # --- Fecha de publicación ---
    data["fecha_publicacion"] = None
    for fd in foot_divs:
        txt = fd.get_text(strip=True)
        if txt and not txt.startswith("Nota"):
            data["fecha_publicacion"] = txt

    # --- Imagen ---
    img_tag = card.find("img", class_="gallery__item-image")
    data["img_url"] = None
    data["img_url_full"] = None
    data["local_img_path"] = None

    if img_tag and img_tag.get("src"):
        data["img_url"] = img_tag["src"]  # ya es URL absoluta

        # La versión completa (sin _clip) está en el <a> que envuelve al <img>
        parent_a = img_tag.find_parent("a")
        if parent_a and parent_a.get("href"):
            data["img_url_full"] = parent_a["href"]

    # Descargar la imagen (usando la _clip que es más ligera para miniatura)
    if data["img_url"]:
        filename = f"{dog_id}.jpg"
        filepath = os.path.join(IMG_DIR, filename)
        if not os.path.exists(filepath):
            try:
                img_res = requests.get(data["img_url"], headers=headers, timeout=10)
                if img_res.status_code == 200:
                    with open(filepath, "wb") as f:
                        f.write(img_res.content)
                    data["local_img_path"] = filepath
            except Exception as e:
                print(f"    Error descargando imagen {dog_id}: {e}")
        else:
            data["local_img_path"] = filepath

    return data


def total_pages(soup):
    """Calcula el número total de páginas desde los enlaces de paginación."""
    page_links = []
    for a in soup.find_all("a", href=True):
        if "offset=" in a["href"]:
            txt = a.get_text(strip=True)
            if txt.isdigit():
                page_links.append(int(txt))
    return max(page_links) if page_links else 1


def sync_scraped_data():
    today_str = datetime.now().strftime("%Y-%m-%d")
    all_dogs = []

    # --- 1. Scrapear la primera página ---
    print("Scrapeando página 1...")
    soup = get_soup(LIST_URL)
    if soup is None:
        return

    cards = soup.find_all("li", class_="gallery__item")
    print(f"  Perros encontrados en página 1: {len(cards)}")
    for card in cards:
        dog_data = parse_dog_card(card)
        if dog_data:
            all_dogs.append(dog_data)

    # --- 2. Paginación ---
    total = total_pages(soup)
    if total > 1:
        for page in range(2, total + 1):
            offset = (page - 1) * 10
            page_url = f"{BASE_URL}/g06-02w/animal/list?especie.id=1&offset={offset}&max=10"
            print(f"Scrapeando página {page} (offset={offset})...")
            soup_p = get_soup(page_url)
            if soup_p is None:
                continue
            cards_p = soup_p.find_all("li", class_="gallery__item")
            print(f"  Perros encontrados: {len(cards_p)}")
            for card in cards_p:
                dog_data = parse_dog_card(card)
                if dog_data:
                    all_dogs.append(dog_data)

    if not all_dogs:
        print("No se encontraron perros en la web.")
        return

    print(f"Total perros scrapeados: {len(all_dogs)}")

    # --- 3. Crear DataFrame con la captura de hoy ---
    df_current = pd.DataFrame(all_dogs).set_index("id")
    df_current["estado"] = "activo"
    df_current["fecha_deteccion"] = today_str
    df_current["fecha_desaparicion"] = None

    # --- 4. Cargar CSV maestro o crearlo ---
    if os.path.exists(CSV_FILE):
        df_master = pd.read_csv(CSV_FILE, dtype={"id": str}).set_index("id")
    else:
        df_current.to_csv(CSV_FILE, encoding="utf-8")
        print(f"Archivo inicial creado con {len(df_current)} perros activos.")
        return

    # --- 5. Detectar bajas ---
    perros_activos_anteriormente = df_master[df_master["estado"] == "activo"].index
    perros_hoy = df_current.index
    ids_desaparecidos = perros_activos_anteriormente.difference(perros_hoy)

    if not ids_desaparecidos.empty:
        print(f"Detectados {len(ids_desaparecidos)} perros que desaparecen del catálogo.")
        df_master.loc[ids_desaparecidos, "estado"] = "desaparecido"
        df_master.loc[ids_desaparecidos, "fecha_desaparicion"] = today_str

    # --- 6. Detectar perros NUEVOS (no estaban en el maestro antes del upsert) ---
    ids_nuevos = perros_hoy.difference(df_master.index)
    nuevos_df = df_current.loc[ids_nuevos].reset_index().to_dict("records") if not ids_nuevos.empty else []

    # --- 7. Upsert de datos nuevos/actualizados ---
    for idx, row in df_current.iterrows():
        if idx in df_master.index:
            df_master.loc[idx, ["raza", "sexo", "tamano", "edad", "nota",
                                "fecha_publicacion", "img_url", "img_url_full",
                                "local_img_path", "estado"]] = [
                row["raza"], row["sexo"], row["tamano"], row["edad"], row["nota"],
                row["fecha_publicacion"], row["img_url"], row["img_url_full"],
                row["local_img_path"], "activo"
            ]
            df_master.loc[idx, "fecha_desaparicion"] = None
        else:
            df_master.loc[idx] = row

    # --- 8. Guardar CSV ---
    df_master.sort_index().to_csv(CSV_FILE, encoding="utf-8")
    print(f"Sincronización finalizada. Perros en la web hoy: {len(df_current)}.")

    # --- 9. Notificaciones Telegram ---
    if not ids_nuevos.empty:
        print(f"Notificando {len(ids_nuevos)} perro(s) nuevo(s)...")
        notify_new_dogs(nuevos_df)

    if not ids_desaparecidos.empty:
        print(f"Notificando {len(ids_desaparecidos)} perro(s) desaparecido(s)...")
        notify_missing_dogs(ids_desaparecidos, df_master)


if __name__ == "__main__":
    sync_scraped_data()
