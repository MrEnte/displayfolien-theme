import { Component } from '@theme/component';

const STORAGE_KEY = 'displayfolien:fahrzeug';

/**
 * @typedef {Object} VehicleDisplay
 * @property {string} id
 * @property {string} name
 * @property {string} hint
 * @property {string | null} image
 * @property {string | null} imageAlt
 * @property {string | null} productUrl
 * @property {{ id: string, name: string, from: number, to: number | null }} series
 * @property {{ id: string, name: string }} model
 * @property {{ id: string, name: string }} brand
 */

/**
 * @typedef {Object} SavedVehicle
 * @property {string} brand
 * @property {string} model
 * @property {string} year
 * @property {string} display
 * @property {string} [label] - Lesbarer Name, z. B. "VW Golf (2021)" – für assets/product-fit-badge.js
 */

/**
 * @typedef {Object} Refs
 * @property {HTMLFormElement} form
 * @property {HTMLSelectElement} brand
 * @property {HTMLSelectElement} model
 * @property {HTMLSelectElement} year
 * @property {HTMLFieldSetElement} displayFieldset
 * @property {HTMLElement} displayList
 * @property {HTMLButtonElement} submit
 * @property {HTMLElement} message
 * @property {HTMLElement} summary
 * @property {HTMLElement} summaryText
 * @property {HTMLAnchorElement} [summaryLink]
 * @property {HTMLElement} empty
 * @property {HTMLScriptElement} data
 * @property {HTMLScriptElement} strings
 */

/**
 * Fahrzeugauswahl: Marke → Modell → Baujahr → Displayausführung.
 * Die Daten kommen als JSON aus snippets/vehicle-selector-data.liquid.
 *
 * @extends {Component<Refs>}
 */
class VehicleSelectorComponent extends Component {
  requiredRefs = ['form', 'brand', 'model', 'year', 'displayFieldset', 'displayList', 'submit', 'message', 'data'];

  /** @type {VehicleDisplay[]} */
  #displays = [];

  /** @type {Record<string, string>} */
  #strings = {};

  connectedCallback() {
    super.connectedCallback();

    this.#displays = parseJson(this.refs.data, []);
    this.#strings = parseJson(this.refs.strings, {});

    if (this.#displays.length === 0) {
      this.refs.form.hidden = true;
      this.refs.empty.hidden = false;
      return;
    }

    this.#renderBrands();
    this.#restoreSavedVehicle();
    this.#applyUrlPreset();
  }

  /* ----------------------------------------------------------------------- */
  /* Event-Handler (über on:change / on:submit / on:click im Markup)          */
  /* ----------------------------------------------------------------------- */

  handleBrandChange() {
    this.#renderModels();
    this.#resetFrom('year');
    this.#update();
  }

  handleModelChange() {
    this.#renderYears();
    this.#resetFrom('display');
    this.#update();
  }

  handleYearChange() {
    this.#renderDisplays();
    this.#update();
    // Nur ein Display → wurde automatisch ausgewählt, also auch merken
    this.#save();
  }

  handleDisplayChange() {
    this.#update();
    this.#save();
  }

  /** @param {SubmitEvent} event */
  handleSubmit(event) {
    event.preventDefault();

    const display = this.#selectedDisplay;
    if (!display) return;

    this.#save();

    if (display.productUrl) {
      window.location.assign(display.productUrl);
      return;
    }

    this.#showNoProductMessage();
  }

  editVehicle() {
    this.refs.summary.hidden = true;
    this.refs.form.hidden = false;
    this.refs.brand.focus();
  }

  /* ----------------------------------------------------------------------- */
  /* Rendering                                                              */
  /* ----------------------------------------------------------------------- */

  #renderBrands() {
    const brands = uniqueBy(
      this.#displays.map((d) => d.brand),
      (b) => b.id
    ).sort(byName);

