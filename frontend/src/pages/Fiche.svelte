<script>
  // La fiche de la soirée : tout ce qui s'est dit (notes, commentaires), le classement du groupe, du jury et du
  // public, et la comparaison avec les vrais votes du concours, saisis ici quand ils sont connus.
  // Elle s'imprime (ou s'enregistre en PDF depuis l'impression) et se télécharge en tableau.
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { EMISSIONS, note, normaliser } from '$lib/pays.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Drapeau from '$lib/Drapeau.svelte'
  import Affinites from '$lib/Affinites.svelte'
  let { soiree, onferme } = $props()

  let f = $state(null)
  let erreur = $state('')
  let saisie = $state(null)        // les vrais votes en cours de saisie : { [chanson]: { jury, public } }
  let message = $state('')

  let j = $state(null)             // 1.6 : jumeaux de vote et photos de la soirée
  let renvoi = $state('')
  async function lire() {
    try {
      const lu = await api.get(`/api/soirees/${soiree}/fiche`)
      f = { ...lu, chansons: lu.chansons.map(normaliser) }
      j = await api.get(`/api/soirees/${soiree}/jumeaux`).catch(() => null)
    } catch (e) { erreur = e.message }
  }
  async function renvoyer() {
    renvoi = 'Envoi…'
    try {
      const r = await api.post('/api/photos/envoyer')
      renvoi = r.erreur ? `${r.erreur} : ${r.en_attente} en attente, nouvel essai dans 10 minutes.` : 'Toutes les photos sont dans Immich.'
      j = await api.get(`/api/soirees/${soiree}/jumeaux`)
    } catch (e) { renvoi = e.message }
  }
  onMount(lire)

  function ouvrirSaisie() {
    saisie = Object.fromEntries(f.chansons.map((c) => [c.id, { jury: c.officiel.jury ?? '', public: c.officiel.public ?? '' }]))
    message = ''
  }
  async function enregistrer() {
    erreur = ''
    try {
      await api.put(`/api/soirees/${soiree}/officiel`, { resultats: Object.entries(saisie).map(([id, v]) => ({ chanson_id: +id, jury: v.jury, public: v.public })) })
      saisie = null
      message = 'Vrais votes enregistrés.'
      await lire()
    } catch (e) { erreur = e.message }
  }

  const image = (sorte) => `/api/soirees/${soiree}/image/${sorte}?v=${f.soiree.images[sorte]}`
  let parRang = $derived(f ? [...f.chansons].sort((a, b) => a.rang - b.rang || a.ordre - b.ordre) : [])
  let aOfficiel = $derived(!!f && f.chansons.some((c) => c.officiel.total !== null))
  const phrase = (k) => k && `${k.meme_gagnant ? 'même gagnant' : 'pas le même gagnant'}, ${k.trois_premieres} chanson${k.trois_premieres > 1 ? 's' : ''} en commun dans les trois premières, ${note(k.ecart_moyen)} place${k.ecart_moyen >= 2 ? 's' : ''} d'écart en moyenne`
  const ecart = (nous, eux) => (nous == null || eux == null ? '' : eux === nous ? '=' : (eux - nous > 0 ? '+' : '−') + Math.abs(eux - nous))
</script>

