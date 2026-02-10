# 🎨 Temi AInaudi - Campagna Referendum 2026

## Tema "VOTA NO" - Referendum Giustizia 2026

Questo tema allinea l'interfaccia dell'app AInaudi con la comunicazione visiva della campagna **"VOTA NO AL REFERENDUM SALVA-CASTA"**.

### 📋 Palette Colori

| Colore | Hex | Uso |
|--------|-----|-----|
| **Navy Profondo** | `#1e3a5f` | Sfondo principale, header |
| **Navy Chiaro** | `#264a6e` | Sfondo secondario, gradienti |
| **Rosso Acceso** | `#dc143c` | CTA, bottoni primari, accenti |
| **Rosso Scuro** | `#b01030` | Hover states, enfasi |
| **Bianco** | `#ffffff` | Testo su sfondo navy, cards |

### 🎯 Caratteristiche Stilistiche

**Design System:**
- ✅ Sfondo navy con pattern a puntini (come materiale campagna)
- ✅ Cards bianche con bordi arrotondati generosi (1rem - 1.5rem)
- ✅ Bottoni rossi accesi con gradiente
- ✅ Tipografia bold e maiuscola per header
- ✅ Contrasto elevato per leggibilità
- ✅ Accenti rossi su elementi interattivi

**Componenti Stilizzati:**
- Navbar con sfondo navy e bordo rosso
- Cards con bordi arrotondati e ombra profonda
- Bottoni primari rosso acceso con effetto hover
- Headers con gradiente navy e barra laterale rossa
- Scrollbar personalizzata (navy con thumb rosso)
- Alerts e badges coordinati

### 🚀 Come Usare il Tema

#### Attivazione Automatica

Il tema può essere attivato tramite il **Theme Switcher** presente nell'interfaccia:
- Bottone fisso in basso a destra
- Toggle tra "Tema Standard" e "Tema VOTA NO"
- Salva la preferenza in localStorage

#### Attivazione Programmatica

```javascript
// Attiva il tema VOTA NO
document.documentElement.setAttribute('data-theme', 'referendum-no');

// Torna al tema standard
document.documentElement.removeAttribute('data-theme');

// Salva la preferenza
localStorage.setItem('app-theme', 'referendum-no');
```

### 📁 File del Tema

```
src/themes/
├── referendum-no-theme.css     # Stili del tema
└── README.md                    # Questa documentazione

src/components/
└── ThemeSwitcher.js            # Componente toggle tema
```

### 🔧 Personalizzazione

Il tema usa CSS Variables per facilitare personalizzazioni:

```css
[data-theme="referendum-no"] {
  /* Modifica questi valori per personalizzare */
  --color-campaign-navy: #1e3a5f;
  --color-campaign-red: #dc143c;
  --radius-lg: 1.5rem;
}
```

### 📱 Responsive

Il tema è completamente responsive:
- Mobile: Bordi arrotondati ridotti, padding ottimizzato
- Tablet: Layout adattivo
- Desktop: Full experience con pattern e ombre

### ♿ Accessibilità

- ✅ Contrasto WCAG AAA (Navy + Bianco)
- ✅ Contrasto WCAG AA (Rosso + Bianco)
- ✅ Focus states chiari (rosso)
- ✅ Touch target 44px
- ✅ Leggibilità ottimizzata

### 🖨️ Stampa

Il tema include regole di stampa ottimizzate:
- Background bianco per stampa
- Testo nero
- Bordi navy per cards

### 🔍 Confronto con Tema Standard

| Aspetto | Standard | VOTA NO |
|---------|----------|---------|
| **Sfondo** | Grigio chiaro | Navy con pattern |
| **Primary** | Blu Bootstrap | Rosso acceso |
| **Cards** | Bianche subtle | Bianche con ombra forte |
| **Navbar** | Scura Bootstrap | Navy con accento rosso |
| **Radius** | 0.5rem | 1-1.5rem |
| **Stile** | Corporate pulito | Campagna impattante |

### 📊 Metriche di Utilizzo

Il tema traccia automaticamente la preferenza in localStorage:
- Key: `app-theme`
- Values: `'standard'` | `'referendum-no'`

### 🎨 Brand Guidelines Compliance

Il tema rispetta le linee guida della campagna "VOTA NO":
- ✅ Colori ufficiali (Navy #1e3a5f, Rosso #dc143c)
- ✅ Pattern decorativo a puntini
- ✅ Tipografia bold/maiuscola
- ✅ Forme arrotondate
- ✅ Contrasto forte

### 🔄 Compatibilità

- ✅ React 18+
- ✅ Bootstrap 5
- ✅ Browser moderni (Chrome, Firefox, Safari, Edge)
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

### 📝 Note per Sviluppatori

**Quando aggiungere stili al tema:**
1. Nuovi componenti → Aggiungi regole in `referendum-no-theme.css`
2. Usa sempre le CSS variables del tema
3. Testa il contrasto con sfondo navy
4. Verifica responsive su mobile

**Testing Checklist:**
- [ ] Navbar leggibile
- [ ] Cards bianche su navy
- [ ] Bottoni rossi visibili
- [ ] Forms funzionanti
- [ ] Modal leggibili
- [ ] Responsive mobile

### 🐛 Troubleshooting

**Il tema non si applica:**
- Verifica che `referendum-no-theme.css` sia importato in `index.jsx`
- Controlla che `data-theme="referendum-no"` sia presente su `<html>`

**Contrasto basso:**
- Usa sempre `--text-primary` per testo su navy
- Usa sempre `--surface-card` per background cards

**Pattern non visibile:**
- Verifica che non ci siano background inline che lo sovrascrivono

---

**Creato per:** Referendum Costituzionale Giustizia 2026
**Campagna:** VOTA NO AL SALVA-CASTA
**Versione:** 1.0.0
**Data:** Febbraio 2026
