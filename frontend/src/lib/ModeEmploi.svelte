<script>
  // 1.9 : le mode d'emploi sur la télé (visuel 7 du canevas, choix de Julien du 20/11/2026). Quand tout le monde est
  // là, l'écran d'accueil montre deux téléphones animés : l'écran de notation (la chanson entre ses voisines,
  // comme sur les téléphones) et l'écran de classement (une ligne glissée). Les notes suivent le pas de la soirée
  // (point, demi-point ou quart de point) ; les pays sont ceux de la soirée.
  import { onMount, onDestroy } from 'svelte'
  import { prefersReducedMotion } from 'svelte/motion'
  import { drapeau, note, BAREME } from '$lib/pays.js'
  import { notesExemple } from '$lib/dernier.js'
  let { chansons, cran = 0.5, presents = 0, attendus = 0 } = $props()

  // la chanson notée en exemple, et cinq autres déjà notées (notes au pas de la soirée)
  const liste = $derived(chansons.length >= 6 ? chansons : [...chansons, ...REPLI].slice(0, 6))
  const REPLI = [{ pays: 'France', code_pays: 'fr', titre: 'Chanson' }, { pays: 'Suède', code_pays: 'se', titre: 'Chanson' },
    { pays: 'Italie', code_pays: 'it', titre: 'Chanson' }, { pays: 'Espagne', code_pays: 'es', titre: 'Chanson' },
    { pays: 'Grèce', code_pays: 'gr', titre: 'Chanson' }, { pays: 'Malte', code_pays: 'mt', titre: 'Chanson' }]
  const arrondi = (n) => Math.round(n / cran) * cran
  const notees = $derived(liste.slice(0, 5).map((c, i) => ({ c, note: arrondi([18.5, 17, 15, 13, 12][i]) })))
  const exemple = $derived(liste[5])
  const suite = $derived(notesExemple(cran))
  let k = $state(0)
  let minuterie
  onMount(() => { if (!prefersReducedMotion.current) minuterie = setInterval(() => k++, 1600) })
  onDestroy(() => clearInterval(minuterie))
  const v = $derived(suite[k % suite.length])
  const dessus = $derived(notees.filter((x) => x.note > v).sort((a, b) => a.note - b.note)[0] ?? null)
  const dessous = $derived(notees.filter((x) => x.note < v).sort((a, b) => b.note - a.note)[0] ?? null)
  const rang = $derived(1 + notees.filter((x) => x.note > v).length)
  // le classement : la chanson exemple remonte de la 3e à la 1re place, puis redescend
  const classement = $derived.by(() => {
    const base = [...notees.slice(0, 2).map((x) => x.c), exemple, ...notees.slice(2).map((x) => x.c), ...liste.slice(6, 11)]
    const ordre = [...base]
    const place = [2, 1, 0, 0, 1][k % 5]
    ordre.splice(2, 1)
    ordre.splice(place, 0, exemple)
    return base.map((c) => ({ c, i: ordre.indexOf(c), tenue: c === exemple }))
  })
</script>

