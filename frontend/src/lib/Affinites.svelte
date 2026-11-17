<script>
  // Écarts et affinités d'une soirée (1.3) : qui note comme qui, la chanson qui divise, celle qui rassemble,
  // le plus sévère et le plus généreux, les coups de cœur solitaires, les chansons classées à contre-note.
  // Les mêmes tuiles dans la fiche de la régie et sur les téléphones, une fois le dévoilement fini.
  // `affinites` vient du serveur (identifiants) ; rien n'est affiché sous trois invités (le serveur rend null).
  import { note } from '$lib/pays.js'
  import Drapeau from '$lib/Drapeau.svelte'
  let { affinites, prenoms, chansons, compact = false } = $props()

  const p = (id) => prenoms[id] ?? '?'
  const c = (id) => chansons[id] ?? { pays: '?', code_pays: '' }
  let a = $derived(affinites)
  let rien = $derived(!a || (!a.clivante && !a.proches && !a.severe && !a.coups_de_coeur.length && !a.contre_note.length))
</script>

{#snippet pays(id)}{@const x = c(id)}<span class="whitespace-nowrap"><Drapeau pays={x.pays} code={x.code_pays} />{x.pays}</span>{/snippet}

{#if !rien}
  <div class="grille" class:compact>
    {#if a.clivante}
      <article class="tuile">
        <p class="etiquette">La chanson qui divise</p>
        <p class="fort">{@render pays(a.clivante.chanson)}</p>
        <p class="detail">De {note(a.clivante.basse.note)} ({p(a.clivante.basse.invite)}) à {note(a.clivante.haute.note)} ({p(a.clivante.haute.invite)}) : {note(a.clivante.ecart)} points d'écart.</p>
      </article>
      <article class="tuile">
        <p class="etiquette">La chanson qui rassemble</p>
        <p class="fort">{@render pays(a.consensuelle.chanson)}</p>
        <p class="detail">{#if a.consensuelle.ecart === 0}Tout le monde lui a donné {note(a.consensuelle.moyenne)}/20.{:else}Toutes les notes à {note(a.consensuelle.ecart)} point{a.consensuelle.ecart >= 2 ? 's' : ''} près, autour de {note(a.consensuelle.moyenne)}/20.{/if}</p>
      </article>
    {/if}
    {#if a.proches}
      <article class="tuile">
        <p class="etiquette">Ils notent pareil</p>
        <p class="fort">{p(a.proches.invites[0])} et {p(a.proches.invites[1])}</p>
        <p class="detail">{note(a.proches.ecart_moyen)} point{a.proches.ecart_moyen >= 2 ? 's' : ''} d'écart en moyenne sur {a.proches.communes} chansons.</p>
      </article>
      <article class="tuile">
        <p class="etiquette">Ils ne sont d'accord sur rien</p>
        <p class="fort">{p(a.eloignes.invites[0])} et {p(a.eloignes.invites[1])}</p>
        <p class="detail">{note(a.eloignes.ecart_moyen)} points d'écart en moyenne sur {a.eloignes.communes} chansons.</p>
      </article>
    {/if}
    {#if a.severe}
      <article class="tuile">
        <p class="etiquette">Le plus sévère</p>
        <p class="fort">{p(a.severe.invite)}</p>
        <p class="detail">{note(a.severe.moyenne)}/20 de moyenne.</p>
      </article>
      <article class="tuile">
        <p class="etiquette">Le plus généreux</p>
        <p class="fort">{p(a.genereux.invite)}</p>
        <p class="detail">{note(a.genereux.moyenne)}/20 de moyenne.</p>
      </article>
    {/if}
    {#if a.coups_de_coeur.length}
      <article class="tuile large">
        <p class="etiquette">Coup de cœur solitaire</p>
        <ul class="detail">
          {#each a.coups_de_coeur as x}
            <li><strong>{p(x.invite)}</strong> a donné son 12 à {@render pays(x.chanson)}{x.note != null ? ` (${note(x.note)}/20)` : ''}, et personne d'autre ne lui a donné un point.</li>
          {/each}
        </ul>
      </article>
    {/if}
    {#if a.contre_note.length}
      <article class="tuile large">
        <p class="etiquette">Classée à contre-note</p>
        <ul class="detail">
          {#each a.contre_note as x}
            <li><strong>{p(x.invite)}</strong> a mis {@render pays(x.devant)} ({note(x.note_devant)}/20) devant {@render pays(x.derriere)} ({note(x.note_derriere)}/20).</li>
          {/each}
        </ul>
      </article>
    {/if}
  </div>
{/if}

<style>
  .grille { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr)); }
  .grille.compact { grid-template-columns: 1fr 1fr; gap: 0.5rem; }
  .tuile { display: flex; flex-direction: column; gap: 0.2rem; border: 1px solid var(--border); border-radius: 1rem;
    background: var(--card); padding: 0.85rem 1rem; break-inside: avoid; }
  .large { grid-column: 1 / -1; }
  .etiquette { font-size: 0.75rem; letter-spacing: 0.02em; color: var(--muted-foreground); }
  .fort { font-size: 1.1rem; font-weight: 600; }
  .compact .fort { font-size: 1rem; }
  .detail { font-size: 0.85rem; color: var(--muted-foreground); }
  .detail li + li { margin-top: 0.3rem; }
  .detail strong { color: var(--foreground); font-weight: 600; }
  @media print {
    .tuile { border-color: #bbb; background: none; }
    .etiquette, .detail { color: #444; }
    .fort, .detail strong { color: #000; }
  }
</style>
