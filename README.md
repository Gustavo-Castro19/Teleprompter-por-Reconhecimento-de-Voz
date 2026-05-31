# Teleprompter por Reconhecimento de Voz — SQUAD 29

O **Teleprompter por Reconhecimento de Voz** é um MVP desenvolvido pela **Squad 29** com o objetivo de automatizar a rolagem de um teleprompter a partir da fala do apresentador.

A solução utiliza reconhecimento de voz em tempo real para identificar o trecho do roteiro que está sendo lido e, com base nisso, sincronizar a posição do texto exibido na interface. O projeto foi pensado para reduzir a dependência de operação manual, melhorar a fluidez da apresentação e diminuir riscos de dessincronia entre fala e roteiro.

Nesta versão, o sistema utiliza o **Vosk**, uma tecnologia de reconhecimento de fala offline, em conjunto com Python e captura de áudio local pelo microfone. O MVP também conta com uma interface web integrada em página única, utilizada para visualizar o roteiro, controlar a rolagem e apoiar a operação do teleprompter.

---

## 1. Status atual do MVP

O projeto encontra-se em fase de testes e refinamentos finais.

Atualmente, a equipe já desenvolveu a base principal do sistema, incluindo:

* leitura e processamento do roteiro em JSON;
* processamento da estrutura editorial disponibilizada pela Globo;
* separação entre texto exibido no teleprompter e texto falado pelo apresentador;
* preservação de comandos técnicos na visualização;
* remoção de comandos técnicos do texto usado para reconhecimento;
* captura de áudio pelo microfone;
* reconhecimento de fala com Vosk;
* geração de transcrições parciais e finais;
* normalização do texto reconhecido;
* comparação entre fala reconhecida e roteiro;
* controle de avanço e retorno da posição do teleprompter;
* controle de estados internos do sistema;
* integração entre backend Flask + SocketIO e interface web;
* interface visual em página única, desenvolvida em HTML, CSS e JavaScript;
* rolagem contínua do texto no frontend;
* ajuste manual da velocidade da rolagem pelo slider lateral;
* sincronização visual da posição do texto;
* geração de segmentos do roteiro com índices e estimativa de tempo de leitura;
* acompanhamento técnico da execução por logs exibidos no terminal.

A interface visual do MVP já está integrada ao backend e funciona em uma única página principal. Nessa página, o usuário pode visualizar o roteiro, utilizar controles manuais, ajustar fonte e tamanho do texto, inverter a exibição da tela e controlar a velocidade da rolagem contínua.

O botão `PLAY/PARAR` alterna a visualização da interface para o modo com painel auxiliar em formato 4:3, enquanto o botão `INVERTER TELA` realiza o espelhamento horizontal do texto exibido.

Ainda está em desenvolvimento:

* cálculo e envio de velocidade sugerida pelo backend para o frontend, a partir dos metadados e tempos estimados do roteiro;
* testes mais completos em diferentes computadores, microfones e cenários de uso.

---

## 2. Tecnologias utilizadas

* Python 3.13.x
* Vosk
* PyAudio
* Flask
* SocketIO
* HTML
* CSS
* JavaScript
* JSON
* Git/GitHub
* VS Code

### Versão do Python

Durante o desenvolvimento e os testes do MVP, a equipe utilizou Python 3.13.x.

Para verificar a versão instalada, execute:

```bash
python --version
```

Caso o comando `python` não funcione, tente:

```bash
py --version
```

---

## 3. Estrutura do projeto

O sistema utiliza roteiros em formato JSON, seguindo uma estrutura semelhante à disponibilizada pela Globo. Esses arquivos contêm informações do espelho jornalístico, como retrancas, páginas, apresentadores, textos de fala, comandos técnicos, marcações de produção e blocos de conteúdo.

O backend processa esse JSON para gerar duas estruturas principais:

* **linhas exibidas:** conteúdo que aparece visualmente no teleprompter, incluindo comandos técnicos;
* **linhas faláveis:** conteúdo usado para comparação com a fala do apresentador, sem comandos técnicos.

