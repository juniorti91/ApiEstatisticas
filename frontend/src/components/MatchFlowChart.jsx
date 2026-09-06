// Mini-grafico de "fluxo da partida" (pressao recente de cada time),
// embutido direto no card do placar (LiveMatchCard) - fica visivel em
// TODAS as abas, sem precisar entrar em Prognosticos. Cada barra usa o
// Indice de Momentum (0-100, janela nao-acumulativa de 15min) calculado
// pelo backend a partir dos MESMOS snapshots que ja coletamos (ver
// app/services/prognostics_service.compute_momentum_series) - nao gera
// nenhuma chamada nova a API-Football, e nao inventa nenhum numero: e a
// mesma metrica que aparece com detalhe na aba Prognosticos, so que numa
// visualizacao compacta tipo "sparkline".
//
// Layout: uma barra por lado do centro (casa pra cima em azul, fora pra
// baixo em vermelho - mesmas cores usadas no resto do app), altura
// proporcional ao momentum daquele ponto no tempo.

export default function MatchFlowChart({ series, homeName, awayName }) {
  const points = series || [];
  if (points.length < 2) {
    // Precisa de pelo menos 2 pontos pra um "fluxo" fazer sentido -
    // antes disso (comeco de jogo) so mostra um aviso discreto em vez de
    // uma barra unica sem contexto nenhum.
    return (
      <div className="text-[11px] text-muted text-center py-2">
        Fluxo da partida aparece após os primeiros minutos coletados.
      </div>
    );
  }

  const BAR_MAX_PX = 22; // altura maxima de cada metade (acima/abaixo do eixo)

  return (
    <div className="pt-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-muted tracking-wide">FLUXO DA PARTIDA</span>
        <span className="text-[10px] text-muted">{points[0].minute}' - {points[points.length - 1].minute}'</span>
      </div>
      <div className="flex items-end gap-[3px]" style={{ height: `${BAR_MAX_PX * 2 + 2}px` }}>
        {points.map((p, i) => {
          const homeHeight = Math.max(2, (p.home / 100) * BAR_MAX_PX);
          const awayHeight = Math.max(2, (p.away / 100) * BAR_MAX_PX);
          return (
            <div key={i} className="flex-1 flex flex-col items-center justify-end" style={{ height: `${BAR_MAX_PX * 2 + 2}px` }}>
              <div
                className="w-full rounded-t-sm bg-blue-500"
                style={{ height: `${homeHeight}px` }}
                title={`${homeName}: ${p.home.toFixed(0)} aos ${p.minute}'`}
              />
              <div className="w-full h-px bg-border shrink-0" />
              <div
                className="w-full rounded-b-sm bg-red-500"
                style={{ height: `${awayHeight}px` }}
                title={`${awayName}: ${p.away.toFixed(0)} aos ${p.minute}'`}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
