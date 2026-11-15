<script>
  // « Réglages » : ce qui n'est pas un service. Toujours en bas : la version et la déconnexion.
  import { Button } from '$lib/components/ui/button/index.js'
  let { session, deconnecter } = $props()
</script>

<header class="mb-5">
  <p class="etiquette">Douze points</p>
  <h1 class="titre">Réglages</h1>
</header>

<section class="rounded-2xl border bg-card p-5">
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
