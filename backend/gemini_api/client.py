import os
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY', '')

client = None
if api_key:
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f'[Gemini] Aviso: não foi possível inicializar o cliente — {e}')


def get_occurrence_ai_suggestion(title: str, category: str) -> str:
    if not client:
        return ''
    prompt = (
        f'Você é um assistente de gestão urbana. '
        f'Gere uma descrição técnica objetiva (máximo 200 caracteres) '
        f'para uma ocorrência da categoria "{category}" '
        f'com o título "{title}". '
        f'Responda apenas com a descrição, sem introdução ou explicação.'
    )
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f'[Gemini] Erro ao gerar sugestão: {e}')
        return ''


def get_category_ai_description(name: str) -> str:
    if not client:
        return ''
    prompt = f'Me mostre uma descrição da categoria de problema urbano "{name}" em no máximo 250 caracteres.'
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f'[Gemini] Erro ao gerar descrição de categoria: {e}')
        return ''


# ─────────────────────────────────────────────
# Palavras-chave para fallback local
# ─────────────────────────────────────────────

CRITICAL_KEYWORDS = [
    'morte', 'morreu', 'faleceu', 'vítima', 'vítimas', 'óbito',
    'urgente', 'emergência', 'perigo de vida', 'risco de morte',
    'explosão', 'explodiu', 'incêndio', 'pegou fogo',
    'atropelamento', 'atropelou', 'atropelado',
    'desabamento', 'desabou', 'desmoronamento', 'soterrado',
]

HIGH_KEYWORDS = [
    'acidente', 'batida', 'colisão', 'colidiu', 'capotou',
    'ferido', 'feridos', 'machucado', 'sangue', 'grave',
    'perigo', 'perigoso', 'risco',
    'vazamento de gás', 'gás', 'alagamento', 'enchente',
    'fio caído', 'poste caído', 'árvore caída', 'cratera',
]

MEDIUM_KEYWORDS = [
    'buraco', 'asfalto', 'calçada', 'iluminação', 'lâmpada',
    'semáforo', 'sinalização', 'lixo', 'entulho',
    'esgoto', 'fossa', 'cheiro', 'abandono', 'quebrado',
]


def _local_urgency_analysis(title: str, description: str) -> dict:
    text     = f'{title} {description}'.lower()
    detected = []

    critical_hits = sum(1 for kw in CRITICAL_KEYWORDS if kw in text and not detected.append(kw))
    high_hits     = sum(1 for kw in HIGH_KEYWORDS     if kw in text and not detected.append(kw))
    medium_hits   = sum(1 for kw in MEDIUM_KEYWORDS   if kw in text and not detected.append(kw))

    score = min(100, critical_hits * 35 + high_hits * 20 + medium_hits * 8)

    if critical_hits > 0 or score >= 70:
        level, color, reason = 'critical', 'red',    'Palavras-chave críticas detectadas no texto.'
    elif score >= 40:
        level, color, reason = 'high',     'red',    'Indicadores de alta urgência encontrados.'
    elif score >= 15:
        level, color, reason = 'medium',   'yellow', 'Problema de impacto moderado identificado.'
    else:
        level, color, reason = 'low',      'green',  'Sem indicadores críticos no texto.'

    return {
        'urgency_score':            score,
        'urgency_level':            level,
        'urgency_reason':           reason,
        'detected_keywords':        list(set(detected)),
        'suggested_importance_color': color,
    }


def _local_duplicate_detection(new_title: str, new_description: str, existing: list) -> dict:
    new_words  = set(f'{new_title} {new_description}'.lower().split())
    best_score = 0
    best_id    = None

    for occ in existing:
        occ_words = set(f'{occ["title"]} {occ["description"]}'.lower().split())
        if not occ_words or not new_words:
            continue
        intersection = len(new_words & occ_words)
        union        = len(new_words | occ_words)
        jaccard      = (intersection / union) * 100 if union > 0 else 0
        if jaccard > best_score:
            best_score = jaccard
            best_id    = occ['id']

    is_dup = best_score >= 40
    return {
        'is_duplicate':     is_dup,
        'duplicate_of_id':  best_id if is_dup else None,
        'similarity_score': round(best_score),
        'reason': (
            f'Similaridade de {round(best_score)}% com ocorrência #{best_id}.'
            if is_dup else 'Nenhuma ocorrência similar encontrada.'
        ),
    }