Além disso, o processamento do roteiro gera segmentos com informações de apoio, como índice falado, índice visual e estimativa de tempo de leitura.

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
│   ├── js/
│   │   └── script.js
│   └── imgs/
│       ├── logo.png
│       └── comandos/
├── templates/
│   └── comando.html
├── requirements.txt
└── README.md
```

### Função dos principais arquivos

| Arquivo                  | Função                                                                                                                                                                                    |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app.py`                 | Arquivo principal do sistema. Inicializa o servidor Flask + SocketIO, carrega o roteiro, coordena o reconhecimento de fala, inicia o motor de áudio e envia informações para a interface. |
| `processador_roteiro.py` | Processa o roteiro em JSON, separando o texto exibido do texto falado, preservando comandos técnicos na visualização e gerando segmentos com tempo estimado de leitura.                   |
| `reconhecedor_fala.py`   | Inicializa e utiliza o Vosk para transformar áudio em texto parcial ou final.                                                                                                             |
| `motor_audio.py`         | Abre, lê e fecha o microfone utilizando PyAudio.                                                                                                                                          |
| `controlador_rolagem.py` | Compara a fala reconhecida com o roteiro e decide quando avançar ou retornar a posição do teleprompter.                                                                                   |
| `normalizador_texto.py`  | Normaliza textos, removendo diferenças de formatação para melhorar a comparação.                                                                                                          |
| `maquina_estados.py`     | Controla estados internos do sistema, como automático, pausado, finalizado, falha e improviso.                                                                                            |
| `alinhador_roteiro.py`   | Relaciona a linha falada com a linha visual exibida na interface.                                                                                                                         |
| `configuracoes.py`       | Guarda caminhos, limites de similaridade e parâmetros de execução.                                                                                                                        |
| `registrador_eventos.py` | Centraliza mensagens e eventos exibidos no terminal durante os testes.                                                                                                                    |
| `seguranca.py`           | Centraliza funções iniciais relacionadas à segurança e ocultação de dados sensíveis.                                                                                                      |
| `modelos.py`             | Define estruturas de dados utilizadas no processamento dos segmentos do roteiro.                                                                                                          |
| `comando.html`           | Página principal da interface, reunindo visualização do roteiro, controles manuais, barra de ferramentas e painel auxiliar 4:3.                                                           |
| `script.js`              | Controla a comunicação da interface com o backend via SocketIO, a renderização do roteiro, a rolagem contínua, o slider de velocidade, os comandos manuais e os ajustes visuais.          |
| `style.css`              | Define a aparência visual da interface, incluindo barra de ferramentas, área do teleprompter, painel auxiliar 4:3 e controle lateral.                                                     |
| `static/imgs/`           | Armazena a logo e os ícones utilizados nos botões da interface.                                                                                                                           |

---

## 4. Passo a passo de instalação e execução

A seguir está o guia completo para rodar o MVP do zero em um computador **Windows**, mesmo sem conhecimento técnico prévio.

---

## 4.1 Pré-requisitos

Antes de executar o projeto, é necessário instalar alguns programas e arquivos.

### Python

O projeto foi desenvolvido e testado com **Python 3.13.x** ou versão compatível.

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

Procure por **Portuguese** e baixe o modelo utilizado pela equipe:

```text
vosk-model-pt-fb-v0.1.1-20220516_2113
```

---

## 4.2 Baixando o projeto

Escolha uma pasta no computador onde deseja salvar o projeto.

Abra o terminal nessa pasta e execute:

```bash
git clone https://github.com/codedbydaph/Projeto-Porto-Digital.git
```

Depois, entre na pasta do projeto:

```bash
cd Projeto-Porto-Digital
```

---

## 4.3 Configurando o modelo Vosk

Depois de baixar o modelo `vosk-model-pt-fb-v0.1.1-20220516_2113`, siga os passos:

1. Extraia o arquivo baixado;
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

### Ajuste adicional no modelo utilizado pela equipe

Durante os testes realizados pela equipe, após renomear a pasta principal para `model`, foi necessário realizar um ajuste interno para que o Vosk fosse iniciado corretamente.

Dentro da pasta `model`, localize a pasta:

```text
rescore
```

Renomeie para:

```text
rescore_disable
```

A estrutura ficará semelhante a:

```text
projeto/
├── app.py
├── model/
│   ├── ...
│   └── rescore_disable/
└── README.md
```

> Este procedimento foi necessário no modelo utilizado durante os testes da equipe. Em outro modelo ou versão do Vosk, a estrutura interna pode apresentar diferenças.

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
& "C:\Users\SEU_USUARIO\AppData\Local\Programs\Python\Python313\python.exe" -m venv venv
```

Exemplo no CMD:

```cmd
"C:\Users\SEU_USUARIO\AppData\Local\Programs\Python\Python313\python.exe" -m venv venv
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
python -m pip install flask flask-socketio vosk pyaudio
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

Caso apresente erro, confirme:

* se o ambiente virtual está ativo;
* qual versão do Python está instalada;
* se existe uma versão compatível do PyAudio para o ambiente utilizado.

Para verificar a versão do Python:

```bash
python --version
```

> A instalação do PyAudio pode variar conforme a versão do Python e a configuração do computador utilizado.

---

## 4.8 Executando o sistema

Com o ambiente virtual ativado, o modelo Vosk configurado e as dependências instaladas, execute:

```bash
python app.py
```

O sistema irá:

1. carregar o roteiro configurado;
2. processar o roteiro em JSON;
3. separar texto exibido e texto falado;
4. iniciar o servidor Flask + SocketIO;
5. disponibilizar a interface web;
6. inicializar o reconhecedor de fala com Vosk;
7. abrir o microfone;
8. comparar a fala reconhecida com as linhas do roteiro;
9. sincronizar a posição do texto exibido na interface.

