# Tech Week 5

Una aplicación en Streamlit que selecciona cinco noticias tecnológicas relevantes publicadas durante los últimos siete días.

## Qué hace

- Agrega RSS de TechCrunch, WIRED, Ars Technica, The Verge y BBC Technology.
- Mantiene únicamente artículos de los últimos 7 días.
- Agrupa titulares similares para no repetir la misma historia.
- Da más peso a temas cubiertos por varias fuentes.
- Añade señales de impacto (IA, chips, ciberseguridad, regulación, grandes tecnológicas, adquisiciones, etc.).
- Evita que el top 5 quede dominado por un solo tema.
- Enlaza al artículo original.

## Ejecutarla en tu computadora

1. Instala Python 3.10 o superior.
2. Abre una terminal dentro de esta carpeta.
3. Crea un entorno virtual:

   python -m venv .venv

4. Actívalo.

   macOS / Linux:
   source .venv/bin/activate

   Windows:
   .venv\Scripts\activate

5. Instala dependencias:

   pip install -r requirements.txt

6. Inicia la app:

   streamlit run app.py

Streamlit abrirá automáticamente la aplicación en el navegador.

## Publicarla gratis con Streamlit Community Cloud

1. Crea un repositorio en GitHub y sube `app.py` y `requirements.txt`.
2. Entra a Streamlit Community Cloud.
3. Crea una nueva app apuntando al repositorio.
4. Selecciona `app.py` como archivo principal.
5. Deploy.

## Cómo decide qué es “importante”

No existe una medida objetiva única. Este MVP utiliza una heurística:

1. Cobertura cruzada: una historia mencionada por varias fuentes obtiene más peso.
2. Recencia: las publicaciones más nuevas de la semana tienen ventaja.
3. Señales de impacto: regulación, ciberseguridad, IA, chips, Big Tech, adquisiciones, etc.
4. Diversidad: limita la concentración excesiva de un mismo tipo de noticia.

Para una versión 2 se puede sustituir el ranking heurístico por un modelo de IA que evalúe impacto global, genere resúmenes en español y explique por qué cada noticia entra en el top 5.
