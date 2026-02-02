const TEXT = {
  thread_only: {
    pt: '❌ Este comando só pode ser usado dentro de uma thread do fórum.',
    en: '❌ This command can only be used inside a forum thread.',
  },
  qty_invalid: {
    pt: '❌ A quantidade precisa ser maior que zero.',
    en: '❌ Quantity must be greater than zero.',
  },
  request_created: {
    pt: (
      '📦 **Request criado / atualizado**\n'
      + 'Player: {player}\n'
      + 'Item: **{item}**\n'
      + 'Quantidade total: **{qty}**'
    ),
    en: (
      '📦 **Request created / updated**\n'
      + 'Player: {player}\n'
      + 'Item: **{item}**\n'
      + 'Total quantity: **{qty}**'
    ),
  },
  request_updated: {
    pt: '✅ Atualização registrada. Contador de inatividade resetado.',
    en: '✅ Update registered. Inactivity counter reset.',
  },
  request_not_found: {
    pt: '❌ Nenhum request ativo encontrado nesta thread.',
    en: '❌ No active request found in this thread.',
  },
  deliver_ok: {
    pt: '📦 Entrega registrada. Quantidade entregue: **{qty}**',
    en: '📦 Delivery registered. Quantity delivered: **{qty}**',
  },
  rank_empty: {
    pt: '❌ Nenhum request encontrado para esse item.',
    en: '❌ No requests found for this item.',
  },
  rank_header: {
    pt: '📊 **Ranking — {item}**',
    en: '📊 **Ranking — {item}**',
  },
  rank_line: {
    pt: 'Falta: `{remaining}` [🔗]({link})',
    en: 'Remaining: `{remaining}` [🔗]({link})',
  },
  request_info: {
    pt: (
      '🧾 **Informações do Request**\n'
      + 'Player: **{player}**\n'
      + 'Item: **{item}**\n'
      + 'Rank: **{rank}º**\n'
      + 'Dias sem update: **{days}**\n'
      + '[🔗 Ir para a thread]({link})'
    ),
    en: (
      '🧾 **Request info**\n'
      + 'Player: **{player}**\n'
      + 'Item: **{item}**\n'
      + 'Rank: **#{rank}**\n'
      + 'Days without update: **{days}**\n'
      + '[🔗 Go to thread]({link})'
    ),
  },
  idle_3d: {
    pt: '⚠️ <@{player}> seu request de **{item}** está **3 dias sem update**. Envie print.',
    en: '⚠️ <@{player}> your **{item}** request is **3 days idle**. Please post an update.',
  },
  idle_4d: {
    pt: '🚨 <@{player}> **4 dias sem update** no request de **{item}**. Último aviso.',
    en: '🚨 <@{player}> **4 days without update** on **{item}** request. Final warning.',
  },
  rank_down: {
    pt: '⬇️ <@{player}> seu request de **{item}** caiu **1 posição no ranking** por inatividade.',
    en: '⬇️ <@{player}> your **{item}** request dropped **1 rank position** due to inactivity.',
  },
};

module.exports = {
  TEXT,
};
