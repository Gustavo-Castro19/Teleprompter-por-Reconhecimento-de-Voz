# Guarda caminhos, thresholds, cooldowns, modo de teste, modelo Vosk e configurações de rolagem.
# Centraliza as configurações gerais do sistema, como caminhos,
# limites de similaridade, cobertura mínima e intervalo de avanço.

# --- CONFIGURAÇÕES ---
CONFIG = {
    # Caminho da pasta do modelo Vosk
    "caminho_modelo": "model",
    
    # Caminho do roteiro/espelho do NewsHub
    # Atenção: esse arquivo precisa estar dentro da pasta "roteiros"
    "caminho_roteiro": "roteiros/BDDF-07042026.txt",

    # Similaridade mínima para leitura sequencial
    "limite_similaridade": 0.60, 

    # Valores para consideração de saltos globais
    "caracteres_minimos": 37,  
    "limite_similaridade_alto": 0.92,  
    "limite_similaridade_baixo": 0.88,   

    # Mínimo de caracteres reconhecidos para tentar qualquer match
    "caracteres_minimos_reconhecimento": 8,

    # Cobertura mínima da linha que precisa ter sido falada antes de avançar.
    # Ex: linha tem 60 chars → precisa ter falado >= 33 chars (ratio 0.55)
    # Baixo demais = avanço precoce | Alto demais = precisa repetir a frase
    "cobertura_minima_final": 0.65, 

    # Na cobertura para parciais a exigência é um pouco maior (transcrição ainda incompleta)
    "cobertura_minima_parcial": 0.70, 
    
    "avanco_parcial": 0.88,

    # Segundos bloqueados após cada avanço de linha.
    # Impede cascata sem travar o ritmo normal de leitura.
    "intervalo_avanco": 1.0,
}