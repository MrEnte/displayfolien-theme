import { Component } from '@theme/component';
import { StandardEvents } from '@shopify/events';

/**
 * Schaltet den Lieferumfang-Text (Einzelfolie / Montage-Set) beim Variantenwechsel um.
 * Gleiches Muster wie assets/product-sku.js.
 *
 * @typedef {Object} Refs
 * @property {HTMLElement} single
 * @property {HTMLElement} set
 *
 * @extends {Component<Refs>}
 */
class ProductDeliveryScopeComponent extends Component {
  requiredRefs = ['single', 'set'];

  get #target() {
    return this.closest('[id*="ProductInformation-"], [id*="QuickAdd-"], product-card');
  }

  connectedCallback() {
    super.connectedCallback();
    this.#target?.addEventListener(StandardEvents.productSelect, this.#handleProductSelect);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.#target?.removeEventListener(StandardEvents.productSelect, this.#handleProductSelect);
  }

  /** @param {any} event */
  #handleProductSelect = (event) => {
    event.promise
      .then((/** @type {any} */ { detail }) => {
        if (!detail?.resource) return;
        if (detail.productId && String(detail.productId) !== this.dataset.productId) return;

        /** @type {string[]} */
        const options = detail.resource.options ?? [];
        const isSet = options.includes(this.dataset.setValue ?? '');

        this.refs.single.hidden = isSet;
        this.refs.set.hidden = !isSet;
      })
      .catch((/** @type {any} */ error) => {
        if (error?.name !== 'AbortError') console.warn('[product-delivery-scope] Event promise rejected:', error);
      });
  };
}

if (!customElements.get('product-delivery-scope-component')) {
  customElements.define('product-delivery-scope-component', ProductDeliveryScopeComponent);
}
