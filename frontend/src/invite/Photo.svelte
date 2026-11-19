<script>
  // 1.6 : envoyer des photos de la soirée depuis le téléphone d'un invité. Elles partent dans l'album Immich de la
  // soirée (chez l'hôte) ; l'invité ne voit jamais celles des autres.
  // - icône de la soirée : sans `capture`, iOS propose « Photothèque » ou « Prendre une photo », plusieurs à la fois,
  //   et la Pellicule garde une copie (rien de perdu si le Wi-Fi lâche) ;
  // - « Immortaliser » un duo : `capture="user"`, l'appareil photo s'ouvre en selfie.
  // Envoi par XMLHttpRequest, une photo après l'autre : seul XHR donne l'avancement de l'envoi (fetch ne le donne pas).
  import Camera from '@lucide/svelte/icons/camera'
  let { jeton, tel, duo = null, selfie = false, libelle = '', classe = '', onenvoye = () => {} } = $props()

  let champ
  let file = $state([])            // photos choisies, pas encore envoyées
  let avance = $state(0)           // 0 à 1, pour la photo en cours
  let message = $state('')
  let erreur = $state('')
  let enCours = $derived(file.length > 0)
  let total = 0, faites = 0

  function choisir() { erreur = ''; message = ''; champ.value = ''; champ.click() }

  function choisies(ev) {
    const photos = [...(ev.currentTarget.files || [])]
    if (!photos.length) return
    total = photos.length; faites = 0
    file = photos
    suivante()
  }

  function suivante() {
    if (!file.length) return
    const photo = file[0]
    avance = 0
    const x = new XMLHttpRequest()
    x.open('PUT', `/invite/${jeton}/api/photo`)
    x.setRequestHeader('Content-Type', 'application/octet-stream')
    if (tel) x.setRequestHeader('X-Telephone', tel)
    if (duo) x.setRequestHeader('X-Duo', String(duo))
    x.upload.onprogress = (e) => { if (e.lengthComputable) avance = e.loaded / e.total }
    x.onload = () => {
      let d = {}
      try { d = JSON.parse(x.responseText || '{}') } catch { /* sans contenu */ }
      if (x.status >= 200 && x.status < 300) {
        faites++
        onenvoye(d.photos)
        file = file.slice(1)
        if (!file.length) {
          message = (total > 1 ? `${faites} photos envoyées` : 'Photo envoyée') +
            (d.photos?.soiree ? ` · ${d.photos.soiree} photo${d.photos.soiree > 1 ? 's' : ''} ce soir` : '')
          setTimeout(() => (message = ''), 4000)
        } else suivante()
      } else {
        erreur = d.detail || `Photo refusée (${x.status}).`
        file = []
      }
    }
    x.onerror = () => { erreur = "La photo n'est pas partie : es-tu sur le Wi-Fi de la maison ? Elle reste dans ta Pellicule."; file = [] }
    x.send(photo)
  }
</script>

<input bind:this={champ} type="file" accept="image/*" class="hidden" multiple={!selfie}
       capture={selfie ? 'user' : undefined} onchange={choisies} aria-hidden="true" tabindex="-1" />

{#if libelle}
  <button class={classe} onclick={choisir} disabled={enCours}>
    {enCours ? `Envoi… ${Math.round(avance * 100)} %` : libelle}
  </button>
{:else}
  <button class="icone" onclick={choisir} disabled={enCours} aria-label="Ajouter des photos de la soirée">
    {#if enCours}
      <svg viewBox="0 0 36 36" class="size-7" aria-hidden="true"><circle cx="18" cy="18" r="15" fill="none" stroke="var(--border)" stroke-width="3" />
        <circle cx="18" cy="18" r="15" fill="none" stroke="var(--primary)" stroke-width="3" stroke-linecap="round"
                stroke-dasharray={`${avance * 94.2} 94.2`} transform="rotate(-90 18 18)" /></svg>
    {:else}<Camera class="size-6" />{/if}
  </button>
{/if}

{#if message || erreur}
  <p class="avis {erreur ? 'border-destructive/60' : 'border-primary/60'}" role={erreur ? 'alert' : 'status'}>{erreur || message}</p>
{/if}

<style>
  .icone { display: grid; width: 2.75rem; height: 2.75rem; flex-shrink: 0; place-items: center; border-radius: 999px;
    border: 1px solid var(--border); background: var(--card); color: var(--foreground); }
  .icone:active { transform: translateY(1px); }
  .avis { position: fixed; left: 1rem; right: 1rem; top: calc(0.75rem + env(safe-area-inset-top)); z-index: 40; margin: 0 auto;
    max-width: 30rem; border-radius: 1rem; border-width: 1px; background: var(--card); padding: 0.75rem 1rem; font-size: 0.9rem;
    box-shadow: 0 8px 24px rgb(0 0 0 / 0.45); }
</style>