def analyze_occurrence_urgency(title: str, description: str) -> dict:
    """
    Analisa urgência da ocorrência por palavras-chave.
    Usa Gemini se disponível, senão aplica análise local.
    """
    local_result = _local_urgency_analysis(title, description)

    if not client:
        return local_result

    prompt = f"""Você é um especialista em gestão de emergências urbanas.
Analise a seguinte ocorrência e retorne SOMENTE um JSON válido, sem markdown, sem texto extra:

Título: "{title}"
Descrição: "{description}"

Retorne exatamente este JSON:
{{
  "urgency_score": <inteiro de 0 a 100>,
  "urgency_level": "<low|medium|high|critical>",
  "urgency_reason": "<frase curta em português, máximo 100 caracteres>",
  "detected_keywords": [<palavras-chave encontradas que indicam urgência>],
  "suggested_importance_color": "<green|yellow|red>"
}}

Critérios:
- critical (80-100, red): risco de vida, acidentes com vítimas, morte, incêndio, desabamento
- high (60-79, red): batida, colisão, vazamento, alagamento, buraco grande na pista
- medium (30-59, yellow): iluminação quebrada, semáforo com defeito, lixo acumulado
- low (0-29, green): problemas estéticos, calçada irregular, pintura apagada"""

    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        raw = response.text.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        result = json.loads(raw.strip())
        result.setdefault('urgency_score',            local_result['urgency_score'])
        result.setdefault('urgency_level',            local_result['urgency_level'])
        result.setdefault('urgency_reason',           local_result['urgency_reason'])
        result.setdefault('detected_keywords',        local_result['detected_keywords'])
        result.setdefault('suggested_importance_color', local_result['suggested_importance_color'])
        return result
    except Exception as e:
        print(f'[Gemini] Erro na análise de urgência: {e}')
        return local_result


def detect_duplicate_occurrences(new_title: str, new_description: str, existing_occurrences: list) -> dict:
    """
    Verifica se a nova ocorrência é duplicata de alguma existente.
    Usa Gemini se disponível, senão aplica similaridade local (Jaccard).
    """
    if not existing_occurrences:
        return {
            'is_duplicate':     False,
            'duplicate_of_id':  None,
            'similarity_score': 0,
            'reason':           'Nenhuma ocorrência próxima encontrada para comparação.',
        }

    local_result = _local_duplicate_detection(new_title, new_description, existing_occurrences)

    if not client:
        return local_result

    candidates_text = ''
    for occ in existing_occurrences[:5]:
        candidates_text += (
            f'\n- ID {occ["id"]}: Título="{occ["title"]}" | '
            f'Descrição="{occ["description"][:150]}"'
        )

    prompt = f"""Você é um especialista em análise de ocorrências urbanas.

Nova ocorrência:
- Título: "{new_title}"
- Descrição: "{new_description}"

Ocorrências existentes na mesma área:{candidates_text}

Retorne SOMENTE um JSON válido, sem markdown:
{{
  "is_duplicate": <true|false>,
  "duplicate_of_id": <id da ocorrência duplicada ou null>,
  "similarity_score": <inteiro 0-100>,
  "reason": "<frase curta em português, máximo 150 caracteres>"
}}

Considere duplicata se o problema é essencialmente o mesmo no mesmo local (score >= 70)."""

    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        raw = response.text.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        result = json.loads(raw.strip())
        result.setdefault('is_duplicate',     local_result['is_duplicate'])
        result.setdefault('duplicate_of_id',  local_result['duplicate_of_id'])
        result.setdefault('similarity_score', local_result['similarity_score'])
        result.setdefault('reason',           local_result['reason'])
        return result
    except Exception as e:
        print(f'[Gemini] Erro na detecção de duplicatas: {e}')
        return local_result