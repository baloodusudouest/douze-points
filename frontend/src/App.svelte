<script>
  // Régie de Douze points. Navigation commune aux applis maison : rail à gauche sur PC,
  // barre d'icônes collée en bas sur iPhone. Les écrans des invités sont dans src/invite (voir main.js).
  import { onMount } from 'svelte'
  import { fly } from 'svelte/transition'
  import Mic from '@lucide/svelte/icons/mic-vocal'
  import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal'
  import Plug from '@lucide/svelte/icons/plug'
  import Inbox from '@lucide/svelte/icons/inbox'
  import { api } from '$lib/api.js'
  import Ouverture from '$lib/Ouverture.svelte'
  import Connexion from './pages/Connexion.svelte'
  import Soiree from './pages/Soiree.svelte'
  import Reglages from './pages/Reglages.svelte'
  import Services from '$lib/services/Services.svelte'   // 1.10.0 : écran commun (contrat 3, socle 0.10.0)
  import ATraiter from './pages/ATraiter.svelte'
  import { installer as installerSons } from '$lib/sons.js'

  const onglets = [
    { page: 'soiree', nom: 'Soirée', icone: Mic },
    { page: 'a-traiter', nom: 'À traiter', icone: Inbox },          // 1.9 : vrais votes et clôture
    { page: 'connexion', nom: 'Connexion', icone: Plug },
    { page: 'reglages', nom: 'Réglages', icone: SlidersHorizontal },
  ]

  let connecte = $state(null) // null : on ne sait pas encore
  let session = $state({ version: '' })
  let page = $state(lirePage())

  function lirePage() {
    const p = location.hash.replace('#/', '').split('/')[0]      // 1.5 : « #/soiree/<id> » ouvre cette soirée
    return onglets.some((o) => o.page === p) ? p : 'soiree'
  }

  async function verifier() {
    try {
      const s = await api.get('/api/session')
      session = s
      connecte = s.connecte
    } catch {
      connecte = false
    }
  }

  async function deconnecter() {
    try { await api.post('/api/deconnexion') } catch { /* déjà déconnecté */ }
    connecte = false
  }

  // 1.9 : le nombre de soirées à clôturer, sur l'entrée « À traiter »
  let aTraiter = $state(0)
  async function compter() { try { aTraiter = (await api.get('/api/a-traiter')).nombre } catch { /* plus tard */ } }
  // 1.11.0 : les sons de la télé (lib/sons.js) : le contexte audio naît au premier geste sur la régie (jamais sur la
  // page des invités, qui n'importe pas sons.js)
  onMount(async () => { installerSons(); await verifier(); if (connecte) compter() })
</script>

<Ouverture />

<svelte:window onhashchange={() => (page = lirePage())} />

{#if connecte === false}
  <Connexion onconnecte={verifier} />
{:else if connecte}
  <div class="md:pl-52 print:pl-0">
    <!-- iPhone : barre d'onglets collée au bord bas (22/11/2026), icônes seules (le nom de la section est le titre de l'écran).
         PC : rail à gauche, avec les noms. Mêmes entrées, même ordre. -->
    <nav
      aria-label="Sections"
      class="print:hidden fixed inset-x-0 bottom-0 z-20 flex items-center justify-around gap-1 border-t bg-card/95 px-2 pt-1.5 pb-[calc(0.375rem+env(safe-area-inset-bottom))] backdrop-blur-md
             md:inset-y-0 md:left-0 md:right-auto md:justify-start md:w-52 md:translate-x-0 md:flex-col md:items-stretch md:gap-1 md:rounded-none md:border-0 md:border-r md:bg-transparent md:p-4 md:shadow-none md:backdrop-blur-none"
    >
      <span class="mb-4 hidden px-2 text-xl font-light tracking-tight md:block">Douze points</span>
      {#each onglets as o}
        {@const Icone = o.icone}
        <a
          href={'#/' + o.page}
          aria-label={o.nom}
          aria-current={page === o.page ? 'page' : undefined}
          class="flex h-11 items-center gap-2 rounded-full px-4 text-sm font-medium text-muted-foreground transition-colors
                 hover:text-foreground aria-[current=page]:bg-foreground aria-[current=page]:text-background
                 md:h-10 md:rounded-lg md:px-3 md:aria-[current=page]:bg-secondary md:aria-[current=page]:text-foreground"
        >
          <span class="relative inline-flex"><Icone class="size-[1.15rem]" aria-hidden="true" />
            {#if o.page === 'a-traiter' && aTraiter}<span class="pastille-nombre" aria-hidden="true">{aTraiter}</span>{/if}</span>
          <span class="sr-only md:not-sr-only">{o.nom}{#if o.page === 'a-traiter' && aTraiter}<span class="sr-only"> : {aTraiter} soirée{aTraiter > 1 ? 's' : ''} à clôturer</span>{/if}</span>
        </a>
      {/each}
    </nav>

    <main
      class="mx-auto max-w-5xl px-[max(1rem,env(safe-area-inset-left))] pt-[calc(1.25rem+env(safe-area-inset-top))] pb-[calc(6rem+env(safe-area-inset-bottom))] md:px-8 md:pt-8 md:pb-10"
    >
      {#key page}
        <div in:fly={{ y: 6, duration: 180 }}>
          {#if page === 'a-traiter'}
            <ATraiter onnombre={(n) => (aTraiter = n)} />
          {:else if page === 'reglages'}
            <Reglages {session} {deconnecter} />
          {:else if page === 'connexion'}
            <Services ondeconnecte={() => (connecte = false)} />
          {:else}
            <Soiree ondeconnecte={() => (connecte = false)} />
          {/if}
        </div>
      {/key}
    </main>
  </div>
{/if}

<style>
  /* 1.9 : le nombre de soirées à clôturer sur l'entrée « À traiter » */
  .pastille-nombre { position: absolute; top: -0.45rem; right: -0.65rem; display: grid; min-width: 1.05rem; height: 1.05rem;
    place-items: center; border-radius: 999px; background: var(--primary); color: var(--primary-foreground);
    font-size: 0.65rem; font-weight: 700; padding: 0 0.2rem; }
</style>
