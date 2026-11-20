<script>
  // L'écran d'accueil de la soirée : le « 12 », le nom de l'évènement, le QR code. Fait pour un iPhone en paysage
  // recopié sur la télé, et pour partir en image dans une conversation (avec le lien).
  import { EMISSIONS } from '$lib/pays.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Embleme from '$lib/Embleme.svelte'
  import Scene from '$lib/Scene.svelte'
  import RotateCcw from '@lucide/svelte/icons/rotate-ccw'
  import { onMount, onDestroy } from 'svelte'
  import { api } from '$lib/api.js'
  import { normaliser } from '$lib/pays.js'
  import ModeEmploi from '$lib/ModeEmploi.svelte'
  import BoutonSon from '$lib/BoutonSon.svelte'
  import * as sons from '$lib/sons.js'
  let { soiree, onferme, onrejouer } = $props()

  // 1.9 : quand tous les invités attendus ont choisi leur prénom, le mode d'emploi s'affiche (30 s par défaut,
  // Réglages › Dévoilement), une fois par soirée sur cet écran ; un bouton le remontre quand l'hôte veut (un absent
  // ne le bloque pas).
  let modeEmploi = $state(false)
  let presents = $state(0), attendus = $state(0)
  let chansons = $state([])
  let reglages = { duree_mode_emploi: 30, pas_note: 0.5 }
  let cran = $state(0.5)
  let minuterieEtat, minuteMode
  const CLE_VU = `douze-points:mode-emploi:${soiree.id}`
  function montrerMode() {
    modeEmploi = true
    clearTimeout(minuteMode)
    minuteMode = setTimeout(() => (modeEmploi = false), reglages.duree_mode_emploi * 1000)
    try { sessionStorage.setItem(CLE_VU, '1') } catch { /* rien */ }
  }
  // 1.11.0 : les sons de l'écran du QR code (lib/sons.js) : musique d'attente en boucle tant qu'il manque quelqu'un,
  // un carillon par invité qui arrive (une fois par invité et par soirée sur cette page ; ceux déjà là au chargement ne
  // sont pas salués), l'accord « tout le monde est là » une seule fois.
  let salues = null                 // ids des invités déjà là (null : pas encore lu)
  let tousLaJoue = false
  function sonsDesArrivees(gens) {
    const la = gens.filter((g) => g.pris || g.etat === 'envoye').map((g) => g.id)
    const tous = gens.length > 0 && la.length === gens.length
    if (salues === null) {
      salues = new Set(la)
      tousLaJoue = tous
    } else {
      for (const id of la) if (!salues.has(id)) { salues.add(id); sons.jouer('carillon') }
      if (tous && !tousLaJoue) { tousLaJoue = true; sons.jouer('tous_la') }
    }
    if (tous) sons.arreter('attente')
    else sons.boucle('attente')
  }
  async function surveiller() {
    try {
      const d = await api.get(`/api/soirees/${soiree.id}`)
      chansons = d.chansons.map(normaliser)
      const gens = d.participants.filter((g) => g.etat !== 'ecarte')
      attendus = gens.length
      presents = gens.filter((g) => g.pris || g.etat === 'envoye').length
      sonsDesArrivees(gens)
      let vu = false
      try { vu = !!sessionStorage.getItem(CLE_VU) } catch { /* rien */ }
      if (d.etat === 'ouverte' && attendus && presents === attendus && !vu && !modeEmploi) montrerMode()
    } catch { /* plus tard */ }
  }
  onMount(async () => {
    try { reglages = { ...reglages, ...(await api.get('/api/reglages')) }; cran = reglages.pas_note; sons.regler(reglages) } catch { /* défauts */ }
    surveiller()
    minuterieEtat = setInterval(() => { if (!document.hidden) surveiller() }, 3000)
  })
  onDestroy(() => { clearInterval(minuterieEtat); clearTimeout(minuteMode); sons.arreter('attente') })

  const qr = `/api/soirees/${soiree.id}/qr.svg`
  const image = (sorte) => (soiree.images[sorte] ? `/api/soirees/${soiree.id}/image/${sorte}?v=${soiree.images[sorte]}` : null)
  const logo = image('logo'), poster = image('poster'), apero = image('apero')     // 1.9 : la photo apéro remplace le logo

  async function charger(src) {
    const img = new Image()
    img.src = URL.createObjectURL(await (await fetch(src, { credentials: 'same-origin' })).blob())
    await img.decode()
    return img
  }
  let message = $state('')
  let champLien = $state()

  // L'affiche en image : dessinée ici, dans le navigateur (aucun outil de plus côté serveur).
  async function affiche() {
    const L = 1600, H = 900, c = Object.assign(document.createElement('canvas'), { width: L, height: H })
    const g = c.getContext('2d')
    g.fillStyle = '#151311'; g.fillRect(0, 0, L, H)
    await document.fonts.ready
    const police = getComputedStyle(document.body).fontFamily
    // Avec un poster : il occupe la gauche, sur toute la hauteur utile, et le texte se décale.
    let x = 120, largeurTexte = 820
    if (poster) {
      const p = await charger(poster), h = 740, l = Math.min(h * p.width / p.height, 520)
      g.drawImage(p, 90, 80 + (h - l * p.height / p.width) / 2, l, l * p.height / p.width)
      x = 90 + l + 60; largeurTexte = L - 620 - 60 - x
    }
    if (logo) {
      const im = await charger(logo), h = 260, l = Math.min(h * im.width / im.height, largeurTexte)
      g.drawImage(im, x, 100, l, l * im.height / im.width)
    } else {
    // le logo : le « 12 » sous un projecteur (mêmes tracés que lib/Logo.svelte, à l'échelle 3)
    g.save(); g.translate(x - 10, 70); g.scale(3, 3)
    const faisceau = g.createLinearGradient(0, -14, 0, 98)
    faisceau.addColorStop(0, 'rgba(229,85,159,0.6)'); faisceau.addColorStop(1, 'rgba(229,85,159,0.04)')
    g.fillStyle = faisceau; g.fill(new Path2D('M52 -14h16l46 112H6z'))
    g.strokeStyle = '#f2ece2'; g.lineWidth = 6; g.lineCap = 'round'; g.lineJoin = 'round'
    g.stroke(new Path2D('M28 34l15-11v60')); g.stroke(new Path2D('M62 38c0-9.5 7-16 16-16s16 6.5 16 15.5c0 7.5-4.5 12.5-12.5 20L62 82h33'))
    g.restore()
    }
    g.textBaseline = 'alphabetic'
    g.fillStyle = '#f2ece2'; g.font = `300 ${poster ? 64 : 84}px ${police}`
    lignes(g, soiree.nom, largeurTexte).forEach((l, i) => g.fillText(l, x, 500 + i * (poster ? 76 : 96)))
    g.fillStyle = '#a89e91'; g.font = `400 40px ${police}`
    g.font = `400 ${poster ? 32 : 40}px ${police}`
    g.fillText(`${soiree.concours} ${soiree.annee}, ${EMISSIONS[soiree.emission].toLowerCase()}`, x, 740)
    g.fillText(poster ? 'Wi-Fi de la maison, puis scanne.' : 'Connecte-toi au Wi-Fi de la maison, puis scanne.', x, 800)
    g.drawImage(await charger(qr), L - 620, 190, 520, 520)
    return new Promise((ok) => c.toBlob(ok, 'image/png'))
  }
  function lignes(g, texte, largeur) {
    const sortie = ['']
    for (const mot of texte.split(' ')) {
      const essai = (sortie.at(-1) + ' ' + mot).trim()
      if (g.measureText(essai).width > largeur && sortie.at(-1)) sortie.push(mot)
      else sortie[sortie.length - 1] = essai
    }
    return sortie.slice(0, 2)
  }

  async function partager() {
    message = ''
    try {
      const fichier = new File([await affiche()], 'douze-points.png', { type: 'image/png' })
      // Le partage direct n'existe qu'en HTTPS : sinon, l'image est enregistrée et le lien se copie à côté.
      if (navigator.canShare?.({ files: [fichier] })) {
        await navigator.share({ files: [fichier], text: `${soiree.nom} : ${soiree.lien}` })
      } else {
        const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(fichier), download: fichier.name })
        a.click()
        message = "Image enregistrée. Envoie-la avec le lien ci-dessous."
      }
    } catch (e) {
      if (e.name !== 'AbortError') message = "L'image n'a pas pu être fabriquée."
    }
  }

  async function copier() {
    try {
      await navigator.clipboard.writeText(soiree.lien)
      message = 'Lien copié.'
    } catch {      // en http, le presse-papiers n'est pas ouvert aux pages : on sélectionne, il reste à copier
      champLien.select()
      message = document.execCommand?.('copy') ? 'Lien copié.' : 'Lien sélectionné : copie-le.'
    }
  }
