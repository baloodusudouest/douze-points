<script>
  // « Réglages » : ce qui n'est pas un service. Toujours en bas : la version et la déconnexion.
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  let { session, deconnecter } = $props()

  let concours = $state([])
  let invites = $state([])
  let nom = $state('')
  let erreur = $state('')

  async function lire() {
    concours = (await api.get('/api/concours')).filter((c) => c.actif)
    invites = (await api.get('/api/invites')).filter((i) => i.actif)
  }
  async function regler(invite, corps) {
    erreur = ''
    try { await api.put('/api/invites/' + invite.id, corps); await lire() } catch (x) { erreur = x.message }
  }
  onMount(() => lire().catch((e) => (erreur = e.message)))

  async function ajouter(e) {
    e.preventDefault()
    erreur = ''
    try { await api.post('/api/concours', { nom }); nom = ''; await lire() } catch (x) { erreur = x.message }
  }
  async function retirer(c) {
    erreur = ''
    try {
      const r = await fetch('/api/concours/' + c.id, { method: 'DELETE', credentials: 'same-origin' })
      if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail || 'Le concours n\'a pas pu être retiré.')
      await lire()
    } catch (x) { erreur = x.message }
  }
</script>

<header class="mb-5">
  <h1 class="titre">Réglages</h1>
</header>

<section class="rounded-2xl border bg-card p-5">
  <h2 class="text-lg font-semibold">Concours</h2>
  <p class="mt-1 text-sm text-muted-foreground">La liste proposée quand tu crées une soirée. Retirer un concours ne touche pas aux soirées déjà faites.</p>
  {#if erreur}<p class="mt-2 text-sm text-destructive" role="alert">{erreur}</p>{/if}
  <ul class="mt-3 grid gap-2" aria-label="Concours">
    {#each concours as c (c.id)}
      <li class="flex items-center gap-3 rounded-xl border px-3 py-2">
        <span class="font-medium">{c.nom}</span>
        <span class="mr-auto text-sm text-muted-foreground">{c.soirees ? `${c.soirees} soirée${c.soirees > 1 ? 's' : ''}` : ''}</span>
        <Button variant="outline" size="sm" onclick={() => retirer(c)} aria-label="Retirer {c.nom}" disabled={concours.length === 1}>Retirer</Button>
      </li>
    {/each}
  </ul>
  <form class="mt-4 flex gap-2" onsubmit={ajouter}>
    <input class="saisie flex-1" bind:value={nom} placeholder="Nom du concours" maxlength="60" aria-label="Nom d'un nouveau concours" required />
    <Button type="submit">Ajouter</Button>
  </form>
</section>

<section class="mt-4 rounded-2xl border bg-card p-5">
  <h2 class="text-lg font-semibold">Invités : jury ou public</h2>
  <p class="mt-1 text-sm text-muted-foreground">Coche les membres du jury ; les autres sont le public. Au dévoilement « jury puis public », les points du jury arrivent d'abord, chanson par chanson, puis ceux du public en partant du bas du classement. Tous les points comptent pareil.</p>
  {#if invites.length}
    <ul class="mt-3 grid gap-2 sm:grid-cols-2" aria-label="Invités">
      {#each invites as i (i.id)}
        <li class="flex items-center gap-2 rounded-xl border px-3 py-2">
          <span class="mr-auto font-medium">{i.prenom}</span>
          <button class="pastille" aria-pressed={i.jury} aria-label="{i.prenom} : jury" onclick={() => regler(i, { jury: true })}>Jury</button>
          <button class="pastille" aria-pressed={!i.jury} aria-label="{i.prenom} : public" onclick={() => regler(i, { jury: false })}>Public</button>
          <Button variant="outline" size="sm" onclick={() => regler(i, { actif: false })} aria-label="Retirer {i.prenom} de la liste">Retirer</Button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="mt-3 text-sm text-muted-foreground">Aucun invité pour l'instant : ils s'ajoutent en préparant une soirée.</p>
  {/if}
</section>

<section class="mt-4 rounded-2xl border bg-card p-5">
  <h2 class="text-lg font-semibold">Adresse donnée aux invités</h2>
  <p class="mt-1 text-sm text-muted-foreground">
    {#if session.adresse}
      Le QR code et le lien mènent à <span class="text-foreground">{session.adresse}</span>. Ils ne répondent que sur le Wi-Fi de la maison.
    {:else}
      Aucune adresse n'est réglée : sans elle, pas de QR code ni de lien. À renseigner dans la stack (DOUZE_POINTS_ADRESSE).
    {/if}
  </p>
</section>

<p class="mt-6 flex items-center justify-between gap-3 text-sm text-muted-foreground">
  <span>Douze points {session.version}</span>
  <Button variant="outline" onclick={deconnecter}>Se déconnecter</Button>
</p>
