import os
import json
from dotenv import load_dotenv

load_dotenv()

# RNF02: tempo máximo de espera por uma resposta do Gemini. Passou disso, a
# chamada levanta exceção e cada função de IA cai no seu fallback local.
GEMINI_TIMEOUT_SECONDS = float(os.getenv('GEMINI_TIMEOUT_SECONDS', '5'))


class GeminiClient:
    """
    Singleton — ponto único de acesso ao cliente da API Google Gemini.

    Evita reinstanciar a conexão/configuração da API a cada chamada de IA
    (transcrição, análise de imagem, urgência, duplicidade etc.), reaproveitando
    a mesma instância durante todo o ciclo de vida do processo Django.
    """

    _instance = None

    def __init__(self):
        if GeminiClient._instance is not None:
            raise RuntimeError(
                'GeminiClient já possui uma instância. Use GeminiClient.get_instance().'
            )
        self._api_key = os.getenv('GEMINI_API_KEY', '')
        self._client = None
        if self._api_key:
            try:
                from google import genai
                from google.genai import types
                self._client = genai.Client(
                    api_key=self._api_key,
                    # O SDK recebe o timeout em milissegundos.
                    http_options=types.HttpOptions(timeout=int(GEMINI_TIMEOUT_SECONDS * 1000)),
                )
            except Exception as e:
                print(f'[Gemini] Aviso: não foi possível inicializar o cliente — {e}')

    @classmethod
    def get_instance(cls) -> 'GeminiClient':
        """Retorna a instância única do cliente, criando-a na primeira chamada."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_available(self) -> bool:
        """True se a API key foi configurada e o client foi inicializado com sucesso."""
        return self._client is not None

    def processar_prompt(self, prompt: str, model: str = 'gemini-2.5-flash') -> str:
        """
        Ponto único de acesso ao modelo Gemini. Todas as funções de IA deste
        módulo passam por aqui em vez de falar direto com o SDK do Google.
        """
        if not self._client:
            return ''
        response = self._client.models.generate_content(model=model, contents=prompt)
        return response.text.strip()


def get_occurrence_ai_suggestion(title: str, category: str) -> str:
    gemini = GeminiClient.get_instance()
    if not gemini.is_available():
        return ''
    prompt = (
        f'Você é um assistente de gestão urbana. '
        f'Gere uma descrição técnica objetiva (máximo 200 caracteres) '
        f'para uma ocorrência da categoria "{category}" '
        f'com o título "{title}". '
        f'Responda apenas com a descrição, sem introdução ou explicação.'
    )
    try:
        return gemini.processar_prompt(prompt)
    except Exception as e:
        print(f'[Gemini] Erro ao gerar sugestão: {e}')
        return ''


def get_category_ai_description(name: str) -> str:
    gemini = GeminiClient.get_instance()
    if not gemini.is_available():
        return ''
    prompt = f'Me mostre uma descrição da categoria de problema urbano "{name}" em no máximo 250 caracteres.'
    try:
        return gemini.processar_prompt(prompt)
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

    gemini = GeminiClient.get_instance()
    if not gemini.is_available():
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
        raw = gemini.processar_prompt(prompt)
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

    gemini = GeminiClient.get_instance()
    if not gemini.is_available():
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
        raw = gemini.processar_prompt(prompt)
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


# ─────────────────────────────────────────────
# Análise de Foto e Descrição do Usuário (RF / UC Novo)
# ─────────────────────────────────────────────

VALID_ANALYSIS_STATUSES = {'MANTIDA', 'CORRIGIDA', 'SUBSTITUIDA', 'GERADA', 'FOTO_INSUFICIENTE'}

DESCRIPTION_ANALYSIS_SYSTEM_PROMPT = """Você é um assistente de análise de ocorrências de infraestrutura urbana. Receberá UMA foto e, opcionalmente, uma descrição do usuário. Siga estritamente as regras de negócio e responda no formato definido. Descreva apenas o que é visível na foto. Não explique seu raciocínio.

Regras de Negócio:
1. Se não houver descrição do usuário (ou se for apenas espaços em branco): GERAR a descrição a partir da foto. Defina o status como GERADA.
2. Se houver descrição do usuário, avaliar:
   - Correspondência com a foto. Informações que a foto não pode confirmar (rua, bairro, número, referência, data) NÃO são erro e devem ser sempre preservadas. Só é erro o que a foto contradiz diretamente.
   - Profundidade. Textos com menos de 25 caracteres exigem atenção, mas não são rasos automaticamente: um texto curto e objetivo que identifica o problema é aceitável. Raso é o texto genérico (ex.: "problema na rua") ou que não deixa claro qual é o problema.
