import os
from typing import List, Dict
from pathlib import Path

def cargar_docs(context_dir) -> Dict[str, str]:
    docs = {}
    archivos = {
        "criterios": "contexto_criterios_hallazgos.md",
        "recomendaciones": "contexto_recomendaciones.md",
        "salida": "contexto_salida_estructurada.md",
    }
    context_dir = Path(context_dir)
    for key, nombre in archivos.items():
        full_path = context_dir / nombre
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                docs[key] = f.read()
        else:
            docs[key] = ""
    return docs

def chunkear(texto: str, doc_name: str) -> List[Dict]:
    chunks = []
    parrafos = texto.split("\n\n")
    for i, p in enumerate(parrafos):
        p_limpio = p.strip()
        if len(p_limpio) > 0:
            chunks.append({
                "doc": doc_name,
                "chunk_id": f"{doc_name}#p{i}",
                "text": p_limpio,
            })
    return chunks

def buscar_chunks(chunks: List[Dict], query_keywords: List[str], top_k: int = 3) -> List[Dict]:
    scored = []
    for ch in chunks:
        texto_lower = ch["text"].lower()
        score = 0
        for kw in query_keywords:
            if kw.lower() in texto_lower:
                score += 1
        if score > 0:
            scored.append((score, ch))

    # ordeno desc por score
    scored.sort(key=lambda x: x[0], reverse=True)
    return [ch for score, ch in scored[:top_k]]

def recuperar_contexto_para_hallazgo(chunks: List[Dict], hallazgo: Dict) -> List[str]:
    keywords = ["sobreconsumo", "severidad", "desviacion", "kwh", "hallazgo"]
    if hallazgo.get("severity") == "alta":
        keywords.append("Alta")
    elif hallazgo.get("severity") == "media":
        keywords.append("Media")
    else:
        keywords.append("Baja")

    encontrados = buscar_chunks(chunks, keywords, top_k=2)
    return [c["chunk_id"] for c in encontrados]

def recuperar_contexto_para_recomendacion(chunks: List[Dict]) -> List[str]:
    keywords = ["recomendaciones", "calibracion", "mantenimiento", "preliminar"]
    encontrados = buscar_chunks(chunks, keywords, top_k=2)
    return [c["chunk_id"] for c in encontrados]