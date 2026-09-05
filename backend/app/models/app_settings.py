"""
NAO USADO MAIS.

Chegou a existir um recurso de editar o intervalo de odds pela propria
tela (guardando o valor aqui, numa tabela `app_settings`), mas foi
revertido a pedido do usuario: agora os 3 intervalos automaticos
(scan/coleta/odds) so podem ser mudados no .env, sem edicao pela tela -
ver app/routers/settings.py (virou so-leitura) e app/services/scheduler.py.

Este arquivo fica so para nao quebrar quem ainda tiver a tabela
`app_settings` no banco (ela e inofensiva, simplesmente parou de ser lida
ou escrita por qualquer parte do sistema). Pode ser apagado com seguranca.
"""
