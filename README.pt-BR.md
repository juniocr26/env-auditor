# ENV Auditor

Uma CLI Python independente para auditar, sincronizar e limpar arquivos `.env`, `.env.*` e `.env.example` entre projetos em um workspace.

O ENV Auditor mantém todos os arquivos de ambiente de um mesmo projeto consistentes com um `.env.example` compartilhado, detecta variáveis potencialmente não utilizadas, remove configurações obsoletas e ajuda a reduzir o risco de exposição acidental de valores sensíveis.

A ferramenta foi projetada para funcionar sem dependências externas do Python e nunca exibe os valores das variáveis de ambiente.

## Funcionalidades

- Descobre automaticamente arquivos `.env`, `.env.*` e `.env.example`.

- Suporta qualquer arquivo de ambiente correspondente a `.env.*`, incluindo:
  - `.env.prod`
  - `.env.test`
  - `.env.local`
  - `.env.dev`
  - `.env.qa`
  - `.env.staging`
  - `.env.production`
  - `.env.docker`
  - nomes personalizados de ambiente

- Trata todos os arquivos `.env` / `.env.*` no mesmo diretório como ambientes do mesmo projeto.

- Utiliza um único `.env.example` como contrato de ambiente de cada projeto.

- Sincroniza a união das chaves dos ambientes no `.env.example`.

- Sincroniza as chaves do `.env.example` de volta para todos os arquivos de ambiente existentes.

- Nunca copia valores reais de `.env` / `.env.*` para o `.env.example`.

- Cria o `.env.example` quando existem apenas arquivos de ambiente.

- Pode criar o `.env` a partir do `.env.example` quando nenhum arquivo de ambiente existe.

- Detecta chaves duplicadas.

- Detecta possíveis secrets armazenados no `.env.example`.

- Pesquisa arquivos de runtime e configuração em busca de referências a variáveis de ambiente.

- Classifica o uso das variáveis como forte, fraco ou potencialmente não utilizado.

- Remove automaticamente variáveis sem uso detectado.

- Preserva variáveis com evidência fraca de uso.

- Suporta exclusões explícitas para variáveis gerenciadas externamente.

- Cria backups antes de modificar arquivos existentes.

- Suporta simulação segura com `--dry-run`.

- Suporta análise somente leitura com `--audit-only`.

- Nunca exibe os valores das variáveis de ambiente.

## Estrutura do Projeto

O script executável está localizado em:

```text
scripts/audit-envs.py
```

Um projeto sendo auditado pode ter a seguinte estrutura:

```text
project/
├── .env
├── .env.prod
├── .env.test
├── .env.local
├── .env.example
├── .env-audit.json
└── scripts/
    └── audit-envs.py
```

Os seguintes arquivos são tratados como arquivos de ambiente reais:

```text
.env
.env.*
```

Arquivos especiais são excluídos, incluindo:

```text
.env.example
.env*.bak.*
```

Isso significa que arquivos como:

```text
.env.test
.env.qa
.env.production
.env.my-environment
```

são descobertos automaticamente sem necessidade de configuração adicional.

## Como Funciona

Cada diretório contendo arquivos de ambiente é tratado como um projeto.

```text
                 ┌── .env
                 ├── .env.prod
.env.example  ←→ ├── .env.test
                 ├── .env.local
                 └── .env.staging
```

O arquivo `.env.example` representa o conjunto completo de chaves de variáveis de ambiente esperadas para aquele projeto.

Os valores reais permanecem isolados dentro de cada arquivo de ambiente e nunca são propagados de um ambiente real para outro.

## Requisitos

- Python 3.10 ou superior
- Acesso de leitura aos projetos que serão auditados
- Acesso de escrita para execução normal

Nenhum pacote Python externo é necessário.

## Uso Básico

Execute o auditor a partir da raiz do workspace:

```bash
python3 scripts/audit-envs.py
```

Por padrão, o ENV Auditor:

1. descobre arquivos `.env`, `.env.*` e `.env.example`;
2. agrupa os arquivos de ambiente pelo diretório do projeto;
3. sincroniza as chaves dos ambientes no `.env.example`;
4. sincroniza as chaves do `.env.example` em cada arquivo de ambiente;
5. detecta chaves duplicadas e possíveis secrets;
6. pesquisa o projeto em busca de referências às variáveis de ambiente;
7. classifica as variáveis de acordo com as evidências de uso;
8. remove automaticamente variáveis sem uso detectado;
9. informa quais variáveis foram removidas e de quais arquivos.