<div class="fiche">
  <div class="mb-4 flex flex-wrap items-center gap-2 print:hidden">
    <Button variant="outline" onclick={onferme}>Retour</Button>
    {#if f}
      <span class="mr-auto"></span>
      <Button variant="outline" onclick={ouvrirSaisie}>{aOfficiel ? 'Corriger les vrais votes' : 'Saisir les vrais votes'}</Button>
      <a class="lien-bouton" href="/api/soirees/{soiree}/fiche.csv" download>Télécharger le tableau</a>
      <Button onclick={() => window.print()}>Imprimer ou enregistrer en PDF</Button>
    {/if}
  </div>
  {#if erreur}<p class="mb-3 text-sm text-destructive" role="alert">{erreur}</p>{/if}
  {#if message}<p class="mb-3 text-sm text-primary print:hidden" role="status">{message}</p>{/if}

  {#if f}
    {#if f.soiree.images.banniere}<img class="banniere" src={image('banniere')} alt="Bannière de l'évènement" />{/if}
    <header class="mb-5 flex items-center gap-4">
      {#if f.soiree.images.logo}<img class="logo" src={image('logo')} alt="Logo de l'évènement" />{/if}
      <div class="min-w-0">
      <h1 class="titre">{f.soiree.nom}</h1>
      <p class="mt-1 text-sm text-muted-foreground">{f.soiree.concours} {f.soiree.annee}, {EMISSIONS[f.soiree.emission].toLowerCase()}{f.soiree.ville ? `, ${f.soiree.ville}` : ''}.
        {f.invites.length} classements{f.soiree.forcee ? ', dévoilement forcé' : ''}.</p>
      </div>
    </header>

    {#if saisie}
      <section class="mb-6 rounded-2xl border bg-card p-5 print:hidden" aria-label="Vrais votes">
        <h2 class="text-lg font-semibold">Les vrais votes du concours</h2>
        <p class="text-sm text-muted-foreground">Les points donnés par le vrai jury et par le vrai public à chaque chanson. Une case vide reste sans valeur.</p>
        <div class="mt-3 grid gap-1">
          <div class="vrai text-xs text-muted-foreground"><span></span><span>Jury</span><span>Public</span></div>
          {#each f.chansons as c (c.id)}
            <div class="vrai">
              <span class="truncate">{c.ordre}. <Drapeau pays={c.pays} code={c.code_pays} />{c.pays}</span>
              <input class="saisie" type="number" min="0" inputmode="numeric" bind:value={saisie[c.id].jury} aria-label="{c.pays} : vrais points du jury" />
              <input class="saisie" type="number" min="0" inputmode="numeric" bind:value={saisie[c.id].public} aria-label="{c.pays} : vrais points du public" />
            </div>
          {/each}
        </div>
        <div class="mt-4 flex gap-2"><Button onclick={enregistrer}>Enregistrer les vrais votes</Button><Button variant="outline" onclick={() => (saisie = null)}>Annuler</Button></div>
      </section>
    {/if}

    <section class="bloc">
      <h2>Le classement de la soirée</h2>
      <div class="defile">
        <table>
          <thead><tr>
            <th>Rang</th><th class="g">Chanson</th><th>Points</th><th>Moyenne</th>
            {#if f.a_jury}<th>Jury</th><th>Public</th>{/if}
            {#if aOfficiel}<th>Vrai rang</th><th>Écart</th>{/if}
          </tr></thead>
          <tbody>
            {#each parRang as c (c.id)}
              <tr>
                <td class="chiffre">{c.rang}</td>
                <td class="g"><Drapeau pays={c.pays} code={c.code_pays} />{c.pays}<span class="sous">{c.artiste}{c.titre ? ', ' + c.titre : ''}</span></td>
                <td class="chiffre fort">{c.points}</td><td>{note(c.moyenne)}</td>
                {#if f.a_jury}<td>{c.jury.points} <span class="sous-ligne">({c.jury.rang}e)</span></td><td>{c.public.points} <span class="sous-ligne">({c.public.rang}e)</span></td>{/if}
                {#if aOfficiel}<td>{c.officiel.rang ?? ''}</td><td>{ecart(c.rang, c.officiel.rang)}</td>{/if}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    {#if f.affinites}
      <section class="bloc">
        <h2>Écarts et affinités</h2>
        <Affinites affinites={f.affinites} prenoms={Object.fromEntries(f.invites.map((i) => [i.id, i.prenom]))}
                   chansons={Object.fromEntries(f.chansons.map((c) => [c.id, c]))} />
      </section>
    {/if}

    {#if j && (j.duos.length || j.photos.total)}
      <section class="bloc">
        <h2>Jumeaux de vote et photos</h2>
        {#if j.duos.length}
          <ul class="grid gap-1 text-sm">
            {#each j.duos as d (d.cle)}
              <li>{d.invites[0].prenom} {d.reciproques ? '⇄' : '→'} {d.invites[1].prenom} · {d.tranche}{d.photos ? ' · 📸 immortalisés' : ''}</li>
            {/each}
          </ul>
        {/if}
        {#if j.photos.total}
          <p class="mt-2 text-sm">
            {j.photos.total} photo{j.photos.total > 1 ? 's' : ''} ce soir, {j.photos.dans_immich === j.photos.total ? 'toutes dans Immich' : `${j.photos.dans_immich} dans Immich`}
            · album « {j.album.nom} »{#if j.album.lien} · <a class="underline" href={j.album.lien} target="_blank" rel="noopener">ouvrir dans Immich</a>{/if}
          </p>
          {#if j.photos.dans_immich < j.photos.total}
            <p class="mt-1 text-sm text-muted-foreground print:hidden">{j.photos.erreur || 'En cours d’envoi.'}
              <button class="underline" onclick={renvoyer}>Renvoyer maintenant</button>{#if renvoi} · {renvoi}{/if}</p>
          {/if}
        {/if}
      </section>
    {/if}

    {#if aOfficiel}
      <section class="bloc">
        <h2>Notre soirée face aux vrais votes</h2>
        <ul class="grid gap-1 text-sm">
          {#if f.comparaison.ensemble}<li><strong>Ensemble :</strong> {phrase(f.comparaison.ensemble)}.</li>{/if}
          {#if f.comparaison.jury}<li><strong>Notre jury et le vrai jury :</strong> {phrase(f.comparaison.jury)}.</li>{/if}
          {#if f.comparaison.public}<li><strong>Notre public et le vrai public :</strong> {phrase(f.comparaison.public)}.</li>{/if}
        </ul>
        <div class="defile mt-3">
          <table>
            <thead><tr><th class="g">Chanson</th>
              {#if f.a_jury}<th>Notre jury</th>{/if}<th>Vrai jury</th>
              {#if f.a_jury}<th>Notre public</th>{/if}<th>Vrai public</th><th>Vrai total</th></tr></thead>
            <tbody>
              {#each [...f.chansons].sort((a, b) => (a.officiel.rang ?? 99) - (b.officiel.rang ?? 99) || a.ordre - b.ordre) as c (c.id)}
                <tr><td class="g"><Drapeau pays={c.pays} code={c.code_pays} />{c.pays}</td>
                  {#if f.a_jury}<td>{c.jury.rang}e</td>{/if}<td>{c.officiel.rang_jury ? `${c.officiel.rang_jury}e (${c.officiel.jury})` : ''}</td>
                  {#if f.a_jury}<td>{c.public.rang}e</td>{/if}<td>{c.officiel.rang_public ? `${c.officiel.rang_public}e (${c.officiel.public})` : ''}</td>
                  <td>{c.officiel.rang ? `${c.officiel.rang}e (${c.officiel.total})` : ''}</td></tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {:else}
      <p class="mb-6 text-sm text-muted-foreground print:hidden">Les vrais votes du jury et du public ne sont pas encore saisis : la comparaison apparaîtra ici.</p>
    {/if}

    <section class="bloc">
      <h2>Les notes de chacun</h2>
      <div class="defile">
        <table>
          <thead><tr><th class="g">Chanson</th>
            {#each f.invites as i (i.id)}<th>{i.prenom}{#if i.jury}<span class="sous">jury</span>{/if}</th>{/each}</tr></thead>
          <tbody>
            {#each f.chansons as c (c.id)}
              <tr><td class="g">{c.ordre}. <Drapeau pays={c.pays} code={c.code_pays} />{c.pays}</td>
                {#each f.invites as i (i.id)}
                  {@const v = c.invites[i.id]}
                  <td>{#if v}{note(v.note)}{#if v.points}<span class="pts">{v.points}</span>{/if}{/if}</td>
                {/each}</tr>
            {/each}
            <tr class="pied"><td class="g">Moyenne de ses notes</td>{#each f.invites as i (i.id)}<td>{note(i.moyenne)}</td>{/each}</tr>
          </tbody>
        </table>
      </div>
      <p class="mt-2 text-xs text-muted-foreground">La note sur 20 ; en rose, les points donnés par son classement.</p>
    </section>

    <section class="bloc">
      <h2>Les commentaires</h2>
      {#each f.chansons as c (c.id)}
        {@const dits = f.invites.filter((i) => c.invites[i.id]?.commentaire)}
        {#if dits.length}
          <h3>{c.ordre}. <Drapeau pays={c.pays} code={c.code_pays} />{c.pays}</h3>
          <ul class="mb-3 grid gap-1 text-sm">
            {#each dits as i (i.id)}<li><strong>{i.prenom}</strong> ({note(c.invites[i.id].note)}/20) : {c.invites[i.id].commentaire}</li>{/each}
          </ul>
        {/if}
      {/each}
    </section>
    {#if f.soiree.images.poster}
      <section class="bloc poster-bloc"><img class="poster" src={image('poster')} alt="Poster de l'évènement" /></section>
    {/if}
  {:else if !erreur}
    <p class="text-sm text-muted-foreground">Lecture…</p>
  {/if}
</div>

<style>
  .bloc { margin-bottom: 1.75rem; }
  .bloc h2 { margin-bottom: 0.6rem; font-size: 1.125rem; font-weight: 600; }
  .bloc h3 { margin-bottom: 0.25rem; font-weight: 500; }
  .defile { overflow-x: auto; border: 1px solid var(--border); border-radius: 0.9rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
  th, td { padding: 0.45rem 0.6rem; text-align: center; white-space: nowrap; border-bottom: 1px solid var(--border); }
  tr:last-child td { border-bottom: 0; }
  th { font-weight: 500; color: var(--muted-foreground); }
  .g { text-align: left; }
  .fort { font-size: 1.15rem; color: var(--primary); }
  .sous { display: block; font-size: 0.75rem; color: var(--muted-foreground); white-space: normal; }
  .sous-ligne { font-size: 0.75rem; color: var(--muted-foreground); }
  .pts { margin-left: 0.3rem; font-size: 0.75rem; color: var(--primary); }
  .pied td { color: var(--muted-foreground); }
  .vrai { display: grid; grid-template-columns: minmax(0, 1fr) 5.5rem 5.5rem; gap: 0.5rem; align-items: center; }
  .vrai .saisie { min-height: 2.5rem; width: 100%; }
  .lien-bouton { display: inline-flex; min-height: 2.25rem; align-items: center; border-radius: 0.6rem; border: 1px solid var(--border); padding: 0 0.9rem; font-size: 0.875rem; font-weight: 500; }

  .banniere { display: block; width: 100%; max-height: 11rem; margin-bottom: 1rem; border-radius: 0.8rem; object-fit: cover; }
  .logo { width: 4.5rem; height: 4.5rem; flex-shrink: 0; border-radius: 0.6rem; object-fit: contain; }
  .poster { display: block; max-width: 100%; max-height: 24rem; margin: 0 auto; border-radius: 0.8rem; object-fit: contain; }
  /* À l'impression : noir sur blanc, tableaux entiers, rien de la navigation */
  @media print {
    .fiche { color: #000; }
    .fiche :global(.titre) { color: #000; }
    .defile { overflow: visible; border-color: #999; }
    th, td { border-color: #bbb; white-space: normal; }
    th, .sous, .sous-ligne, .pied td { color: #444; }
    .fort, .pts { color: #b01e6b; }
    .bloc { break-inside: auto; }
    tr, li { break-inside: avoid; }
    .banniere, .logo, .poster { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
    .poster-bloc { break-before: page; }
  }
</style>
