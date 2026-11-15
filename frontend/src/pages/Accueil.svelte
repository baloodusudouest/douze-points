<script>
  // L'écran d'accueil de la soirée : le « 12 », le nom de l'évènement, le QR code. Fait pour un iPhone en paysage
  // recopié sur la télé, et pour partir en image dans une conversation (avec le lien).
  import { EMISSIONS } from '$lib/pays.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Logo from '$lib/Logo.svelte'
  let { soiree, onferme } = $props()

  const qr = `/api/soirees/${soiree.id}/qr.svg`
  let message = $state('')
  let champLien = $state()

  // L'affiche en image : dessinée ici, dans le navigateur (aucun outil de plus côté serveur).
  async function image() {
    const L = 1600, H = 900, c = Object.assign(document.createElement('canvas'), { width: L, height: H })
    const g = c.getContext('2d')
    g.fillStyle = '#151311'; g.fillRect(0, 0, L, H)
    await document.fonts.ready
    const police = getComputedStyle(document.body).fontFamily
    // le logo : le « 12 » sous un projecteur (mêmes tracés que lib/Logo.svelte, à l'échelle 3)
    g.save(); g.translate(110, 70); g.scale(3, 3)
    const faisceau = g.createLinearGradient(0, -14, 0, 98)
    faisceau.addColorStop(0, 'rgba(229,85,159,0.6)'); faisceau.addColorStop(1, 'rgba(229,85,159,0.04)')
    g.fillStyle = faisceau; g.fill(new Path2D('M52 -14h16l46 112H6z'))
    g.strokeStyle = '#f2ece2'; g.lineWidth = 6; g.lineCap = 'round'; g.lineJoin = 'round'
    g.stroke(new Path2D('M28 34l15-11v60')); g.stroke(new Path2D('M62 38c0-9.5 7-16 16-16s16 6.5 16 15.5c0 7.5-4.5 12.5-12.5 20L62 82h33'))
    g.restore(); g.textBaseline = 'alphabetic'
    g.fillStyle = '#f2ece2'; g.font = `300 84px ${police}`
    lignes(g, soiree.nom, 820).forEach((l, i) => g.fillText(l, 120, 500 + i * 96))
    g.fillStyle = '#a89e91'; g.font = `400 40px ${police}`
    g.fillText(`${soiree.concours} ${soiree.annee}, ${EMISSIONS[soiree.emission].toLowerCase()}`, 120, 740)
    g.fillText('Connecte-toi au Wi-Fi de la maison, puis scanne.', 120, 800)
    const img = new Image()
    img.src = URL.createObjectURL(await (await fetch(qr, { credentials: 'same-origin' })).blob())
    await img.decode()
    g.drawImage(img, L - 620, 190, 520, 520)
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
      const fichier = new File([await image()], 'douze-points.png', { type: 'image/png' })
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

<div class="fixed inset-0 z-30 grid bg-background p-[max(1.25rem,env(safe-area-inset-top))] landscape:grid-cols-[1fr_auto] landscape:items-center landscape:gap-8 portrait:content-center portrait:justify-items-center portrait:gap-6">
  <div class="min-w-0 portrait:text-center">
    <p style="font-size: clamp(5rem, 26vh, 14rem); line-height: 1" class="portrait:flex portrait:justify-center"><Logo /></p>
    <h1 class="mt-2 font-light tracking-tight" style="font-size: clamp(1.6rem, 7vh, 4.2rem); line-height: 1.08">{soiree.nom}</h1>
    <p class="mt-3 text-muted-foreground" style="font-size: clamp(0.95rem, 3.2vh, 1.7rem)">
      {soiree.concours} {soiree.annee}, {EMISSIONS[soiree.emission].toLowerCase()}<br />
      Connecte-toi au Wi-Fi de la maison, puis scanne.
    </p>
  </div>
  {#if soiree.lien}
    <img src={qr} alt="QR code du lien des invités" class="rounded-2xl" style="width: min(70vh, 78vw); height: auto" />
  {:else}
    <p class="max-w-xs rounded-2xl border p-5 text-sm">Aucune adresse n'est réglée dans la stack (DOUZE_POINTS_ADRESSE) : pas de QR code ni de lien.</p>
  {/if}

  <div class="fixed inset-x-0 bottom-[max(0.75rem,env(safe-area-inset-bottom))] flex flex-wrap items-center justify-center gap-2 px-4">
    {#if soiree.lien}
      <input bind:this={champLien} readonly value={soiree.lien} aria-label="Lien des invités" class="saisie w-56 text-xs" style="min-height: 2.25rem; font-size: 0.75rem" />
      <Button variant="outline" size="sm" onclick={copier}>Copier le lien</Button>
      <Button variant="outline" size="sm" onclick={partager}>Partager l'image</Button>
    {/if}
    <Button variant="outline" size="sm" onclick={onferme}>Fermer</Button>
    {#if message}<p class="basis-full text-center text-xs text-muted-foreground" role="status">{message}</p>{/if}
  </div>
</div>
