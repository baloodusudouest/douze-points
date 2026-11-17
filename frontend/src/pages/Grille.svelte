<script>
  // La grille papier de secours (1.3) : une page par invité attendu (son prénom en tête) et une page vierge.
  // Chansons dans l'ordre de passage, une case pour la note sur 20 et une pour le mot, puis les dix lignes du
  // classement (12, 10, 8… 1). Si l'appli tombe, la soirée continue sur papier ; sinon, l'hôte recopie une grille
  // remplie avec « Saisir sa grille » (écran Soirée), au nom de l'invité.
  import { EMISSIONS, normaliser } from '$lib/pays.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Drapeau from '$lib/Drapeau.svelte'
  let { soiree, onferme } = $props()

  const BAREME = [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]
  let chansons = $derived(soiree.chansons.map(normaliser))
  let pages = $derived([...soiree.participants.map((p) => p.prenom), ''])
</script>

<div class="grille-papier">
  <div class="mb-4 flex flex-wrap items-center gap-2 print:hidden">
    <Button variant="outline" onclick={onferme}>Retour</Button>
    <p class="mr-auto text-sm text-muted-foreground">{pages.length - 1} grille{pages.length > 2 ? 's' : ''} au prénom des invités attendus, et une vierge.</p>
    <Button onclick={() => window.print()}>Imprimer</Button>
  </div>

  {#each pages as prenom, k}
    <section class="page" class:suite={k > 0} aria-label={prenom ? `Grille de ${prenom}` : 'Grille vierge'}>
      <header class="entete">
        <div>
          <h1>{soiree.nom}</h1>
          <p>{soiree.concours} {soiree.annee}, {EMISSIONS[soiree.emission].toLowerCase()}</p>
        </div>
        <p class="prenom">Prénom : <span class="ecrit">{prenom}</span></p>
      </header>

      <table class="notes">
        <thead><tr><th class="n">N°</th><th class="g">Chanson</th><th class="note">Note /20</th><th class="g">Mon mot</th></tr></thead>
        <tbody>
          {#each chansons as c (c.id)}
            <tr>
              <td class="n">{c.ordre}</td>
              <td class="g"><Drapeau pays={c.pays} code={c.code_pays} /><strong>{c.pays}</strong>
                {#if c.artiste || c.titre}<span class="sous">{c.artiste}{c.titre ? ', ' + c.titre : ''}</span>{/if}</td>
              <td class="note"><span class="case"></span></td>
              <td class="mot"></td>
            </tr>
          {/each}
        </tbody>
      </table>

      <h2>Mon classement</h2>
      <p class="aide">Range tes dix chansons préférées : c'est ce classement qui donne les points.</p>
      <table class="classement">
        <tbody>
          {#each BAREME as pts}
            <tr><td class="pts">{pts}</td><td class="g">points</td><td class="ligne-vide"></td></tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/each}
</div>

<style>
  .page { margin-bottom: 2rem; border: 1px solid var(--border); border-radius: 1rem; background: var(--card); padding: 1.25rem; }
  .entete { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
  .entete h1 { font-size: 1.4rem; font-weight: 300; letter-spacing: -0.02em; }
  .entete p { font-size: 0.85rem; color: var(--muted-foreground); }
  .prenom { font-size: 1rem !important; color: var(--foreground) !important; }
  .ecrit { display: inline-block; min-width: 10rem; border-bottom: 1px solid currentColor; padding: 0 0.3rem; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th, td { border: 1px solid var(--border); padding: 0.3rem 0.45rem; vertical-align: middle; }
  th { font-weight: 500; color: var(--muted-foreground); text-align: center; }
  .g { text-align: left; }
  .n { width: 2.2rem; text-align: center; color: var(--muted-foreground); }
  .note { width: 5.5rem; text-align: center; }
  .case { display: inline-block; width: 3.2rem; height: 1.5rem; border: 1px solid var(--muted-foreground); border-radius: 0.3rem; }
  .mot { width: 40%; }
  .sous { display: block; font-size: 0.72rem; color: var(--muted-foreground); }
  h2 { margin-top: 1.1rem; font-size: 1.05rem; font-weight: 600; }
  .aide { margin-bottom: 0.4rem; font-size: 0.78rem; color: var(--muted-foreground); }
  .classement { max-width: 32rem; }
  .pts { width: 2.6rem; text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }
  .classement .g { width: 4rem; color: var(--muted-foreground); }
  .ligne-vide { height: 1.75rem; }

  /* À l'impression : noir sur blanc, une page par invité */
  @media print {
    .page { border: 0; border-radius: 0; background: none; padding: 0; margin: 0; color: #000; }
    .page.suite { break-before: page; }
    th, td { border-color: #888; }
    th, .n, .sous, .aide, .classement .g, .entete p { color: #444; }
    .prenom { color: #000 !important; }
    .case { border-color: #555; }
    tr { break-inside: avoid; }
    :global(.drapeau-image) { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
  }
</style>
