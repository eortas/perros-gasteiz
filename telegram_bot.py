"""
Módulo de notificaciones para Telegram.
Envía mensajes con los cambios detectados en el scraping de perros.
"""

import os
import requests

TELEGRAM_API = os.getenv("TELEGRAM_API")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_API}/sendMessage"
TELEGRAM_API_PHOTO = f"https://api.telegram.org/bot{TELEGRAM_API}/sendPhoto"


def _send_message(text, parse_mode="HTML"):
    """Envía un mensaje de texto a Telegram."""
    if not TELEGRAM_API or not TELEGRAM_CHAT_ID:
        print("  ⚠️  TELEGRAM_API o TELEGRAM_CHAT_ID no configurados. Saltando notificación.")
        return False

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)
        if resp.status_code != 200:
            print(f"  ⚠️  Error enviando mensaje Telegram: {resp.status_code} - {resp.text}")
            return False
        print("  ✅ Notificación enviada a Telegram.")
        return True
    except Exception as e:
        print(f"  ⚠️  Excepción al enviar mensaje Telegram: {e}")
        return False


def _send_photo(chat_id, photo_path, caption=""):
    """Envía una foto a Telegram."""
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": chat_id, "caption": caption}
            resp = requests.post(TELEGRAM_API_PHOTO, files=files, data=data, timeout=15)
            return resp.status_code == 200
    except Exception as e:
        print(f"    ⚠️  Error enviando foto: {e}")
        return False


def notify_new_dogs(nuevos):
    """
    Envía notificación de perros nuevos encontrados.
    nuevos: lista de dicts con los datos de los perros nuevos.
    """
    if not nuevos:
        return

    # Mensaje resumen
    nombres = []
    for d in nuevos:
        nombre = f"🆕 <b>{d['id']}</b> - {d.get('raza', '?')} ({d.get('sexo', '?')}, {d.get('edad', '?')})"
        nombres.append(nombre)

    resumen = (
        f"🐾 <b>¡{len(nuevos)} perro(s) nuevo(s) en adopción!</b>\n\n"
        + "\n".join(nombres)
        + "\n\n🔗 <a href='https://www.vitoria-gasteiz.org/g06-02w/animal/list?especie.id=1'>Ver en la web</a>"
    )
    _send_message(resumen)

    # Enviar foto del primer perro nuevo si existe
    if nuevos and nuevos[0].get("local_img_path") and os.path.exists(nuevos[0]["local_img_path"]):
        cap = f"🆕 {nuevos[0]['id']} - {nuevos[0].get('raza', '?')}"
        _send_photo(TELEGRAM_CHAT_ID, nuevos[0]["local_img_path"], cap)


def notify_missing_dogs(desaparecidos_ids, df_master):
    """
    Envía notificación de perros que han desaparecido del listado.
    desaparecidos_ids: lista de IDs (strings) que ya no aparecen.
    df_master: DataFrame con los datos históricos para obtener info de cada perro.
    """
    if not desaparecidos_ids:
        return

    lineas = []
    for dog_id in desaparecidos_ids:
        try:
            row = df_master.loc[dog_id]
            raza = row.get("raza", "?")
            sexo = row.get("sexo", "?")
            edad = row.get("edad", "?")
            lineas.append(f"❌ <b>{dog_id}</b> - {raza} ({sexo}, {edad})")
        except (KeyError, TypeError):
            lineas.append(f"❌ <b>{dog_id}</b> - datos no disponibles")

    msg = (
        f"⚠️ <b>{len(desaparecidos_ids)} perro(s) han desaparecido del catálogo</b>\n"
        "(pueden haber sido adoptados o dados de baja)\n\n"
        + "\n".join(lineas)
    )
    _send_message(msg)