A limpeza de variáveis não utilizadas faz parte do comportamento padrão.

Não existe uma opção separada `--remove-unused`.

## Descoberta de Arquivos de Ambiente

Qualquer arquivo correspondente a:

```text
.env.*
```

é tratado como um arquivo de ambiente real, a menos que seja explicitamente excluído.

Exemplos:

```text
.env.prod
.env.test
.env.local
.env.dev
.env.qa
.env.staging
.env.production
.env.docker
.env.custom
```

O arquivo `.env` convencional também é suportado.

O `.env.example` é tratado separadamente como arquivo de referência do projeto.

Backups criados pelo ENV Auditor são ignorados durante a descoberta.

## Sincronizando Múltiplos Ambientes

Considere o seguinte projeto:

```text
project/
├── .env
├── .env.prod
├── .env.test
└── .env.example
```

Suponha que os arquivos contenham estas chaves:

```text
.env
APP_NAME
LOCAL_ONLY

.env.prod
APP_NAME
PROD_ONLY

.env.test
APP_NAME
TEST_ONLY

.env.example
APP_NAME
FROM_EXAMPLE
```

Após a sincronização, todos os arquivos de ambiente e o `.env.example` conterão o mesmo conjunto de chaves:

```text
APP_NAME
LOCAL_ONLY
PROD_ONLY
TEST_ONLY
FROM_EXAMPLE
```

Os valores não são sincronizados entre arquivos de ambiente reais.

### Os valores são tratados de forma diferente dependendo da direção

Quando uma chave é encontrada em um arquivo de ambiente real e não existe no `.env.example`, somente a chave é adicionada:

```env
MY_VARIABLE=
```

O valor real nunca é copiado.

Quando uma chave existe no `.env.example`, mas está ausente de um arquivo de ambiente real, o bloco correspondente do `.env.example` pode ser copiado para esse ambiente.

Isso permite que valores padrão seguros do `.env.example` sejam propagados sem copiar secrets entre ambientes reais.

## Chave Existe em um Ambiente, mas Não no `.env.example`

Se uma variável existe em:

```text
.env
.env.prod
.env.test
.env.local
```

mas não existe no `.env.example`, o ENV Auditor adiciona somente a chave:

```env
MY_VARIABLE=
```

O valor original do ambiente nunca é copiado.

## Chave Existe no `.env.example`, mas Não em um Ambiente

Suponha que o `.env.example` contenha:

```env
APP_TIMEZONE=UTC
```

e o `.env.prod` não contenha `APP_TIMEZONE`.

O bloco correspondente do `.env.example` é adicionado ao `.env.prod`.

A sincronização é realizada independentemente para cada arquivo de ambiente.

## Chaves Específicas de Ambiente

Uma variável pode existir inicialmente em apenas um ambiente.

Por exemplo:

```text
.env
APP_NAME=...

.env.prod
APP_NAME=...
PROD_SPECIAL=real-value

.env.example
APP_NAME=
```

O ENV Auditor primeiro adiciona a chave ao `.env.example`:

```env
PROD_SPECIAL=
```

A chave pode então ser propagada para os outros ambientes a partir da representação segura presente no `.env.example`.

O valor real do `.env.prod` nunca é copiado para outro ambiente.

## Criando o `.env.example`

Se um projeto contém arquivos de ambiente, mas não possui `.env.example`:

```text
.env
.env.prod
.env.test
```

o ENV Auditor cria o `.env.example` utilizando a união de todas as chaves encontradas.

Dado:

```text
.env
A=value
B=value

.env.prod
A=value
C=value

.env.test
A=value
D=value
```

o `.env.example` gerado contém:

```env
A=
B=
C=
D=
```

Nenhum valor real é copiado.

## Criando o `.env`

Se um projeto contém apenas:

```text
.env.example
```

o ENV Auditor pode criar:

```text
.env
```

a partir do `.env.example`, desde que nenhum possível secret real seja detectado no arquivo de exemplo.

A ferramenta não cria automaticamente `.env.prod`, `.env.test` ou outros arquivos específicos de ambiente que ainda não existam.

## Limpeza Automática