Durante a execução, o terminal é utilizado para acompanhar informações técnicas do sistema, como:

* carregamento e diagnóstico do roteiro;
* inicialização do Vosk;
* abertura do microfone;
* mensagens reconhecidas;
* métricas de comparação;
* eventos de rolagem;
* alterações de estado;
* possíveis falhas.

---

## 4.9 Acessando a interface

Após executar o sistema, acesse no navegador:

```text
http://127.0.0.1:5500/comando
```

A interface atual funciona em uma única página principal, reunindo:

* visualização e edição do roteiro;
* barra de ferramentas;
* abertura e salvamento de arquivo;
* opções de fonte, tamanho e formatação;
* botão de inversão da tela;
* controle lateral de velocidade da rolagem;
* botões manuais de avanço e retorno;
* modo com painel auxiliar em formato 4:3.

---

## 4.10 Usando o teleprompter

Após iniciar o sistema:

1. verifique se o microfone está conectado;
2. acesse a interface em `http://127.0.0.1:5500/comando`;
3. confirme se o roteiro foi carregado corretamente;
4. ajuste fonte, tamanho ou formatação do texto, se necessário;
5. utilize o botão `INVERTER TELA` caso seja necessário espelhar horizontalmente a exibição;
6. ajuste a velocidade da rolagem contínua utilizando o slider lateral;
7. utilize o botão `PLAY/PARAR` para alternar a visualização com painel auxiliar em formato 4:3;
8. acompanhe o destaque da linha atual durante a leitura;
9. utilize os botões `PREV` e `NEXT` caso seja necessário intervir manualmente;
10. acompanhe no terminal os logs gerados durante os testes.

A interface também permite abrir arquivos locais nos formatos `.txt` e `.json`, editar visualmente o roteiro e salvar o conteúdo em arquivo `.txt`.

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
& "C:\Users\SEU_USUARIO\AppData\Local\Programs\Python\Python313\python.exe" --version
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

ou procure o caminho real da instalação do Python.

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

### Já existe uma pasta `venv` e o ambiente apresenta conflito

Caso a pasta `venv` tenha sido criada em outro computador ou com outra versão do Python, ela pode causar erros de ativação ou incompatibilidade entre dependências.

Se o ambiente estiver ativo, desative-o:

```bash
deactivate
```

Depois, exclua a pasta `venv` antiga.

No CMD:

```cmd
rmdir /s /q venv
```

No PowerShell:

```powershell
Remove-Item -Recurse -Force venv
```

Em seguida, crie novamente o ambiente virtual:

```bash
python -m venv venv
```

Ative o novo ambiente e instale novamente as dependências:

```bash
python -m pip install -r requirements.txt
```

> A pasta `venv` é específica de cada computador e deve permanecer fora do repositório, preferencialmente registrada no arquivo `.gitignore`.

---

### Modelo Vosk não encontrado ou não inicializa

Verifique se a pasta `model` está na raiz do projeto.

A estrutura deve ser:

```text
projeto/
├── app.py
├── model/
│   └── arquivos do modelo
```

Caso o modelo esteja na pasta correta, mas o Vosk apresente erro durante a inicialização, verifique se foi realizado o ajuste utilizado pela equipe:

```text
model/rescore  →  model/rescore_disable
```

---

### Microfone não encontrado

Verifique:

* se o microfone está conectado;
* se o Windows reconhece o dispositivo;
* se outro aplicativo está usando o microfone;
* se o VS Code ou terminal tem permissão de acesso ao microfone.

---

### A interface não abre no navegador

Verifique se o sistema continua executando no terminal.

Depois, tente acessar:

```text
http://127.0.0.1:5500/comando
```

Caso a página não abra:

* verifique se houve alguma mensagem de erro no terminal;
* confirme se a porta `5500` está disponível;
* encerre e execute novamente o comando `python app.py`.

---

## 5. Observações de segurança

Por segurança, senhas, tokens, credenciais e informações sensíveis não devem ser colocadas diretamente no código ou no README.

Caso o sistema utilize autenticação ou configurações sensíveis futuramente, recomenda-se o uso de variáveis de ambiente ou arquivos de configuração não versionados no GitHub.

Exemplos de arquivos e pastas que não devem ser enviados ao repositório:

```text
.env
venv/
model/
__pycache__/
```

---

## 6. Equipe

Projeto desenvolvido pela **Squad 29**.

| Integrante | Responsabilidade                 |
| ---------- | -------------------------------- |
| [Nome]     | Backend / reconhecimento de fala |
| [Nome]     | Processamento do roteiro JSON    |
| [Nome]     | Interface HTML/CSS/JavaScript    |
| [Nome]     | Documentação                     |
| [Nome]     | Testes e validação               |
