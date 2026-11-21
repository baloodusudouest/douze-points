<script>
  // 1.8 (choix de Julien du 20/11/2026) : « Saisir sa grille » (grille papier d'un invité, recopiée par l'hôte).
  // Toute la liste d'un coup : une case pour la note, une pour son mot ; enregistré à la sortie de la case (PUT note,
  // comme sur un téléphone). Puis « Passer au classement » : l'étape existante, où l'on range à la main comme sur la
  // grille papier. Le passage attend la fin des enregistrements en cours ; une note refusée le bloque (conseil 1.8.0).
  import { drapeau, note, pointsDuClassement } from '$lib/pays.js'
  let { chansons, notes, cran = 0.5, ecrire, onclassement } = $props()

  // ce qui est écrit dans les cases (texte), chanson par chanson
  let cases = $state({})
  let erreurs = $state({})
  let enCours = $state(0)
  let attentes = []
  $effect(() => {
    for (const c of chansons) {
      if (cases[c.id]) continue
      const n = notes[c.id]
      cases[c.id] = { note: n ? note(n.valeur) : '', mot: n?.commentaire ?? '' }
    }
  })

  const lire = (t) => {
    const v = String(t).trim().replace(',', '.')
    if (v === '') return null
    const n = Number(v)
    return Number.isFinite(n) ? n : NaN
  }
  const libellePas = $derived(cran === 1 ? 'en points entiers' : cran === 0.25 ? 'par quart de point' : 'par demi-point')

  function verifier(id) {
    const v = lire(cases[id].note)
    if (v === null) return cases[id].mot.trim() ? 'Écris d\'abord la note.' : ''
    if (Number.isNaN(v) || v < 0 || v > 20 || Math.abs(Math.round(v / cran) * cran - v) > 1e-9) return `La note va de 0 à 20, ${libellePas}.`
    return ''
  }

  async function enregistrer(c) {
    const message = verifier(c.id)
    erreurs = { ...erreurs, [c.id]: message }
    if (message) return
    const v = lire(cases[c.id].note)
    const avant = notes[c.id]
    if (v === null && !avant) return
    if (v !== null && avant && avant.valeur === v && (avant.commentaire ?? '') === cases[c.id].mot.trim()) return
    enCours++
    const promesse = ecrire('PUT', 'note', v === null ? { chanson_id: c.id, valeur: null }
      : { chanson_id: c.id, valeur: v, commentaire: cases[c.id].mot.trim() })
    attentes.push(promesse)
    try {
      const d = await promesse
      if (!d) erreurs = { ...erreurs, [c.id]: 'Pas enregistrée : réessaie.' }
    } finally { enCours-- }
  }

  // les points d'après les notes, en direct (le classement à la main vient ensuite) ; à égalité, l'ordre de passage
  let points = $derived.by(() => {
    const notees = chansons.map((c) => ({ c, v: lire(cases[c.id]?.note ?? '') }))
      .filter((x) => x.v !== null && !Number.isNaN(x.v) && !erreurs[x.c.id])
      .sort((a, b) => b.v - a.v || a.c.ordre - b.c.ordre)
    // 1.12 : notre pays garde sa place, sans points
    return pointsDuClassement(notees.map((x) => x.c.id), new Set(chansons.filter((c) => c.hors_points).map((c) => c.id)))
  })
  let nbNotees = $derived(Object.keys(notes).length)
  let bloque = $derived(Object.values(erreurs).some(Boolean))

  // Appelé par le bouton « Passer au classement » du bas de l'écran (Invite.svelte)
  export async function passer() {
    // attendre ce qui part encore (la dernière case quittée en touchant ce bouton)
    await new Promise((r) => setTimeout(r, 0))
    await Promise.allSettled(attentes)
    attentes = []
    if (Object.values(erreurs).some(Boolean)) {
      document.querySelector('.ligne.erreur input')?.focus()
      return
    }
    onclassement()
  }
</script>

<p class="mb-3 text-sm text-muted-foreground">Recopie sa grille : la note sur 20, puis son mot s'il en a écrit un. Tu rangeras son classement à l'étape suivante.
  <span class="block" role="status">{enCours ? 'Enregistrement…' : `${nbNotees} note${nbNotees > 1 ? 's' : ''} sur ${chansons.length}`}{bloque ? ' · une note est à corriger' : ''}</span></p>
<ol class="grid gap-1" aria-label="Grille à recopier">
  {#each chansons as c (c.id)}
    {#if cases[c.id]}
      <li class="ligne" class:erreur={erreurs[c.id]}>
        <div class="flex min-w-0 items-center gap-2.5">
          <span class="w-6 shrink-0 text-right text-sm text-muted-foreground">{c.ordre}</span>
          <span class="shrink-0 text-2xl leading-none">{drapeau(c.pays, c.code_pays)}</span>
          <span class="min-w-0">
            <span class="block truncate font-medium">{c.pays}</span>
            <span class="block text-xs {points[c.id] ? 'text-primary' : 'text-muted-foreground'}">{erreurs[c.id] || (lire(cases[c.id].note) === null ? 'Pas encore notée' : points[c.id] ? (points[c.id] === 12 ? 'Douze points' : `${points[c.id]} points`) : c.hors_points ? 'Notre pays : pas de points' : 'Pas de points')}</span>
          </span>
        </div>
        <label class="block">
          <span class="sr-only">Note de {c.pays} sur 20</span>
          <input class="champ note" type="text" inputmode="decimal" autocomplete="off" placeholder="/20" bind:value={cases[c.id].note}
                 onchange={() => enregistrer(c)} aria-invalid={!!erreurs[c.id]} />
        </label>
        <label class="mot block">
          <span class="sr-only">Son mot sur {c.pays}</span>
          <input class="champ" type="text" maxlength="280" autocomplete="off" placeholder="Son mot (facultatif)" bind:value={cases[c.id].mot}
                 onchange={() => enregistrer(c)} />
        </label>
      </li>
    {/if}
  {/each}
</ol>

<style>
  .ligne { display: grid; grid-template-columns: minmax(0, 1fr) 4.8rem; gap: 0.5rem 0.6rem; align-items: center; padding: 0.7rem 0;
    border-bottom: 1px solid var(--border); }
  .ligne .mot { grid-column: 1 / -1; padding-left: 2rem; }
  .champ { width: 100%; min-height: 2.75rem; border-radius: 0.75rem; border: 1px solid var(--border); background: var(--card); padding: 0 0.75rem;
    font-size: 1rem; color: var(--foreground); }
  .champ.note { min-height: 3rem; text-align: center; font-size: 1.25rem; font-weight: 600; font-variant-numeric: tabular-nums; padding: 0 0.3rem; }
  .champ:focus { outline: 2px solid var(--primary); outline-offset: 1px; border-color: transparent; }
  .ligne.erreur .champ.note { border-color: var(--destructive); }
  .ligne.erreur .text-xs { color: var(--destructive); }
</style>