Durante uma execução normal:

```bash
python3 scripts/audit-envs.py
```

o ENV Auditor remove automaticamente variáveis para as quais nenhuma evidência forte ou fraca de uso foi encontrada.

A remoção é aplicada a:

```text
.env
.env.*
.env.example
```

onde quer que a chave esteja presente.

Variáveis com evidência fraca de uso são preservadas.

Variáveis listadas em:

```json
"ignore_unused_keys"
```

também são preservadas.

## Exemplo de Limpeza

Uma execução normal pode produzir uma saída semelhante a:

```text
REMOVING automatically detected unused variables:

    - LEGACY_FEATURE_FLAG
    - OLD_WORKER_COUNT

REMOVED BY FILE:

    .env:
      - LEGACY_FEATURE_FLAG
      - OLD_WORKER_COUNT

    .env.example:
      - LEGACY_FEATURE_FLAG
      - OLD_WORKER_COUNT

    .env.prod:
      - LEGACY_FEATURE_FLAG
      - OLD_WORKER_COUNT
```

O ENV Auditor exibe somente os nomes das variáveis.

Os valores das variáveis de ambiente nunca são exibidos.

> Nota: a implementação atual da CLI pode exibir alguns rótulos de status em português. O comportamento descrito aqui permanece o mesmo.

## Dry Run

Para visualizar todas as operações de sincronização e limpeza sem modificar arquivos:

```bash
python3 scripts/audit-envs.py --dry-run
```

`--dry-run` simula:

- descoberta de ambientes;
- criação do `.env.example`;
- criação do `.env` a partir do `.env.example`;
- sincronização de chaves;
- detecção de variáveis não utilizadas;
- limpeza automática.

Nenhum arquivo é alterado.

Este é o modo recomendado antes de executar o ENV Auditor pela primeira vez em um projeto existente.

## Modo Audit-Only

Para inspecionar um projeto sem sincronizar ou modificar nada:

```bash
python3 scripts/audit-envs.py --audit-only
```

Neste modo:

- nenhum arquivo é criado;
- nenhuma variável é adicionada;
- nenhuma variável é removida;
- nenhum arquivo é modificado.

Variáveis potencialmente não utilizadas são apenas reportadas.

`--audit-only` não pode ser combinado com `--dry-run`.

## Exibindo Evidências de Uso

Use:

```bash
python3 scripts/audit-envs.py --show-usage
```

para exibir os arquivos nos quais evidências de uso foram encontradas.

Exemplo:

```text
USO_FORTE DB_HOST: docker-compose.yml, config/database.php

USO_FRACO FEATURE_FLAG_X: config/custom.php
```

Também pode ser combinado com:

```bash
python3 scripts/audit-envs.py --dry-run --show-usage
```

ou:

```bash
python3 scripts/audit-envs.py --audit-only --show-usage
```

## Detecção de Uso

O ENV Auditor separa as referências em três categorias.

### Uso Forte

Uso forte é detectado quando uma variável é referenciada utilizando um padrão reconhecido de acesso a variáveis de ambiente.

PHP / Laravel:

```php
env('DB_HOST')
```

Shell e Docker Compose:

```bash
${DB_HOST}
$DB_HOST
```

Node.js:

```javascript
process.env.DB_HOST;
process.env["DB_HOST"];
```

Vite:

```javascript
import.meta.env.VITE_API_URL;
```

Python:

```python
os.getenv("DB_HOST")
os.environ["DB_HOST"]
```

Java / Kotlin:

```java
System.getenv("DB_HOST")
```

O auditor também reconhece diversas funções auxiliares de ambiente:

```text
getRequiredEnv
getEnv
getNumberEnv
getListEnv
getRequiredEnvFrom
getNumberEnvFrom
getListEnvFrom
```

Variáveis com evidência forte de uso são preservadas.

### Uso Fraco

Uso fraco significa que o nome exato da variável foi encontrado em um arquivo pesquisável de runtime ou configuração, mas a referência não correspondeu a um padrão reconhecido de uso forte.

Exemplo:

```text
USO_APENAS_FRACO:

    - MY_VARIABLE
```

Variáveis com referência fraca são preservadas automaticamente.

Esse comportamento conservador ajuda a evitar remoções acidentais quando as variáveis são acessadas indiretamente ou por padrões ainda não suportados.

