"""
Módulo de notificaciones para Telegram.
Envía mensajes con los cambios detectados en el scraping de perros.
"""

import os
import requests


def _get_creds():
    """Obtiene las credenciales de Telegram desde variables de entorno."""
    api = os.getenv("TELEGRAM_API")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    return api, chat_id


def _send_message(text):
    """Envía un mensaje de texto a Telegram con formato HTML."""
    api, chat_id = _get_creds()
    if not api or not chat_id:
        print("  ⚠️  TELEGRAM_API o TELEGRAM_CHAT_ID no configurados. Saltando notificación.")
        return False

    url = f"https://api.telegram.org/bot{api}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            print(f"  ⚠️  Error enviando mensaje Telegram: {resp.status_code} - {resp.text}")
            return False
        print("  ✅ Notificación enviada a Telegram.")
        return True
    except Exception as e:
        print(f"  ⚠️  Excepción al enviar mensaje Telegram: {e}")
        return False


def _send_photo(photo_path, caption=""):
    """Envía una foto a Telegram con caption en HTML."""
    api, chat_id = _get_creds()
    if not api or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{api}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "HTML",
            }
            resp = requests.post(url, files=files, data=data, timeout=15)
            if resp.status_code != 200:
                print(f"    ⚠️  Error enviando foto: {resp.status_code} - {resp.text}")
            return resp.status_code == 200
    except Exception as e:
        print(f"    ⚠️  Error enviando foto: {e}")
        return False


def _formatear_mensaje_perro(d, prefijo="🐾"):
    """Formatea un mensaje con los datos de un perro (formato HTML para Telegram)."""
    # Enlace a la imagen grande del perro (más informativo que la página general)
    enlace = f'https://www.vitoria-gasteiz.org/g06-02w/animal/list?especie.id=1'

    msg = (
        f"{prefijo} Perro {d['id']}\n"
        f"━━━━━━━━━━━━━━\n"
        f"Raza: {d.get('raza', '?')}\n"
        f"Sexo: {d.get('sexo', '?')}\n"
        f"Tamaño: {d.get('tamano', '?')}\n"
        f"Edad: {d.get('edad', '?')}\n"
    )
    if d.get("nota"):
        msg += f"Nota: {d['nota']}\n"
    msg += f"\nVer más: {enlace}"
    return msg


def notify_new_dogs(nuevos):
    """
    Envía notificación de perros nuevos encontrados.
    nuevos: lista de dicts con los datos de los perros nuevos.
    """
    if not nuevos:
        return

    for d in nuevos:
        msg = _formatear_mensaje_perro(d, prefijo="🆕")
        if d.get("local_img_path") and os.path.exists(d["local_img_path"]):
            _send_photo(d["local_img_path"], msg)
        else:
            _send_message(msg)


def notify_missing_dogs(desaparecidos_ids, df_master):
    """
    Envía notificación individual por cada perro desaparecido.
    desaparecidos_ids: lista de IDs (strings) que ya no aparecen.
    df_master: DataFrame con los datos históricos para obtener info de cada perro.
    """
    if not desaparecidos_ids:
        return

    for dog_id in desaparecidos_ids:
        try:
            row = df_master.loc[dog_id]
            raza = row.get("raza", "?")
            sexo = row.get("sexo", "?")
            tamano = row.get("tamano", "?")
            edad = row.get("edad", "?")
            enlace = "https://www.vitoria-gasteiz.org/g06-02w/animal/list?especie.id=1"
            msg = (
                f"❌ Perro {dog_id} ha desaparecido\n"
                f"━━━━━━━━━━━━━━\n"
                f"Raza: {raza}\n"
                f"Sexo: {sexo}\n"
                f"Tamaño: {tamano}\n"
                f"Edad: {edad}\n"
                f"\nPuede haber sido adoptado o dado de baja ✅\n"
                f"Ver listado: {enlace}"
            )
            img_path = row.get("local_img_path")
            if img_path and os.path.exists(img_path):
                _send_photo(img_path, msg)
            else:
                _send_message(msg)
        except (KeyError, TypeError):
            _send_message(f"❌ Perro {dog_id} ha desaparecido (datos no disponibles)")