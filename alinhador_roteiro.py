# Responsável por alinhar a linha falada com a linha exibida na interface.
# Usa o mapa falar_para_exibir para saber onde a seta deve aparecer na tela.


class AlinhadorRoteiro:
    def __init__(self, falar_para_exibir, linhas_exibidas):
        # Mapa que liga cada linha falada ao índice da linha exibida na interface.
        self.falar_para_exibir = falar_para_exibir

        # Lista com todas as linhas que aparecem visualmente no teleprompter.
        self.linhas_exibidas = linhas_exibidas

    def obter_indice_visual(self, idx):
        # idx representa o índice da linha falada atual.
        # mostrar_idx representa o índice da linha que será destacada na interface.
        if idx < len(self.falar_para_exibir):
            mostrar_idx = self.falar_para_exibir[idx]
        else:
            mostrar_idx = len(self.linhas_exibidas) - 1

        return mostrar_idx

    def obter_primeiro_indice_visual(self):
        # first_idx representa o primeiro índice visual usado quando o cliente conecta.
        first_idx = self.falar_para_exibir[0] if self.falar_para_exibir else 0
        return first_idx