### Potencialmente Não Utilizada

Se nenhuma referência forte ou fraca for encontrada, a variável é classificada como potencialmente não utilizada.

No modo audit-only:

```text
POSSIVELMENTE_SEM_USO:

    - LEGACY_VARIABLE
```

Durante uma execução normal, essas variáveis são automaticamente removidas de todos os arquivos de ambiente relevantes.

## Arquivos de Ambiente Não São Evidência de Uso

Os próprios arquivos de ambiente são fontes de configuração, e não evidência de que uma variável esteja realmente sendo utilizada pela aplicação.

Por esse motivo, arquivos como:

```text
.env
.env.prod
.env.test
.env.local
.env.example
```

são excluídos da análise de uso.

Isso evita que uma variável seja considerada "em uso" simplesmente porque está declarada em outro arquivo de ambiente.

## Fluxo de Execução

Uma execução normal segue este fluxo geral:

```text
Descobrir projetos

        ↓

Descobrir .env / .env.*

        ↓

Ler .env.example

        ↓

Validar possíveis secrets

        ↓

Construir a união das chaves de ambiente

        ↓

Sincronizar chaves no .env.example

        ↓

Sincronizar .env.example em cada ambiente

        ↓

Pesquisar arquivos de runtime/configuração

        ↓

Classificar uso

        ↓

Preservar uso forte

        ↓

Preservar uso fraco

        ↓

Preservar ignore_unused_keys

        ↓

Remover variáveis sem evidência de uso

        ↓

Recarregar arquivos modificados

        ↓

Validar paridade final das chaves
```

## Saída por Projeto

Quando arquivos de ambiente são encontrados, o ENV Auditor informa quais arquivos pertencem ao projeto.

Exemplo:

```text
[my-project]

  Environment files: .env, .env.local, .env.prod, .env.test
```

Isso facilita confirmar que arquivos personalizados como `.env.test` ou `.env.qa` foram descobertos corretamente.

## Validação de Paridade das Chaves

A paridade é verificada entre:

```text
.env.example
```

e cada arquivo de ambiente real do mesmo projeto.

A CLI atual informa condições estruturais utilizando rótulos como:

```text
FALTANDO_NO_EXAMPLE
EXAMPLE_SEM_CHAVE_NO_AMBIENTE
DUPLICADAS
POSSIVEL_SECRET_NO_EXAMPLE
```

### `FALTANDO_NO_EXAMPLE`

Uma chave existe em pelo menos um arquivo de ambiente real, mas não existe no `.env.example`.

### `EXAMPLE_SEM_CHAVE_NO_AMBIENTE`

Uma chave existe no `.env.example`, mas está ausente de um ou mais arquivos de ambiente reais.

### `DUPLICADAS`

Uma chave aparece mais de uma vez no mesmo arquivo.

### `POSSIVEL_SECRET_NO_EXAMPLE`

Uma variável com nome potencialmente sensível contém um valor no `.env.example` que pode representar uma credencial real.

## Proteção de Secrets

O ENV Auditor verifica nomes de variáveis potencialmente sensíveis contendo termos como:

```text
SECRET
PASSWORD
PASS
TOKEN
PRIVATE
CREDENTIAL
CREDENTIALS
CLIENT_SECRET
APP_KEY
API_KEY
```

Valores comuns utilizados como placeholders são aceitos, incluindo:

```text
change
changeme
placeholder
example
dummy
fake
your_...
xxx
<value>
false
true
0
1
null
base64:
```

Se uma variável com nome potencialmente sensível contiver um valor que pareça real, a sincronização poderá ser bloqueada.

A validação de secrets é aplicada ao `.env.example`.

Valores reais de `.env` / `.env.*` não são inspecionados para propagação e nunca são exibidos.

## Backups

Antes de modificar arquivos existentes, o ENV Auditor cria backups em:

```text
.env-audit-backups/
```

Exemplo:

```text
.env-audit-backups/
└── my-project/
    ├── .env.20260911_083500_123456.bak
    ├── .env.prod.20260911_083500_234567.bak
    ├── .env.test.20260911_083500_345678.bak
    └── .env.example.20260911_083500_456789.bak
```

Os arquivos de backup recebem permissões `0600` quando suportadas pelo sistema operacional.

Para desabilitar os backups:

```bash
python3 scripts/audit-envs.py --no-backup
```

