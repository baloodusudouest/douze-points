<script>
  // Avant de démarrer : la salle est dans le noir, le « 12 » éteint. Le bouton allume les projecteurs.
  import Logo from '$lib/Logo.svelte'
  import { Button } from '$lib/components/ui/button/index.js'
  let { soiree, ondemarre, onferme, erreur = '' } = $props()
  let enCours = $state(false)

  async function demarrer() {
    enCours = true
    await ondemarre()
    enCours = false
  }
</script>

<div class="fixed inset-0 z-30 grid place-items-center bg-[#0b0a09] p-6 text-center">
  <div>
    <p class="flex justify-center" style="font-size: clamp(7rem, 38vh, 16rem); line-height: 1"><Logo eteint /></p>
    <h1 class="mt-4 text-2xl font-light tracking-tight text-muted-foreground">{soiree.nom}</h1>
    {#if erreur}<p class="mt-3 text-sm text-destructive" role="alert">{erreur}</p>{/if}
    <div class="mt-6 flex flex-col items-center gap-3">
      <Button size="lg" onclick={demarrer} disabled={enCours}>Démarrer la soirée</Button>
      <button class="text-sm text-muted-foreground underline" onclick={onferme}>Pas encore</button>
    </div>
  </div>
</div>
