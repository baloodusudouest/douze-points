<script>
  // Un podium de trois marches (2, 1, 3) : celui de la soirée, ou en plus petit celui d'un invité.
  import { drapeau } from '$lib/pays.js'
  let { places, petit = false } = $props()      // places : [{ c, points }] dans l'ordre 1, 2, 3
</script>

<ol class="podium" class:petit aria-label={petit ? 'Ton podium' : 'Podium de la soirée'}>
  {#each [1, 0, 2] as place}
    {#if places[place]}
      <li class="marche m{place + 1}">
        <span class="drap">{drapeau(places[place].c.pays, places[place].c.code_pays)}</span>
        <span class="pays">{places[place].c.pays}</span>
        <span class="chiffre points">{places[place].points}</span>
        <span class="socle chiffre">{place + 1}</span>
      </li>
    {/if}
  {/each}
</ol>

<style>
  .podium { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); align-items: end; gap: 0.4rem; margin-top: 0.75rem; }
  .marche { display: flex; min-width: 0; flex-direction: column; align-items: center; animation: monter 0.7s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
  .m1 { animation-delay: 0.5s; } .m2 { animation-delay: 0.25s; }
  .drap { font-size: 2.2rem; line-height: 1.1; }
  .pays { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.95rem; }
  .points { font-size: 1.6rem; color: var(--primary); }
  .socle { display: grid; width: 100%; place-items: start center; border-radius: 0.5rem 0.5rem 0 0; border: 1px solid var(--border); border-bottom: 0;
    background: var(--card); padding-top: 0.2rem; font-size: 1.2rem; color: var(--muted-foreground); }
  .m1 .socle { height: 6.5rem; background: var(--primary); color: var(--primary-foreground); border-color: var(--primary); }
  .m2 .socle { height: 4.5rem; } .m3 .socle { height: 3rem; }
  .petit .drap { font-size: 1.5rem; } .petit .pays { font-size: 0.8rem; } .petit .points { font-size: 1.1rem; color: #a98be6; }
  .petit .m1 .socle { height: 3.5rem; background: #8f6ad8; border-color: #8f6ad8; color: #fff; } .petit .m2 .socle { height: 2.5rem; } .petit .m3 .socle { height: 1.75rem; }
  @keyframes monter { from { opacity: 0; transform: translateY(2rem); } to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) { .marche { animation: none; } }
</style>