Utilize essa opção somente quando necessário.

## Modo Strict

Use:

```bash
python3 scripts/audit-envs.py --strict
```

para retornar o código de saída `1` quando problemas estruturais permanecerem.

O modo strict considera condições como:

- `.env.example` ausente;
- arquivos de ambiente reais ausentes;
- divergência de chaves;
- variáveis duplicadas;
- possíveis secrets no `.env.example`.

Para também tratar variáveis sem referências detectadas como falhas:

```bash
python3 scripts/audit-envs.py --strict --strict-unused
```

`--strict-unused` requer `--strict`.

Como a execução normal remove variáveis completamente não utilizadas, variáveis removidas com sucesso não permanecem como problemas finais no modo strict.

## Auditando Outro Diretório

Por padrão, o ENV Auditor utiliza o diretório atual:

```bash
python3 scripts/audit-envs.py
```

Uma raiz de workspace diferente pode ser fornecida:

```bash
python3 scripts/audit-envs.py /path/to/workspace
```

Dry run:

```bash
python3 scripts/audit-envs.py /path/to/workspace --dry-run
```

Somente auditoria:

```bash
python3 scripts/audit-envs.py /path/to/workspace --audit-only
```

## Opções da CLI

```text
--strict

    Retorna o código de saída 1 quando problemas estruturais permanecem.

--strict-unused

    Utilizado em conjunto com --strict.

    Também falha quando uma variável não possui uso detectado.

--audit-only

    Apenas analisa.

    Não sincroniza nem remove variáveis.

--dry-run

    Simula sincronização e limpeza sem modificar arquivos.

--no-backup

    Desabilita backups antes de modificar arquivos existentes.

--show-usage

    Exibe arquivos contendo evidências fortes ou fracas de uso.
```

Não existe a opção `--remove-unused`.

A remoção de variáveis completamente não utilizadas faz parte do comportamento padrão da execução.

## Configuração

Um arquivo de configuração opcional pode ser criado na raiz do workspace:

```text
.env-audit.json
```

Exemplo:

```json
{
  "public_non_secret_keys": ["PUBLIC_CLIENT_KEY"],
  "ignore_unused_keys": ["EXTERNALLY_MANAGED_VARIABLE"],
  "ignore_projects": ["legacy-project"],
  "ignore_files": ["generated/config.js"]
}
```

O próprio arquivo `.env-audit.json` é excluído da detecção de uso para evitar falsos positivos.

### `public_non_secret_keys`

Alguns nomes de variáveis podem parecer sensíveis mesmo que seus valores sejam intencionalmente públicos.

Essas chaves podem ser explicitamente permitidas:

```json
{
  "public_non_secret_keys": ["PUBLIC_CLIENT_KEY"]
}
```

### `ignore_unused_keys`

Algumas variáveis podem ser consumidas fora da árvore de código-fonte e, portanto, não podem ser detectadas por meio da análise estática.

Exemplo:

```json
{
  "ignore_unused_keys": ["SERVER_INJECTED_VARIABLE"]
}
```

Essas variáveis:

- não são tratadas como não utilizadas;
- não são removidas automaticamente dos arquivos de ambiente;
- não são removidas do `.env.example`.

Isso é útil para variáveis fornecidas por sistemas como:

- pipelines de CI/CD;
- GitHub Actions;
- GitLab CI;
- Docker Swarm;
- Kubernetes;
- systemd;
- plataformas de deploy;
- scripts externos;
- configuração do servidor;
- outra aplicação ou serviço.

### `ignore_projects`

Diretórios inteiros podem ser excluídos da descoberta:

```json
{
  "ignore_projects": ["legacy-project"]
}
```

### `ignore_files`

Arquivos específicos podem ser excluídos da análise de uso:

```json
{
  "ignore_files": ["generated/config.js"]
}
```

## Diretórios Ignorados

Os seguintes diretórios são ignorados por padrão:

```text
.git
.idea
.vscode
.env-audit-backups
node_modules
storage
vendor
__pycache__
bootstrap/cache
public/build
```

Documentação, arquivos binários e assets comuns também são excluídos.

Exemplos:

```text
.png
.jpg
.jpeg
.gif
.webp
.ico
.pdf
.zip
.gz
.tar
.tgz
.7z
.woff
.woff2
.ttf
.otf
.mp3
.mp4
.wav
.ogg
.webm
.jar
.class
.so
.dylib
.dll
.exe
.sqlite
.db
```

