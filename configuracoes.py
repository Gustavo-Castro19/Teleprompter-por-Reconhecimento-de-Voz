# Guarda caminhos, thresholds, cooldowns, modo de teste, modelo Vosk e configurações de rolagem.
# Centraliza as configurações gerais do sistema.

CONFIG = {
    # Caminho da pasta do modelo Vosk.
    "caminho_modelo": "model",

    # Caminho do roteiro/espelho do NewsHub/iNEWS.
    # Atenção: esse arquivo precisa existir no projeto.
    "caminho_roteiro": "roteiros/roteiro_demo_bddf.json",

    # Ritmo usado apenas quando o JSON não trouxer tempo confiável.
    "palavras_por_minuto_base": 150,

    # Velocidade mínima/máxima de segurança no frontend.
    "velocidade_minima_rolagem": 0.05,
    "velocidade_maxima_rolagem": 3.0,

    # Pausa curta usada em separadores/reticências quando não há tempo oficial.
    "pausa_curta_segundos": 0.6,

    # Similaridade mínima para leitura sequencial.
    "limite_similaridade": 0.60,

    # Valores para consideração de saltos globais.
    "caracteres_minimos": 37,
    "limite_similaridade_alto": 0.92,
    "limite_similaridade_baixo": 0.88,

    # Mínimo de caracteres reconhecidos para tentar qualquer match.
    "caracteres_minimos_reconhecimento": 8,

    # Cobertura mínima da linha que precisa ter sido falada antes de avançar.
    "cobertura_minima_final": 0.65,

    # Na cobertura para parciais a exigência é um pouco maior.
    "cobertura_minima_parcial": 0.70,

    "avanco_parcial": 0.88,

    # Segundos bloqueados após cada avanço de linha.
    "intervalo_avanco": 0.30,

    # Se o apresentador falar algo que não bate com a linha esperada,
    # o sistema entra em improviso e pausa a rolagem visual.
    "habilitar_improviso": True,

    # Quantidade mínima de palavras em resultado final para considerar improviso.
    "min_palavras_improviso": 3,

    # ============================================================
    # AJUSTES DA ROLAGEM ASSISTIDA POR VOZ
    # ============================================================

    # Score mínimo para considerar que a fala está acompanhando o roteiro
    # e enviar progresso ao frontend mesmo antes de avançar linha.
    "score_minimo_andamento_voz": 0.35,

    # Score mínimo para considerar que uma fala voltou ao roteiro
    # depois de improviso ou pausa técnica.
    "score_minimo_retorno_roteiro": 0.55,

    # Tempo que o frontend espera sem match antes de travar a rolagem
    # por improviso. Evita pausar por erro rápido do Vosk.
    "tempo_sem_match_para_improviso_ms": 1200,

    # Suavidade da adaptação de velocidade no frontend.
    # Maior = reage mais rápido; menor = visual mais suave.
    "suavidade_velocidade_voz": 0.08,

}
