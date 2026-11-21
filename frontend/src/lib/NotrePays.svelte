<script>
  // 1.12 : « Et notre pays ? », après le podium (télé et téléphones) et dans la fiche. Notre pays a été noté et classé
  // comme les autres, mais ne reçoit pas de points (comme au concours) : on montre la moyenne des notes du groupe et la
  // place qu'il aurait eue d'après ces notes. `bilan` : { chanson, moyenne, place_notes, sur, notes } (serveur) ;
  // `chanson` : { pays, code_pays, artiste, titre }. `grand` : la version de la télé.
  import { drapeau, note } from '$lib/pays.js'
  let { bilan, chanson, grand = false } = $props()
  const place = (n) => (n === 1 ? '1re' : `${n}e`)
</script>

{#if bilan && chanson}
  <section class="notre text-center" class:grand aria-label="Et notre pays ?">
    <p class="titre font-light text-muted-foreground">Et notre pays ?</p>
    <p class="pays mt-1 truncate font-light tracking-tight">{drapeau(chanson.pays, chanson.code_pays)} {chanson.pays}</p>
    {#if chanson.artiste || chanson.titre}<p class="truncate text-sm text-muted-foreground">{chanson.artiste}{chanson.titre ? ' – ' + chanson.titre : ''}</p>{/if}
    {#if bilan.moyenne !== null && bilan.moyenne !== undefined}
      <p class="chiffre moyenne mt-2">{note(bilan.moyenne)}<span class="sur">/20</span></p>
      <p class="text-muted-foreground">de moyenne pour le groupe</p>
      {#if bilan.place_notes}
        <p class="mt-2">D'après les notes, {place(bilan.place_notes)} sur {bilan.sur}.</p>
      {/if}
    {:else}
      <p class="mt-3 text-muted-foreground">Personne ne l'a notée.</p>
    {/if}
    <p class="mt-3 text-sm text-muted-foreground">Comme au concours, on ne vote pas pour son propre pays : aucun point.</p>
  </section>
{/if}

<style>
  .notre { margin-inline: auto; max-width: 28rem; border-radius: 1rem; border: 1px solid var(--border); background: var(--card); padding: 1rem 1.25rem; }
  .titre { font-size: 1.1rem; }
  .pays { font-size: 1.6rem; line-height: 1.2; }
  .moyenne { font-size: 3rem; line-height: 1; color: var(--primary); }
  .sur { font-size: 0.4em; color: var(--muted-foreground); margin-left: 0.15em; }
  .grand { max-width: none; border: 0; background: transparent; padding: 0; }
  .grand .titre { font-size: clamp(1.1rem, 4vh, 1.8rem); }
  .grand .pays { font-size: clamp(1.4rem, 8vh, 3rem); }
  .grand .moyenne { font-size: clamp(3rem, 18vh, 9rem); }
</style>
