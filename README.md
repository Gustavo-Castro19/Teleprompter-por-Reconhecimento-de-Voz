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

A integração inicial entre backend e interface web também foi implementada. O sistema deixou de funcionar apenas em modo terminal e passou a executar como um servidor **Flask + SocketIO**, permitindo a comunicação entre o motor de rolagem e as telas no navegador.

Também já foram implementados:

- servidor Flask iniciando em `http://127.0.0.1:5500`;
- rotas `/comando` e `/tp`;
- envio do roteiro do backend para o navegador;
- envio de comandos de rolagem via SocketIO;
- eventos `roteiro`, `cmd` e `status_motor`;
- renderização das linhas do roteiro no navegador;
- destaque da linha atual;
- rolagem visual com `transform`;
- controles manuais de avançar, voltar e pausar/retomar;
- controle por teclado com setas e espaço;
- ajustes visuais de fonte, tamanho, negrito, itálico, sublinhado e inversão de tela;
- ajuste manual de rolagem pelo slider;
- opção de abrir e salvar roteiro localmente.

Ainda estão em teste ou refinamento:

- validação completa da integração entre áudio, backend e interface;
- testes em diferentes computadores;
- ajustes finos da rolagem automática;
- validação do comportamento em cenários com ruído e improviso.

**Status atual:** integração inicial concluída e em fase de testes.

## 2. Tecnologias utilizadas

- Python 3.13.x
- Vosk
- PyAudio
- Flask
- SocketIO
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
│   ├── css/
│   │   └── style.css
│   ├── imgs/
│   │   ├── logo.png
│   │   └── comandos/
│   └── js/
│       └── script.js
├── templates/
│   ├── comando.html
│   └── tp.html
├── requirements.txt
└── README.md
```

### Interface web

A interface web do teleprompter foi integrada inicialmente ao backend em **Flask + SocketIO**. O sistema possui duas telas principais:

- `/comando`: tela de controle, com botões e ajustes manuais;
- `/tp`: tela cheia do teleprompter, usada para exibição do roteiro.

A comunicação entre backend e frontend ocorre por eventos SocketIO. O backend envia o roteiro e os comandos de rolagem para o navegador, enquanto a interface renderiza as linhas, destaca a linha atual e aplica os comandos visuais.

Eventos utilizados:

- `roteiro`: envia as linhas do roteiro para a interface;
- `cmd`: envia comandos de rolagem e atualização da linha atual;
- `status_motor`: informa o estado do motor de execução.

Funcionalidades da interface:

- renderização das linhas do roteiro;
- destaque da linha atual;
- avanço e retorno manual;
- pausar e retomar;
- controle por teclado com setas e espaço;
- troca de fonte;
- alteração do tamanho da fonte;
- negrito, itálico e sublinhado;
- inversão de tela;
- ajuste manual de rolagem pelo slider;
- abertura e salvamento de roteiro localmente.

**Status:** integração inicial concluída e em fase de testes.

### Função dos principais arquivos

| Arquivo | Função |
|---|---|
| `app.py` | Arquivo principal do sistema. Inicializa o servidor Flask + SocketIO, carrega o roteiro, inicia o reconhecedor de fala, abre o microfone e envia comandos para a interface. |
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
| `templates/comando.html` | Tela de controle do teleprompter, com botões manuais e opções de ajuste da interface. |
| `templates/tp.html` | Tela cheia do teleprompter, usada para exibir o roteiro ao apresentador. |
| `static/js/script.js` | Controla a comunicação da interface com o backend via SocketIO, renderização do roteiro, comandos manuais e ajustes visuais. |
| `static/css/style.css` | Define a aparência visual da interface do teleprompter, incluindo layout, fontes, destaque e tela cheia. |


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

Nesta versão, o sistema executa um servidor **Flask + SocketIO**, integrando o backend com a interface web. O terminal continua exibindo logs do motor, reconhecimento de fala e eventos do sistema, enquanto o navegador exibe as telas do teleprompter.

---

## 4.9 Acessando a interface

Após executar o sistema com:

```bash
python app.py
```

acesse as telas pelo navegador:

```text
http://127.0.0.1:5500/comando
```

```text
http://127.0.0.1:5500/tp
```

A tela `/comando` é usada para controle do teleprompter, permitindo avançar, voltar, pausar/retomar e ajustar a visualização.

A tela `/tp` é a visualização em tela cheia do teleprompter, usada para acompanhar o roteiro durante a leitura.

---

## 4.10 Usando o teleprompter

Após iniciar o sistema:

1. verifique se o microfone está conectado;
2. acesse a tela de controle em `http://127.0.0.1:5500/comando`;
3. acesse a tela cheia em `http://127.0.0.1:5500/tp`;
4. confirme se o roteiro foi carregado corretamente;
5. utilize os botões de avançar, voltar e pausar/retomar, se necessário;
6. inicie a leitura do roteiro em voz alta;
7. acompanhe no terminal os textos reconhecidos pelo Vosk e os eventos enviados pelo SocketIO.

O sistema utiliza reconhecimento de fala para identificar o trecho lido pelo apresentador e sincronizar o avanço do teleprompter na interface.

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
| [Nome] | [INSERIR RESPONSABILIDADE] |
| [Nome] | [INSERIR RESPONSABILIDADE] |
| [Nome] | [INSERIR RESPONSABILIDADE] |
| [Nome] | [INSERIR RESPONSABILIDADE] |
| [Nome] | [INSERIR RESPONSABILIDADE] |