    fillSelect(this.refs.brand, brands.map((b) => [b.id, b.name]));
  }

  #renderModels() {
    const brandId = this.refs.brand.value;
    const models = uniqueBy(
      this.#displays.filter((d) => d.brand.id === brandId).map((d) => d.model),
      (m) => m.id
    ).sort(byName);

    fillSelect(this.refs.model, models.map((m) => [m.id, m.name]), this.#strings.chooseModel);
    this.refs.model.disabled = !brandId;

    // Nur ein Modell → direkt auswählen
    if (models.length === 1 && models[0]) {
      this.refs.model.value = models[0].id;
      this.#renderYears();
    }
  }

  #renderYears() {
    const modelId = this.refs.model.value;
    const currentYear = new Date().getFullYear();
    const years = new Set();

    for (const display of this.#displays) {
      if (display.model.id !== modelId) continue;

      const to = display.series.to ?? currentYear;
      for (let year = display.series.from; year <= to; year++) years.add(year);
    }

    const sorted = [...years].sort((a, b) => b - a);
    fillSelect(this.refs.year, sorted.map((y) => [String(y), String(y)]), this.#strings.chooseYear);
    this.refs.year.disabled = !modelId;
  }

  #renderDisplays() {
    const list = this.refs.displayList;
    const displays = this.#displaysForSelection;
    const radioName = `${this.refs.brand.id}-display`;

    list.replaceChildren();
    this.refs.message.replaceChildren();

    if (!this.refs.year.value) {
      this.refs.displayFieldset.hidden = true;
      return;
    }

    this.refs.displayFieldset.hidden = false;

    if (displays.length === 0) {
      const text = document.createElement('p');
      text.className = 'vehicle-selector__help';
      text.textContent = this.#strings.noDisplayForYear ?? '';
      list.append(text);
      return;
    }

    // Mehrere Baureihen im selben Baujahr → Baureihe im Namen mit anzeigen
    const showSeries = new Set(displays.map((d) => d.series.id)).size > 1;

    for (const display of displays) {
      const id = `${radioName}-${display.id}`;

      const label = document.createElement('label');
      label.className = 'vehicle-selector__option';
      label.htmlFor = id;

      const input = document.createElement('input');
      input.type = 'radio';
      input.name = radioName;
      input.id = id;
      input.value = display.id;
      input.checked = displays.length === 1;

      const body = document.createElement('span');
      body.className = 'vehicle-selector__option-body';

      const name = document.createElement('strong');
      name.textContent = showSeries ? `${display.name} (${display.series.name})` : display.name;
      body.append(name);

      if (display.hint) {
        const hint = document.createElement('span');
        hint.className = 'vehicle-selector__option-hint';
        hint.textContent = display.hint;
        body.append(hint);
      }

      if (display.image) {
        const img = document.createElement('img');
        img.className = 'vehicle-selector__option-image';
        img.src = display.image;
        img.alt = display.imageAlt ?? '';
        img.loading = 'lazy';
        img.width = 480;
        body.append(img);
      }

      label.append(input, body);
      list.append(label);
    }
  }

  #showNoProductMessage() {
    const message = this.refs.message;
    const text = document.createElement('p');
    text.textContent = `${this.#strings.noProduct ?? ''} `;

    const link = document.createElement('a');
    link.href = this.dataset.contactUrl ?? '/pages/kontakt';
    link.textContent = this.#strings.contactLink ?? '';
    text.append(link);

    message.replaceChildren(text);
  }

  /* ----------------------------------------------------------------------- */
  /* Zustand                                                                */
  /* ----------------------------------------------------------------------- */

  /** @returns {VehicleDisplay[]} */
  get #displaysForSelection() {
    const modelId = this.refs.model.value;
    const year = Number(this.refs.year.value);
    if (!modelId || !year) return [];

    const currentYear = new Date().getFullYear();

    return this.#displays
      .filter(
        (d) => d.model.id === modelId && d.series.from <= year && year <= (d.series.to ?? currentYear)
      )
      .sort(byName);
  }

  /** @returns {VehicleDisplay | undefined} */
  get #selectedDisplay() {
    const checked = this.refs.displayList.querySelector('input[type="radio"]:checked');
    if (!(checked instanceof HTMLInputElement)) return undefined;

    return this.#displays.find((d) => d.id === checked.value);
  }

  /** @param {'year' | 'display'} from */
  #resetFrom(from) {
    if (from === 'year' && !this.refs.model.value) {
      fillSelect(this.refs.year, [], this.#strings.chooseYear);
      this.refs.year.disabled = true;
    }
    this.#renderDisplays();
  }

  #update() {
    this.refs.submit.disabled = !this.#selectedDisplay;
    this.refs.message.replaceChildren();
  }

  #save() {
    const display = this.#selectedDisplay;
    if (!display) return;

    /** @type {SavedVehicle} */
    const vehicle = {
      brand: this.refs.brand.value,
      model: this.refs.model.value,
      year: this.refs.year.value,
      display: display.id,
      label: `${display.brand.name} ${display.model.name} (${this.refs.year.value})`,
    };

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(vehicle));
    } catch {
      // localStorage nicht verfügbar (privater Modus, blockiert) – Auswahl funktioniert trotzdem
    }
  }

  /**
   * Vorauswahl über ?baureihe=<handle> (Kacheln aus sections/vehicle-quicklinks.liquid):
   * Marke und Modell setzen, dann den Kunden das Baujahr wählen lassen.
   */
  #applyUrlPreset() {
    const seriesId = new URLSearchParams(window.location.search).get('baureihe');
    if (!seriesId) return;

    const display = this.#displays.find((d) => d.series.id === seriesId);
    if (!display) return;

    this.refs.summary.hidden = true;
    this.refs.form.hidden = false;

    this.refs.brand.value = display.brand.id;
    this.#renderModels();
    this.refs.model.value = display.model.id;
    this.#renderYears();
    this.#resetFrom('display');
    this.#update();

    // Nur ein Baujahr in der Baureihe → direkt setzen, sonst Fokus auf das Baujahr-Feld
    const to = display.series.to ?? new Date().getFullYear();
    if (display.series.from === to) {
      this.refs.year.value = String(to);
      this.handleYearChange();
    } else {
      this.refs.year.focus({ preventScroll: true });
    }
    this.scrollIntoView({ block: 'start' });
  }

  #restoreSavedVehicle() {
    /** @type {SavedVehicle | null} */
    let saved = null;

    try {
      saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null');
    } catch {
      saved = null;
    }

    if (!saved || typeof saved !== 'object') return;

    const display = this.#displays.find((d) => d.id === saved?.display);
    // Gespeichertes Display existiert nicht mehr (oder Passform zurückgezogen) → ignorieren
    if (!display || display.brand.id !== saved.brand || display.model.id !== saved.model) return;

    this.refs.brand.value = saved.brand;
    this.#renderModels();
    this.refs.model.value = saved.model;
    this.#renderYears();

    if (![...this.refs.year.options].some((o) => o.value === saved?.year)) return;
    this.refs.year.value = saved.year;
    this.#renderDisplays();

    const radio = this.refs.displayList.querySelector(`input[value="${CSS.escape(display.id)}"]`);
    if (!(radio instanceof HTMLInputElement)) return;
    radio.checked = true;
    this.#update();

    this.refs.summaryText.textContent = `${display.brand.name} ${display.model.name} (${saved.year}) – ${display.name}`;

    // Direkter Weg zur passenden Folie, wenn es ein verknüpftes Produkt gibt
    const summaryLink = this.refs.summaryLink;
    if (summaryLink) {
      summaryLink.hidden = !display.productUrl;
      if (display.productUrl) summaryLink.href = display.productUrl;
    }
    this.refs.summary.hidden = false;
    this.refs.form.hidden = true;
  }
}

