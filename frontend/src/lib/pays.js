// Le drapeau d'un pays à partir de son nom en français (émoji : deux lettres « indicateur régional »).
// Un pays absent de la table n'a pas de drapeau, c'est tout : rien n'est inventé.
const CODES = {
  albanie: 'AL', allemagne: 'DE', andorre: 'AD', armenie: 'AM', australie: 'AU', autriche: 'AT', azerbaidjan: 'AZ',
  belgique: 'BE', bielorussie: 'BY', 'bosnie-herzegovine': 'BA', bulgarie: 'BG', chypre: 'CY', croatie: 'HR',
  danemark: 'DK', espagne: 'ES', estonie: 'EE', finlande: 'FI', france: 'FR', georgie: 'GE', grece: 'GR',
  hongrie: 'HU', irlande: 'IE', islande: 'IS', israel: 'IL', italie: 'IT', kazakhstan: 'KZ', kosovo: 'XK',
  lettonie: 'LV', lituanie: 'LT', luxembourg: 'LU', 'macedoine du nord': 'MK', malte: 'MT', maroc: 'MA',
  moldavie: 'MD', monaco: 'MC', montenegro: 'ME', norvege: 'NO', 'pays-bas': 'NL', pologne: 'PL', portugal: 'PT',
  roumanie: 'RO', 'royaume-uni': 'GB', russie: 'RU', 'saint-marin': 'SM', serbie: 'RS', slovaquie: 'SK',
  slovenie: 'SI', suede: 'SE', suisse: 'CH', tchequie: 'CZ', 'republique tcheque': 'CZ', turquie: 'TR', ukraine: 'UA',
  bangladesh: 'BD', bhoutan: 'BT', cambodge: 'KH', chine: 'CN', 'coree du sud': 'KR', inde: 'IN', indonesie: 'ID',
  japon: 'JP', laos: 'LA', malaisie: 'MY', mongolie: 'MN', nepal: 'NP', philippines: 'PH', singapour: 'SG',
  'sri lanka': 'LK', thailande: 'TH', vietnam: 'VN', 'viet nam': 'VN',
}

const cle = (nom) => (nom || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/['’]/g, ' ').trim()

export function drapeau(pays, code) {
  const c = (code || CODES[cle(pays)] || '').toUpperCase()
  if (!/^[A-Z]{2}$/.test(c)) return ''
  return String.fromCodePoint(...[...c].map((l) => 0x1f1e6 + l.charCodeAt(0) - 65))
}

export const EMISSIONS = { demi1: 'Première demi-finale', demi2: 'Seconde demi-finale', finale: 'Finale', unique: 'Soirée unique' }
export const BAREME = [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]
// 13.5 → « 13,5 » ; 12 → « 12 »
export const note = (v) => (v == null ? '' : String(v).replace('.', ','))

// Le titre fabriqué d'une soirée : « Eurovision Burgas 2027, finale ». Même règle que titre_evenement (app/main.py).
const LIBELLES = { demi1: 'première demi-finale', demi2: 'seconde demi-finale', finale: 'finale', unique: '' }
export function titreEvenement({ concours, annee, emission, ville }) {
  const debut = [concours, (ville || '').trim(), annee].filter(Boolean).join(' ')
  return LIBELLES[emission] ? `${debut}, ${LIBELLES[emission]}` : debut
}
