from pathlib import Path
from typing import Dict, List, Optional

EXTS_PERMITIDAS = {".md", ".txt"}

def cargar_docs(context_dir) -> Dict[str, str]:
    context_dir = Path(context_dir)
    docs: Dict[str, str] = {}
    if not context_dir.exists():
        return docs
    for p in sorted(context_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in EXTS_PERMITIDAS:
            continue
        try:
            docs[p.stem] = p.read_text(encoding="utf-8")
        except OSError:
            continue
    return docs

def chunkear(texto: str, doc_name: str) -> List[Dict]:
    chunks: List[Dict] = []
    parrafos = texto.split("\n\n")
    for i, p in enumerate(parrafos):
        limpio = p.strip()
        if len(limpio) > 0:
            chunks.append({
                "doc": doc_name,
                "chunk_id": f"{doc_name}#p{i}",
                "text": limpio,
            })
    return chunks

def buscar_chunks(chunks: List[Dict], query_keywords: List[str], top_k: int = 3) -> List[Dict]:
    scored = []
    for ch in chunks:
        texto_lower = ch["text"].lower()
        score = sum(1 for kw in query_keywords if kw.lower() in texto_lower)
        if score > 0:
            scored.append((score, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [ch for _, ch in scored[:top_k]]

def recuperar_contexto_para_hallazgo(chunks: List[Dict], hallazgo: Dict) -> List[str]:
    keywords = ["sobreconsumo", "severidad", "desviacion", "kwh", "hallazgo"]
    sev = hallazgo.get("severity")
    if sev == "alta":
        keywords.append("alta")
    elif sev == "media":
        keywords.append("media")
    elif sev == "baja":
        keywords.append("baja")
    encontrados = buscar_chunks(chunks, keywords, top_k=2)
    return [c["chunk_id"] for c in encontrados]

def recuperar_contexto_para_recomendacion(chunks: List[Dict]) -> List[str]:
    keywords = ["recomendaciones", "calibracion", "mantenimiento", "preliminar"]
    encontrados = buscar_chunks(chunks, keywords, top_k=2)
    return [c["chunk_id"] for c in encontrados]