/* ------------------------------------------------------------------------- */
/* Hilfsfunktionen                                                          */
/* ------------------------------------------------------------------------- */

/**
 * @template T
 * @param {HTMLScriptElement | undefined} element
 * @param {T} fallback
 * @returns {T}
 */
function parseJson(element, fallback) {
  try {
    return JSON.parse(element?.textContent ?? '') ?? fallback;
  } catch {
    return fallback;
  }
}

/**
 * Ersetzt die Optionen eines Selects, behält die erste (Platzhalter-)Option.
 *
 * @param {HTMLSelectElement} select
 * @param {[string, string][]} options - [value, label]
 * @param {string} [placeholder]
 */
function fillSelect(select, options, placeholder) {
  const first = select.options[0];
  const placeholderOption = new Option(placeholder ?? first?.text ?? '', '');
  select.replaceChildren(placeholderOption, ...options.map(([value, label]) => new Option(label, value)));
}

/**
 * @template T
 * @param {T[]} items
 * @param {(item: T) => string} key
 * @returns {T[]}
 */
function uniqueBy(items, key) {
  const map = new Map();
  for (const item of items) if (!map.has(key(item))) map.set(key(item), item);
  return [...map.values()];
}

/**
 * @param {{ name: string }} a
 * @param {{ name: string }} b
 */
function byName(a, b) {
  return a.name.localeCompare(b.name, 'de', { numeric: true });
}

if (!customElements.get('vehicle-selector-component')) {
  customElements.define('vehicle-selector-component', VehicleSelectorComponent);
}
