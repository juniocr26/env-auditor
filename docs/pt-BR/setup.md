# Instalação e recuperação

Execute no diretório `env-auditor/` do host. Não há Dockerfile, serviços Compose, profiles, entrypoints, manifest de pacotes ou dependências externas. A CLI exige Python 3.10+ e usa a biblioteca padrão. Não é necessário introduzir Docker ou ambiente virtual artificial. A auditoria anterior executou `--help` com Python 3.14.7.

## Preparação e operação segura

```sh
python3 --version
python3 scripts/audit-envs.py --help
# Análise somente leitura de um diretório escolhido explicitamente:
python3 scripts/audit-envs.py /path/to/selected/project --audit-only
```

Substitua o último caminho pelo projeto desejado. A execução normal sincroniza/remove chaves e cria backups; não serve como verificação inofensiva de dependências. `--audit-only` evita alterações. Nenhuma auditoria ou mutação de todo o workspace foi executada na auditoria anterior.

| Componente | Caminho no container | Caminho no host | Montagem / finalidade |
| --- | --- | --- | --- |
| Python e biblioteca padrão | Não se aplica | Distribuição Python instalada | Nenhuma; runtime e biblioteca incluída |

Não há instalação/recuperação de dependências, cache, node_modules, vendor ou ambiente gerado exigido. Se o interpretador estiver ausente, restaure-o pela ferramenta do host usada originalmente; o projeto não prescreve instalador. Bytecode Python é artefato descartável, não configuração personalizada. A compatibilidade depende do interpretador do host, não de pacotes Linux.

## Recuperação de configuração

`.env-audit.json` é JSON personalizado opcional; não existe template versionado nem comando de geração. Exclusões/allowlists perdidas exigem backup ou reconfiguração deliberada conforme o [guia](guide.md). Instalar dependências não as recupera. `.env-audit-backups/` contém backups gerados por execuções com escrita, não por verificações somente leitura. Excluí-lo elimina o histórico de recuperação; restaure de outro backup. Não execute a ferramenta apenas para fabricar backups substitutos.

Para script ou documentação versionados ausentes, confirme a ausência e restaure somente o caminho específico:

```sh
test -e scripts/audit-envs.py || git restore --source=HEAD -- scripts/audit-envs.py
```

Nos projetos-alvo, restaure templates ausentes e obtenha valores reais de backups/fontes de segredos. ENV Auditor pode gerar chaves vazias ou copiar defaults seguros, mas não reconstrói configurações/credenciais excluídas. Nunca sobrescreva configuração existente.

## Encerramento e solução de problemas

A CLI termina após executar; não há containers, portas ou volumes persistentes para parar. Erros de permissão exigem leitura dos arquivos selecionados e, para escrita intencional, acesso aos arquivos/backups específicos. Não altere permissões de forma ampla. Mounts Docker ocultos e containers parados não se aplicam. Não adicione comandos pip/uv: o script importa apenas biblioteca padrão.

## Auditoria anterior — 2026-10-06

Inventário versionado, README, imports e CLI revisados. Versão Python e `--help` conferidos sem alterar configurações. Persistência de dependências externas no host não se aplica; não é um sucesso de persistência Docker. Instalação, recriação, recuperação em containers e startup da aplicação não se aplicam. Nenhum container ou recurso temporário foi criado naquela auditoria. Veja [a validação documental](verification.md) para novas verificações.
