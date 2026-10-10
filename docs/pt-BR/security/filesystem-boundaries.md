# Segurança do filesystem e recuperação em texto puro

[English](../../en/security/filesystem-boundaries.md) | [Português brasileiro](filesystem-boundaries.md)

Revisão estática do código: 2026-10-10. Fatos implementados, teoria geral e mudanças hipotéticas são separados abaixo. Comandos runtime não foram executados.

As entradas precisam ser arquivos regulares; a descoberta ignora links simbólicos e o processamento verifica novamente o tipo do arquivo. O parser rejeita UTF-8 inválido, bytes NUL, atribuições malformadas e aspas sem fechamento. Essas verificações reduzem percurso acidental e transformações inválidas; não há bloqueio de arquivos nem percurso por descritores livre de corridas. Um caminho pode mudar entre a verificação e o uso. Isso não deve ser descrito como sandbox de filesystem adversarial.

Valores não aparecem no terminal, mas caminhos e nomes de chaves permanecem visíveis. Valores de referência são literais confiados: o programa não detecta segredos. Backups contêm bytes originais e blocos removidos em texto puro. Diretórios de sessão usam 0700, arquivos usam 0600 e o ignore da raiz de backup contém `*`. Isso reduz acesso comum e inclusão acidental no Git, mas não cifra backups, não protege contra o mesmo usuário e não define retenção. Bits de permissão do alvo existente são preservados; proprietário, ACLs e atributos estendidos não são.

Um alvo existente alterado recebe backup antes da substituição. O temporário no mesmo diretório recebe flush, fsync, chmod e substitui o alvo com `os.replace`. Isso oferece substituição por arquivo, não transação de múltiplos arquivos. O diretório não recebe fsync e escritores concorrentes podem ser sobrescritos. Durabilidade mais forte exigiria sincronização do diretório; coordenação de escritores exigiria bloqueio e detecção de mudanças. Ambas são alterações hipotéticas. Nenhum ambiente real ou backup foi inspecionado nesta revisão documental.
