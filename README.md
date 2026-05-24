# Teleprompter por Reconhecimento de Voz — SQUAD 29

O **Teleprompter por Reconhecimento de Voz** é um MVP desenvolvido pela **Squad 29** com o objetivo de automatizar a rolagem de um teleprompter a partir da fala do apresentador.

A solução utiliza reconhecimento de voz em tempo real para identificar o trecho do roteiro que está sendo lido e, com base nisso, avançar automaticamente a posição do texto. O projeto foi pensado para reduzir a dependência de operação manual, melhorar a fluidez da apresentação e diminuir riscos de dessincronia entre fala e roteiro.

Nesta versão, o sistema utiliza o **Vosk**, uma tecnologia de reconhecimento de fala offline, em conjunto com Python e captura de áudio local pelo microfone.

---
## 1. Status atual do MVP

O projeto encontra-se em fase de desenvolvimento e validação técnica.

Atualmente, a equipe já desenvolveu a base principal do sistema, incluindo:

- leitura e processamento do roteiro em JSON;
- processamento da estrutura editorial disponibilizada pela Globo;
- separação entre texto exibido no teleprompter e texto falado pelo apresentador;
- preservação de comandos técnicos na visualização;
- remoção de comandos técnicos do texto usado para reconhecimento;
- captura de áudio pelo microfone;
- reconhecimento de fala com Vosk;
- geração de transcrições parciais e finais;
- normalização do texto reconhecido;
- comparação entre fala reconhecida e roteiro;
- desenvolvimento da interface visual em HTML, CSS e JavaScript.

Ainda estão em desenvolvimento ou em fase de integração:

- controle final de avanço da rolagem;
- controle de estados internos do sistema;
- integração entre backend/API e interface web;
- testes mais completos em diferentes computadores e cenários de uso.

A interface visual do MVP já foi desenvolvida em *HTML, CSS e JavaScript*. No estágio atual, a principal pendência técnica é a integração entre essa interface e o backend/API responsável pelo processamento do roteiro, reconhecimento de fala e controle da rolagem automática.

# 2. Tecnologias utilizadas

- Python 3.13.x
- Vosk
- PyAudio
- Flask
- Flask-SocketIO
- Eventlet
- HTML
- CSS
- JavaScript
- Git/GitHub
- VS Code

## Versão do Python

Durante o desenvolvimento e os testes do MVP, a equipe utilizou Python 3.13.


## 3. Estrutura do projeto

O sistema utiliza roteiros em formato JSON, seguindo uma estrutura semelhante à disponibilizada pela Globo. Esses arquivos contêm informações do espelho jornalístico, como retrancas, páginas, apresentadores, textos de fala, comandos técnicos, marcações de produção e blocos de conteúdo.

O backend processa esse JSON para gerar duas estruturas principais:

- **linhas exibidas:** conteúdo que aparece visualmente no teleprompter, incluindo comandos técnicos;
- **linhas faláveis:** conteúdo usado para comparação com a fala do apresentador, sem comandos técnicos.

Abaixo está uma visão geral dos principais arquivos e pastas do projeto:

```text
projeto/
├── app.py
├── alinhador_roteiro.py
├── configuracoes.py
├── controlador_rolagem.py
├── maquina_estados.py
├── modelos.py
├── motor_audio.py
├── normalizador_texto.py
├── processador_roteiro.py
├── reconhecedor_fala.py
├── registrador_eventos.py
├── seguranca.py
├── roteiros/
│   └── roteiro_teste.json
├── model/
│   └── modelo Vosk em português
├── static/
├── templates/
├── requirements.txt
└── README.md
```

### Função dos principais arquivos

| Arquivo | Função |
|---|---|
| `app.py` | Arquivo principal do sistema. Inicializa o roteiro, o reconhecedor de fala, o microfone e o loop principal de execução. |
| `processador_roteiro.py` | Processa o roteiro em JSON, separando o texto exibido no teleprompter do texto falado pelo apresentador. |
| `reconhecedor_fala.py` | Inicializa e utiliza o Vosk para transformar áudio em texto parcial ou final. |
| `motor_audio.py` | Abre, lê e fecha o microfone utilizando PyAudio. |
| `controlador_rolagem.py` | Compara a fala reconhecida com o roteiro e decide quando avançar a rolagem. |
| `normalizador_texto.py` | Normaliza textos, removendo acentos, pontuação e diferenças de formatação. |
| `maquina_estados.py` | Controla estados internos do sistema, como automático, pausado, finalizado, falha e improviso. |
| `alinhador_roteiro.py` | Relaciona a linha falada com a linha visual exibida na interface. |
| `configuracoes.py` | Guarda caminhos, limites de similaridade e parâmetros de execução. |
| `registrador_eventos.py` | Centraliza mensagens e eventos exibidos no terminal. |
| `seguranca.py` | Centraliza funções iniciais relacionadas à segurança e ocultação de dados sensíveis. |
| `modelos.py` | Define estruturas de dados que podem apoiar comparações, eventos e segmentos do roteiro. |


