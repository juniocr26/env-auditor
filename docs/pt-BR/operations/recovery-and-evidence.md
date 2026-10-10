# Operação, falhas e limites de evidência

[English](../../en/operations/recovery-and-evidence.md) | [Português brasileiro](recovery-and-evidence.md)

Revisão estática do código: 2026-10-10. Fatos implementados, teoria geral e mudanças hipotéticas são separados abaixo. Comandos runtime não foram executados.

Consulte o contrato da CLI no README antes de sincronizar. `--dry-run` e `--audit-only` são aliases mutuamente exclusivos da mesma prévia somente leitura. Não criam alvos nem backups. Uma diferença proposta sozinha termina com 0; erros tratados de descoberta/par retornam 1; raiz ou argumentos inválidos retornam 2. Links ignorados e referências ausentes, isoladamente, não são erros. A prévia não comprova futura permissão ou sucesso do backup.

A gravação acontece ao invocar o comando normal, não por daemon em segundo plano. Erros são tratados por par, permitindo continuar os demais; gravações anteriores bem-sucedidas não são revertidas. Se o backup falha, a substituição não começa. Se a substituição falha, backups ou artefatos temporários parciais podem permanecer. O operador deve analisar o relatório de identificadores, localizar a sessão exata de backup e restaurar deliberadamente o original desejado após verificar edições concorrentes. Não há rollback em massa, retenção ou recuperação automática de crash. Falhas de saída e recursão patológica podem escapar do mapeamento usual de erros.

A suíte `unittest` existente usa fixtures temporárias isoladas para parser, variantes, prévia, backups, falhas de substituição, permissões e idempotência. Registros de verificação existentes são históricos, não execuções desta revisão. Nenhum teste de aplicação ou runtime foi executado aqui. A instalação distribui o script com Python 3.10+; mover o script altera sua raiz padrão. Não há implantação de serviço, banco, topologia Docker, pagamentos ou API de rede a documentar. Uma comparação na biblioteca pode abordar esses conceitos sem sugerir que as outras aplicações do portfólio chamam a CLI.

Lacunas de evidência: durabilidade sob crash/queda de energia, escritores concorrentes e corridas no filesystem, portabilidade de ACL/proprietário, árvores muito profundas, retenção de backups e medições de escala. Exigem implementação autorizada separadamente e experimentos isolados; não há alegação de vazão ou compatibilidade completa com parser shell.