3. Decisão de Status (uma das cinco):
   - MANTIDA: descrição correta e suficiente. O texto original NÃO pode ser alterado. Se a foto mostrar algo relevante não citado (ex.: risco a pedestres), retornar uma SUGESTÃO separada, sem mexer no texto.
   - CORRIGIDA: parcialmente errada. Corrigir SOMENTE o trecho contradito pela foto, mantendo o resto e as informações de local.
   - SUBSTITUIDA: totalmente diferente da foto, ou rasa/genérica. Substituir pela análise da IA, preservando as informações de local do usuário.
   - GERADA: não havia descrição do usuário.
   - FOTO_INSUFICIENTE: só quando, mesmo tentando, a IA não consegue identificar a situação real. Foto escura, distante ou ruim deve ser analisada normalmente.
4. Descrições geradas ou ajustadas: até 255 caracteres, português do Brasil, linguagem técnica e direta, descrevendo apenas o que é visível (tipo de problema, elemento afetado, extensão ou gravidade aparente, risco evidente). Sem inventar causa, nome de local ou medidas.

Retorne SOMENTE um JSON válido com a seguinte estrutura:
{
  "status": "MANTIDA|CORRIGIDA|SUBSTITUIDA|GERADA|FOTO_INSUFICIENTE",
  "descricao_final": "<descrição técnica objetiva de no máximo 255 caracteres>",
  "sugestao": "<frase curta de sugestão opcional quando status for MANTIDA e houver algo a acrescentar, caso contrário string vazia>"
}"""


def clean_truncate(text: str, max_len: int = 255) -> str:
    """
    Garante o limite de 255 caracteres para textos gerados/ajustados pela IA.
    Truncagem limpa sem cortar palavras ao meio.
    """
    if not text or len(text) <= max_len:
        return text or ""
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.rstrip('.,;:') + '...'


def analyze_occurrence_description_and_photo(image_file=None, description: str = "", title: str = "") -> dict:
    """
    Analisa a foto e a descrição do usuário antes de salvar a ocorrência.
    Retorna dicionário contendo status, descricao_final, sugestao e original_description.
    Em caso de falha/timeout ou resposta inválida, retorna o status FALHA e mantém o texto original.
    """
    original_desc = (description or "").strip()
    fallback_desc = original_desc if original_desc else (f"Ocorrência de {title} registrada." if title else "Ocorrência urbana registrada.")

    fallback_response = {
        'status': 'FALHA',
        'descricao_final': fallback_desc,
        'sugestao': '',
        'original_description': original_desc,
    }

    gemini = GeminiClient.get_instance()
    if not gemini.is_available():
        return fallback_response

    try:
        from PIL import Image
        contents = [DESCRIPTION_ANALYSIS_SYSTEM_PROMPT]

        if image_file:
            if hasattr(image_file, 'read'):
                try:
                    img = Image.open(image_file)
                    contents.append(img)
                    if hasattr(image_file, 'seek'):
                        image_file.seek(0)
                except Exception as img_err:
                    print(f"[Gemini] Aviso ao ler imagem: {img_err}")
            elif isinstance(image_file, Image.Image):
                contents.append(image_file)

        prompt_user = f"Título: '{title}'\nDescrição do Usuário: '{original_desc}'"
        contents.append(prompt_user)

        response = gemini._client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents
        )
        raw = (response.text or "").strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        data = json.loads(raw.strip())

        status_res = str(data.get('status', '')).upper()
        if status_res not in VALID_ANALYSIS_STATUSES:
            print(f"[Gemini] Status de IA inválido retornado: '{status_res}'")
            return fallback_response

        # Garantia no CÓDIGO de que em MANTIDA o texto salvo é exatamente o original do usuário
        if status_res == 'MANTIDA':
            final_desc = original_desc
        else:
            final_desc = clean_truncate(str(data.get('descricao_final', '')).strip(), 255)

        sugestao = str(data.get('sugestao', '')).strip() if status_res == 'MANTIDA' else ''

        return {
            'status': status_res,
            'descricao_final': final_desc,
            'sugestao': sugestao,
            'original_description': original_desc,
        }

    except Exception as e:
        print(f"[Gemini] Erro ou timeout na análise da foto/descrição: {e}")
        return fallback_response