## 4. Passo a passo de instalação e execução

A seguir está o guia completo para rodar o MVP do zero em um computador **Windows**, mesmo sem conhecimento técnico prévio.

---

## 4.1 Pré-requisitos

Antes de executar o projeto, é necessário instalar alguns programas e arquivos.

### Python

O projeto foi desenvolvido/testado com **Python 3.13.x** ou versão compatível.

Baixe o Python pelo site oficial:

[Baixar Python](https://www.python.org/downloads/)

Durante a instalação, marque a opção:

```text
Add Python to PATH
```

Essa opção permite usar os comandos `python` e `pip` diretamente no terminal.

Para verificar se o Python foi instalado corretamente, abra o terminal e execute:

```bash
python --version
```

Caso o comando `python` não funcione, tente:

```bash
py --version
```

---

### Git

O Git será usado para clonar o repositório do projeto.

Baixe pelo site oficial:

[Baixar Git](https://git-scm.com/downloads)

Durante a instalação, pode seguir clicando em **Next** até finalizar, mantendo as opções padrão.

Para verificar se o Git foi instalado corretamente, execute:

```bash
git --version
```

---

### VS Code

Recomenda-se utilizar o Visual Studio Code para abrir e executar o projeto.

Baixe pelo site oficial:

[Baixar Visual Studio Code](https://code.visualstudio.com/)

---

### Modelo Vosk em português

O sistema utiliza o **Vosk** para reconhecimento de fala offline. O modelo de voz não fica salvo diretamente no GitHub, então precisa ser baixado manualmente.

Acesse a página oficial de modelos:

[Baixar modelos Vosk](https://alphacephei.com/vosk/models)

Procure por **Portuguese** e baixe o modelo:

```text
vosk-model-pt-fb-v0.1.1-20220516_2113
```

---

## 4.2 Baixando o projeto

Escolha uma pasta no computador onde deseja salvar o projeto.

Abra o terminal nessa pasta e execute:

```bash
git clone [INSERIR_LINK_DO_REPOSITORIO]
```

Depois, entre na pasta do projeto:

```bash
cd [NOME_DA_PASTA_DO_PROJETO]
```

Exemplo:

```bash
cd teleprompter-squad-29
```

---

## 4.3 Configurando o modelo Vosk

Depois de baixar o modelo `vosk-model-pt-fb-v0.1.1-20220516_2113`, siga os passos:

1. Extraia o arquivo `.zip`;
2. Renomeie a pasta extraída para:

```text
model
```

3. Mova a pasta `model` para dentro da pasta principal do projeto, no mesmo nível do arquivo `app.py`.

A estrutura esperada deve ficar assim:

```text
projeto/
├── app.py
├── model/
│   └── arquivos do modelo Vosk
├── roteiros/
│   └── roteiro_teste.json
├── static/
├── templates/
├── requirements.txt
└── README.md
```

Se a pasta continuar com o nome original, como:

```text
vosk-model-pt-fb-v0.1.1-20220516_2113
```

o sistema pode não encontrar o modelo. Por isso, renomeie para:

```text
model
```

---

## 4.4 Criando o ambiente virtual

Com o terminal aberto dentro da pasta do projeto, execute:

```bash
python -m venv venv
```

Caso o comando `python` não funcione, tente:

```bash
py -m venv venv
```

Caso ainda não funcione, utilize o caminho completo do Python instalado na máquina.

Exemplo no PowerShell:

```powershell
& "C:\Users\leandro_santos\AppData\Local\Programs\Python\Python313\python.exe" -m venv venv
```

Exemplo no CMD:

```cmd
"C:\Users\leandro_santos\AppData\Local\Programs\Python\Python313\python.exe" -m venv venv
```

> Atenção: o caminho acima é apenas um exemplo. Em outro computador, o caminho pode ser diferente.

---

## 4.5 Ativando o ambiente virtual

### No CMD

```cmd
venv\Scripts\activate
```

### No PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação do ambiente virtual, execute:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Depois tente ativar novamente:

```powershell
.\venv\Scripts\Activate.ps1
```

Quando o ambiente virtual estiver ativo, o terminal deve mostrar algo parecido com:

```text
(venv) C:\caminho\do\projeto>
```

---

## 4.6 Instalando as dependências

Com o ambiente virtual ativado, instale as dependências do projeto:

```bash
python -m pip install -r requirements.txt
```

Caso o arquivo `requirements.txt` ainda não esteja disponível, instale manualmente:

```bash
python -m pip install flask flask-socketio eventlet vosk pyaudio
```

Caso o comando `pip` não seja reconhecido, utilize sempre:

```bash
python -m pip
```

Para verificar se o `pip` está funcionando:

```bash
python -m pip --version
```

Para atualizar o `pip`:

```bash
python -m pip install --upgrade pip
```

---

## 4.7 Instalando o PyAudio no Windows

O PyAudio pode apresentar erro de instalação em alguns computadores com Windows.

Tente primeiro:

```bash
python -m pip install pyaudio
```

Se não funcionar, tente:

```bash
python -m pip install pipwin
pipwin install pyaudio
```

Caso ainda apresente erro, pode ser necessário buscar uma versão compatível do PyAudio com a versão do Python instalada.

---

## 4.8 Executando o sistema

Com o ambiente virtual ativado e as dependências instaladas, execute:

```bash
python app.py
```

O sistema irá:

1. carregar o roteiro configurado;
2. processar o roteiro em JSON;
3. separar texto exibido e texto falado;
4. inicializar o reconhecedor de fala com Vosk;
5. abrir o microfone;
6. comparar a fala reconhecida com as linhas do roteiro;
7. avançar a rolagem conforme a leitura.

Nesta versão, a execução principal ainda ocorre pelo terminal. A interface web já foi desenvolvida em **HTML, CSS e JavaScript**, mas a integração completa com o backend/API ainda está em andamento.

---

## 4.9 Acessando a interface

Quando a integração com a interface estiver ativa, acesse no navegador:

```text
http://127.0.0.1:5500
```

Ou utilize o endereço informado no terminal ao executar o sistema.

> Observação: caso a execução atual esteja apenas no terminal, essa parte deve ser atualizada após a integração final da interface com o backend/API.

---

## 4.10 Usando o teleprompter

Após iniciar o sistema:

1. verifique se o microfone está conectado;
2. confirme se o roteiro foi carregado corretamente;
3. inicie a leitura do roteiro em voz alta;
4. acompanhe no terminal os textos reconhecidos pelo Vosk;
5. observe o avanço da rolagem conforme a leitura.

O sistema utiliza reconhecimento de fala para identificar o trecho lido pelo apresentador e sincronizar o avanço do teleprompter.

---

## 4.11 Problemas comuns e soluções

### O comando `python` não é reconhecido

Teste:

```bash
py --version
```

Ou utilize o caminho completo do Python instalado na máquina.

Exemplo no PowerShell:

```powershell
& "C:\Users\leandro_santos\AppData\Local\Programs\Python\Python313\python.exe" --version
```

> Atenção: o caminho acima é apenas um exemplo. Em outro computador, o nome do usuário e a pasta da versão do Python podem ser diferentes.

Também é possível verificar onde o Windows está encontrando o Python. No **CMD**, execute:

```cmd
where python
```

Se aparecer um caminho contendo `WindowsApps`, por exemplo:

```text
C:\Users\SEU_USUARIO\AppData\Local\Microsoft\WindowsApps\python.exe
```

não utilize esse caminho para criar o ambiente virtual, pois ele pode apontar apenas para um atalho da Microsoft Store e não para a instalação real do Python.

Nesse caso, tente usar:

```cmd
py --version
```

ou procure o caminho real da instalação do Python, como no exemplo:

```cmd
"C:\Users\leandro_santos\AppData\Local\Programs\Python\Python313\python.exe" --version
```

---

### O comando `pip` não é reconhecido

Use:

```bash
python -m pip --version
```

E para instalar dependências:

```bash
python -m pip install -r requirements.txt
```

---

### O ambiente virtual não ativa no PowerShell

Execute:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Depois:

```powershell
.\venv\Scripts\Activate.ps1
```

---

### Modelo Vosk não encontrado

Verifique se a pasta `model` está na raiz do projeto.

A estrutura deve ser:

```text
projeto/
├── app.py
├── model/
│   └── arquivos do modelo
```

---

### Microfone não encontrado

Verifique:

- se o microfone está conectado;
- se o Windows reconhece o dispositivo;
- se outro aplicativo está usando o microfone;
- se o VS Code ou terminal tem permissão de acesso ao microfone.


---

## 5. Observações de segurança

Por segurança, senhas, tokens, credenciais e informações sensíveis não devem ser colocadas diretamente no código ou no README.

Caso o sistema utilize autenticação, a credencial deve ser definida pela equipe em ambiente local. Recomenda-se o uso de variáveis de ambiente ou arquivos de configuração não versionados no GitHub.

Exemplo de arquivo que pode ser ignorado pelo Git:

```text
.env
```
---

## 6. Equipe

Projeto desenvolvido pela **Squad 29**.

| Integrante | Responsabilidade |
|---|---|
| [Nome] | Backend / reconhecimento de fala |
| [Nome] | Interface HTML/CSS/JavaScript |
| [Nome] | Interface HTML/CSS/JavaScript |
| [Nome] | Documentação |
| [Nome] | Testes e validação |
