/**
 * Zeigt, ob das Produkt zum gespeicherten Fahrzeug passt.
 * Liest den Eintrag, den assets/vehicle-selector.js unter "displayfolien:fahrzeug" speichert.
 */
const STORAGE_KEY = 'displayfolien:fahrzeug';

class ProductFitBadge extends HTMLElement {
  connectedCallback() {
    /** @type {{ display?: string, label?: string } | null} */
    let saved = null;
    try {
      saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null');
    } catch {
      saved = null;
    }
    if (!saved?.display) return;

    const displays = (this.dataset.displays ?? '').split(',').filter(Boolean);
    const fits = displays.includes(saved.display);
    const vehicle = saved.label ?? '';

    const text = this.querySelector('.product-fit-badge__text');
    const link = this.querySelector('.product-fit-badge__link');
    if (!text || !(link instanceof HTMLAnchorElement)) return;

    const template = (fits ? this.dataset.textYes : this.dataset.textNo) ?? '';
    // Ältere Einträge ohne Label: "([vehicle])" einfach weglassen
    text.textContent = (vehicle ? template.replace('[vehicle]', vehicle) : template.replace(/\s*\(\[vehicle\]\)/, '')).trim();
    link.textContent = this.dataset.linkText ?? '';
    link.href = this.dataset.linkUrl ?? '/';

    this.classList.add(fits ? 'product-fit-badge--yes' : 'product-fit-badge--no');
    this.hidden = false;
  }
}

if (!customElements.get('product-fit-badge')) {
  customElements.define('product-fit-badge', ProductFitBadge);
}