## Limitação Importante da Detecção Estática de Uso

Uma variável pode não aparecer no código-fonte do projeto e ainda assim ser necessária em runtime.

Exemplos incluem variáveis injetadas por:

- sistemas de CI/CD;
- GitHub Actions;
- GitLab CI;
- Kubernetes;
- Docker Swarm;
- systemd;
- provedores de hospedagem;
- infraestrutura externa ao workspace;
- scripts externos de deploy;
- outro serviço.

Quando isso acontecer, adicione a chave a:

```json
"ignore_unused_keys"
```

Por exemplo:

```json
{
  "ignore_unused_keys": ["EXTERNAL_VARIABLE", "SERVER_MANAGED_VARIABLE"]
}
```

Isso impede que o ENV Auditor remova essas variáveis.

## Configuração Específica de Ambiente

O ENV Auditor mantém intencionalmente a paridade de chaves entre o `.env.example` e todos os arquivos `.env` / `.env.*` no mesmo diretório.

Como resultado, uma chave encontrada inicialmente apenas no `.env.prod` pode ser:

1. adicionada ao `.env.example` com um valor vazio;
2. propagada como chave para os outros arquivos de ambiente.

Isso é intencional.

O `.env.example` atua como o contrato completo de variáveis de ambiente do projeto.

O valor real de produção nunca é propagado.

Se uma variável não deve fazer parte desse contrato, considere se ela realmente pertence a um arquivo de ambiente gerenciado pelo ENV Auditor.

## Fluxo de Trabalho Recomendado

Antes de modificar um projeto existente, execute:

```bash
python3 scripts/audit-envs.py --dry-run --show-usage
```

Revise os ambientes descobertos e as alterações planejadas.

Depois execute:

```bash
python3 scripts/audit-envs.py
```

Opcionalmente, realize posteriormente uma verificação somente leitura:

```bash
python3 scripts/audit-envs.py --audit-only --show-usage
```

## Notas de Segurança

O ENV Auditor foi projetado para evitar a exibição de valores de variáveis de ambiente.

No entanto, o gerenciamento de ambientes ainda exige cuidado:

- nunca faça commit de arquivos `.env` ou `.env.*` contendo credenciais reais;
- mantenha apenas valores seguros e placeholders no `.env.example`;
- mantenha os backups habilitados, a menos que exista um motivo específico para desabilitá-los;
- utilize `--dry-run` antes de aplicar alterações em projetos desconhecidos;
- utilize `ignore_unused_keys` para variáveis consumidas externamente;
- revise usos fracos quando necessário;
- não presuma que a ausência de uma referência no código-fonte prova que uma variável é desnecessária.

Um fluxo de trabalho seguro é:

```bash
# 1. Visualizar sincronização, limpeza e evidências de uso

python3 scripts/audit-envs.py --dry-run --show-usage

# 2. Revisar os arquivos de ambiente descobertos e as alterações planejadas

# 3. Aplicar sincronização e limpeza

python3 scripts/audit-envs.py

# 4. Opcionalmente, verificar o estado final sem modificar nada

python3 scripts/audit-envs.py --audit-only --show-usage
```

## Resumo

O ENV Auditor mantém um conjunto consistente de arquivos de ambiente sem propagar valores reais entre ambientes.

Ele suporta:

```text
.env
.env.*
```

incluindo arquivos como:

```text
.env.prod
.env.test
.env.local
.env.staging
.env.production
```

com:

```text
.env.example
```

atuando como o contrato compartilhado de variáveis de ambiente.

Uma execução normal:

```bash
python3 scripts/audit-envs.py
```

realiza:

```text
descoberta de ambientes

        +

agrupamento por projeto

        +

sincronização do .env.example

        +

sincronização dos ambientes

        +

validação estrutural

        +

detecção de uso

        +

preservação de referências fracas

        +

preservação de exclusões explícitas

        +

limpeza de variáveis não utilizadas

        +

backups
```

Para visualizar todas as alterações sem modificar arquivos:

```bash
python3 scripts/audit-envs.py --dry-run
```

Para inspecionar o workspace sem sincronização ou limpeza:

```bash
python3 scripts/audit-envs.py --audit-only
```