</script>

<div class="fixed inset-0 z-30 flex flex-col bg-background">
  <!-- la scène : des projecteurs qui balaient doucement le « 12 », en continu -->
  <div class="relative shrink-0" style="height: clamp(5rem, 27vh, 16rem)"><Scene />
    <!-- 1.11.0 : le haut-parleur (et « Activer le son » si le navigateur le bloque), en haut à droite -->
    <div class="absolute top-[max(0.5rem,env(safe-area-inset-top))] right-[max(0.75rem,env(safe-area-inset-right))] z-10"><BoutonSon /></div>
  </div>
<div class="grid min-h-0 flex-1 px-[max(1.25rem,env(safe-area-inset-left))] landscape:grid-rows-[minmax(0,1fr)] landscape:items-center landscape:gap-8 portrait:content-center portrait:justify-items-center portrait:gap-5 {poster ? 'landscape:grid-cols-[auto_1fr_auto]' : 'landscape:grid-cols-[1fr_auto]'}">
  {#if poster}<img src={poster} alt="Poster de l'évènement" class="rounded-xl object-contain portrait:hidden" style="max-height: 50vh; max-width: 24vw" />{/if}
  <div class="min-w-0 portrait:text-center">
    {#if apero}<img src={apero} alt="Photo apéro de la soirée" class="rounded-2xl object-cover portrait:mx-auto" style="max-height: 26vh; max-width: 40vw" />
    {:else if logo}<p style="font-size: clamp(2.5rem, 13vh, 8rem); line-height: 1" class="portrait:flex portrait:justify-center"><Embleme src={logo} /></p>{/if}
    <h1 class="mt-2 font-light tracking-tight" style="font-size: clamp(1.5rem, 6.5vh, 4rem); line-height: 1.08">{soiree.nom}</h1>
    <p class="mt-3 text-muted-foreground" style="font-size: clamp(0.95rem, 3.2vh, 1.7rem)">
      {soiree.concours} {soiree.annee}, {EMISSIONS[soiree.emission].toLowerCase()}<br />
      Connecte-toi au Wi-Fi de la maison, puis scanne.
    </p>
  </div>
  {#if soiree.lien}
    <!-- 1.10.3 : le QR code ne déborde plus sur les boutons (petit écran en paysage) : il tient dans la place qui reste -->
    <img src={qr} alt="QR code du lien des invités" class="rounded-2xl" style="height: min(50vh, 70vw); max-height: 100%; width: auto; aspect-ratio: 1" />
  {:else}
    <p class="max-w-xs rounded-2xl border p-5 text-sm">Aucune adresse pour les invités : l'Anneau ne répond pas, ou sa tuile « Douze points » n'a pas d'adresse locale. Pas de QR code ni de lien.</p>
  {/if}

</div>
  <!-- 1.10.3 : la barre des boutons a sa propre place sous la scène (elle flottait par-dessus le QR code) -->
  <div class="flex shrink-0 flex-wrap items-center justify-center gap-2 px-4 pt-2 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
    {#if soiree.lien}
      <input bind:this={champLien} readonly value={soiree.lien} aria-label="Lien des invités" class="saisie w-56 text-xs" style="min-height: 2.25rem; font-size: 0.75rem" />
      <Button variant="outline" size="sm" onclick={copier}>Copier le lien</Button>
      <!-- l'hôte note lui aussi : la même page que les invités, sur cet appareil -->
      <a class="text-xs text-muted-foreground underline" href="/invite/{soiree.jeton_invite}">Passer à la notation</a>
      <Button variant="outline" size="sm" onclick={partager}>Partager l'image</Button>
    {/if}
    <Button variant="outline" size="sm" onclick={montrerMode}>Mode d'emploi</Button>
    <!-- repartir du noir : l'écran éteint, le bouton, les projecteurs, puis de nouveau cet écran -->
    <Button variant="outline" size="sm" onclick={onrejouer} aria-label="Rejouer le démarrage" title="Rejouer le démarrage"><RotateCcw class="size-4" aria-hidden="true" /></Button>
    <Button variant="outline" size="sm" onclick={onferme}>Fermer</Button>
    {#if message}<p class="basis-full text-center text-xs text-muted-foreground" role="status">{message}</p>{/if}
  </div>
{#if modeEmploi}
  <button class="fixed inset-0 z-50 cursor-default" aria-label="Fermer le mode d'emploi" onclick={() => (modeEmploi = false)}></button>
  <ModeEmploi {chansons} {cran} {presents} {attendus} />
{/if}
</div>