<div class="mode" role="region" aria-label="Mode d'emploi">
  <div class="tete">
    <h1>{attendus && presents >= attendus ? 'Tout le monde est là' : 'Comment noter'}</h1>
    <p>{presents} invité{presents > 1 ? 's' : ''}{attendus ? ` sur ${attendus}` : ''} arrivé{presents > 1 ? 's' : ''} · voici comment noter</p>
  </div>
  <div class="milieu">
    <div class="explication droite-texte">
      <p class="num">1</p><p class="titre">Note chaque chanson sur 20</p>
      <p class="aide">Pendant que tu fais glisser la note, tu vois juste au-dessus et juste en dessous les chansons que tu as déjà notées.</p>
    </div>
    <div class="tel" aria-label="Exemple d'écran de notation">
      <p class="petit">Chanson {exemple.ordre ?? 6} sur {chansons.length || 15}</p>
      <p class="pays">{drapeau(exemple.pays, exemple.code_pays)} {exemple.pays}</p>
      <div class="pile">
        <p class="reste">{dessus ? 'Juste au-dessus' : 'Ta meilleure note pour l\'instant'}</p>
        {#if dessus}<div class="voisine"><span>{drapeau(dessus.c.pays, dessus.c.code_pays)}</span><span class="nom">{dessus.c.pays}</span><span class="n">{note(dessus.note)}</span></div>{/if}
        <div class="carte"><span>{drapeau(exemple.pays, exemple.code_pays)}</span><span class="nom">{exemple.pays}<small>{rang === 1 ? '1re' : rang + 'e'} de tes {notees.length + 1} chansons</small></span><span class="grand">{note(v)}</span></div>
        {#if dessous}<div class="voisine"><span>{drapeau(dessous.c.pays, dessous.c.code_pays)}</span><span class="nom">{dessous.c.pays}</span><span class="n">{note(dessous.note)}</span></div>{/if}
        <p class="reste">{dessous ? 'Juste en dessous' : 'Ta plus petite note pour l\'instant'}</p>
      </div>
      <div class="curseur"><i style="width: {v * 5}%"></i><b style="left: {v * 5}%"></b></div>
    </div>
    <div class="tel" aria-label="Exemple d'écran de classement">
      <p class="petit">Rangé d'après tes notes. Glisse une ligne par sa poignée.</p>
      <ol class="rangs" style="height: {classement.length * 1.9}em">
        {#each classement as l (l.c.pays + l.i)}
          <li class:tenue={l.tenue} style="top: {l.i * 1.9}em"><span class="pts">{l.i < 10 ? BAREME[l.i] : '·'}</span><span class="nom">{drapeau(l.c.pays, l.c.code_pays)} {l.c.pays}</span></li>
        {/each}
      </ol>
      <span class="bouton">Envoyer mon classement</span>
    </div>
    <div class="explication">
      <p class="num">2</p><p class="titre">Range tes chansons</p>
      <p class="aide">Tes dix premières reçoivent 12, 10, 8, 7… jusqu'à 1 point. C'est ce classement qui compte. Puis envoie-le.</p>
    </div>
  </div>
  <p class="pied">Le dévoilement commence quand tout le monde a envoyé son classement.</p>
</div>

<style>
  .mode { position: fixed; inset: 0; z-index: 40; display: flex; flex-direction: column; background: var(--background); padding: 3vh 4vw; }
  .tete h1 { font-size: clamp(1.5rem, 5.5vh, 3rem); font-weight: 300; }
  .tete p { color: var(--muted-foreground); font-size: clamp(0.9rem, 2.8vh, 1.4rem); }
  .milieu { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) auto auto minmax(0, 1fr); gap: 3vw; align-items: center; }
  .explication .num { font-size: clamp(2rem, 6vh, 3.4rem); font-weight: 600; color: var(--primary); line-height: 1; }
  .explication .titre { margin-top: 0.5rem; font-size: clamp(1.1rem, 3.6vh, 2rem); font-weight: 300; }
  .explication .aide { margin-top: 0.6rem; font-size: clamp(0.85rem, 2.4vh, 1.25rem); line-height: 1.45; color: var(--muted-foreground); }
  .droite-texte { text-align: right; }
  /* 1.10.3 : le téléphone est dessiné à l'échelle. Tout ce qu'il contient est en em, et sa taille de texte suit sa
     largeur (24 em de large) : sur un petit écran en paysage, il rapetisse en entier au lieu de couper les textes. */
  .tel { --l: min(36vh, 22vw); width: var(--l); height: min(74vh, 46vw); font-size: calc(var(--l) / 24); box-sizing: border-box; border-radius: 2.4em;
    border: 0.38em solid #2f2a26; padding: 1.4em 0.8em 1em; display: flex; flex-direction: column; box-shadow: 0 1.2em 4em rgba(0, 0, 0, 0.55); overflow: hidden; }
  .petit { font-size: 0.7em; color: var(--muted-foreground); }
  .pays { font-size: 1.25em; font-weight: 300; }
  .pile { margin: auto 0; display: grid; gap: 0.35em; }
  .reste { text-align: center; font-size: 0.65em; color: #8b8276; }
  .voisine, .carte { display: flex; align-items: center; gap: 0.45em; border-radius: 0.6em; padding: 0.35em 0.6em; background: var(--card); border: 1px solid var(--border); font-size: 0.8em; }
  .voisine .nom, .carte .nom { flex: 1; min-width: 0; display: flex; flex-direction: column; font-weight: 600; }
  .carte { background: color-mix(in oklab, var(--primary) 22%, var(--background)); border: 2px solid var(--primary); padding: 0.55em 0.7em; }
  .carte small { font-size: 0.75em; font-weight: 400; color: color-mix(in oklab, var(--primary) 50%, white); }
  .carte .grand { font-size: 2.4em; font-weight: 600; line-height: 1; font-variant-numeric: tabular-nums; transition: opacity 0.2s; }
  .n { font-weight: 600; font-variant-numeric: tabular-nums; }
  .curseur { position: relative; height: 0.38em; border-radius: 0.19em; background: var(--muted); margin: 0.8em 0.4em 0.4em; }
  .curseur i { position: absolute; inset: 0 auto 0 0; border-radius: 0.19em; background: var(--primary); transition: width 0.4s; }
  .curseur b { position: absolute; top: 50%; width: 1em; height: 1em; margin-left: -0.5em; transform: translateY(-50%); border-radius: 999px; background: var(--foreground); border: 2px solid var(--primary); transition: left 0.4s; }
  .rangs { position: relative; margin-top: 0.5em; flex-shrink: 0; }
  .rangs li { position: absolute; left: 0; right: 0; height: 1.7em; display: flex; align-items: center; gap: 0.5em; padding: 0 0.5em; border-radius: 0.45em;
    background: var(--card); font-size: 1em; transition: top 0.6s cubic-bezier(0.3, 0.7, 0.3, 1); }
  .rangs li.tenue { z-index: 1; background: color-mix(in oklab, var(--primary) 22%, var(--background)); box-shadow: 0 0.3em 1em rgba(0, 0, 0, 0.5), inset 0 0 0 2px var(--primary); }
  .rangs .pts { width: 1.4em; text-align: right; font-weight: 600; color: var(--primary); font-variant-numeric: tabular-nums; }
  .rangs .nom { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bouton { margin-top: auto; flex-shrink: 0; display: grid; min-height: 2.6em; place-items: center; border-radius: 0.6em; background: var(--primary); color: var(--primary-foreground); font-size: 0.85em; font-weight: 600; }
  .pied { text-align: center; color: var(--muted-foreground); font-size: clamp(0.85rem, 2.4vh, 1.2rem); }
  @media (orientation: portrait) { .milieu { grid-template-columns: 1fr 1fr; } .explication { display: none; } .tel { --l: 44vw; height: 60vh; } }
  @media (prefers-reduced-motion: reduce) { .rangs li, .curseur i, .curseur b { transition: none; } }
</style>
