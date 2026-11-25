(function () {
  const storageKey = 'despensa-lm-cart';
  const formatter = new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
  });

  const cartItems = document.querySelector('[data-cart-items]');
  const totalNode = document.querySelector('[data-total]');
  const countNodes = document.querySelectorAll('[data-cart-count]');
  const mobileTotalNode = document.querySelector('[data-mobile-total]');
  const whatsappButton = document.querySelector('[data-whatsapp]');
  const clearButton = document.querySelector('[data-clear]');
  const searchInput = document.querySelector('[data-search]');
  const searchStatus = document.querySelector('[data-search-status]');
  const cartPanel = document.querySelector('[data-cart]');
  const cartToggles = document.querySelectorAll('[data-cart-toggle]');
  const cartCloseButtons = document.querySelectorAll('[data-cart-close]');
  const mobileViewport = window.matchMedia('(max-width: 820px)');

  const readCart = () => {
    try {
      const parsed = JSON.parse(localStorage.getItem(storageKey) || '[]');
      if (!Array.isArray(parsed)) return [];
      return parsed.filter(
        (item) =>
          item &&
          typeof item.id === 'string' &&
          typeof item.name === 'string' &&
          Number.isFinite(Number(item.price)) &&
          Number(item.price) >= 0 &&
          Number.isInteger(Number(item.quantity)) &&
          Number(item.quantity) > 0
      ).map((item) => ({
        id: item.id,
        name: item.name,
        price: Number(item.price),
        quantity: Number(item.quantity),
      }));
    } catch {
      try {
        localStorage.removeItem(storageKey);
      } catch {
        // Ignorar errores de almacenamiento restringido.
      }
      return [];
    }
  };

  const writeCart = (cart) => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(cart));
    } catch {
      // Ignorar si el navegador bloquea localStorage.
    }
  };

  function renderCart() {
    const cart = readCart();
    cartItems.replaceChildren();

    if (!cart.length) {
      const emptyMessage = document.createElement('p');
      emptyMessage.className = 'empty';
      emptyMessage.textContent = 'Agrega productos para armar tu pedido.';
      cartItems.appendChild(emptyMessage);
    }

    let total = 0;
    let count = 0;
    cart.forEach((item) => {
      total += item.price * item.quantity;
      count += item.quantity;

      const row = document.createElement('div');
      row.className = 'cart-row';

      const info = document.createElement('div');
      const title = document.createElement('p');
      title.textContent = item.name;
      const unitPrice = document.createElement('small');
      unitPrice.textContent = `${formatter.format(item.price)} c/u`;
      info.append(title, unitPrice);

      const qty = document.createElement('div');
      qty.className = 'qty';

      const decButton = document.createElement('button');
      decButton.type = 'button';
      decButton.dataset.dec = item.id;
      decButton.setAttribute('aria-label', `Quitar ${item.name}`);
      decButton.textContent = '-';

      const qtyValue = document.createElement('strong');
      qtyValue.textContent = String(item.quantity);

      const incButton = document.createElement('button');
      incButton.type = 'button';
      incButton.dataset.inc = item.id;
      incButton.setAttribute('aria-label', `Sumar ${item.name}`);
      incButton.textContent = '+';

      qty.append(decButton, qtyValue, incButton);
      row.append(info, qty);
      cartItems.appendChild(row);
    });

    totalNode.textContent = formatter.format(total);
    countNodes.forEach((node) => {
      node.textContent = count;
    });
    if (mobileTotalNode) {
      mobileTotalNode.textContent = formatter.format(total);
    }
    whatsappButton.disabled = !cart.length;
  }

  function setCartOpen(open) {
    const shouldOpen = open && mobileViewport.matches;
    document.body.classList.toggle('cart-open', shouldOpen);
    cartPanel.setAttribute('aria-hidden', String(mobileViewport.matches && !shouldOpen));
    cartToggles.forEach((button) => {
      button.setAttribute('aria-expanded', String(shouldOpen));
    });

    if (shouldOpen) {
      const closeButton = cartPanel.querySelector('[data-cart-close]');
      if (closeButton) closeButton.focus();
    }
  }

  cartToggles.forEach((button) => {
    button.addEventListener('click', () => {
      if (mobileViewport.matches) {
        setCartOpen(!document.body.classList.contains('cart-open'));
      } else {
        cartPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  cartCloseButtons.forEach((button) => {
    button.addEventListener('click', () => setCartOpen(false));
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setCartOpen(false);
  });

  mobileViewport.addEventListener('change', () => setCartOpen(false));

  function updateQuantity(id, delta) {
    const cart = readCart()
      .map((item) => item.id === id ? { ...item, quantity: item.quantity + delta } : item)
      .filter((item) => item.quantity > 0);
    writeCart(cart);
    renderCart();
  }

  document.querySelectorAll('[data-add]').forEach((button) => {
    button.addEventListener('click', () => {
      const product = button.closest('[data-product]');
      const id = product.dataset.id;
      const cart = readCart();
      const existing = cart.find((item) => item.id === id);

      if (existing) {
        existing.quantity += 1;
      } else {
        cart.push({
          id,
          name: product.dataset.name,
          price: Number(product.dataset.price),
          quantity: 1,
        });
      }

      writeCart(cart);
      renderCart();
      const originalLabel = button.textContent;
      button.textContent = 'Agregado';
      button.classList.add('added');
      window.setTimeout(() => {
        button.textContent = originalLabel;
        button.classList.remove('added');
      }, 900);
    });
  });

  cartItems.addEventListener('click', (event) => {
    const inc = event.target.closest('[data-inc]');
    const dec = event.target.closest('[data-dec]');
    if (inc) updateQuantity(inc.dataset.inc, 1);
    if (dec) updateQuantity(dec.dataset.dec, -1);
  });

  clearButton.addEventListener('click', () => {
    writeCart([]);
    renderCart();
  });

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const term = searchInput.value.trim().toLowerCase();
      let visible = 0;
      document.querySelectorAll('[data-product]').forEach((product) => {
        const matches = product.dataset.name.toLowerCase().includes(term);
        product.hidden = !matches;
        if (matches) visible += 1;
      });
      if (searchStatus) {
        searchStatus.textContent = term
          ? `${visible} ${visible === 1 ? 'producto encontrado' : 'productos encontrados'}`
          : '';
      }
    });
  }

  whatsappButton.addEventListener('click', () => {
    const phone = whatsappButton.dataset.phone;
    const cart = readCart();
    const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const lines = cart.map((item) => {
      const subtotal = formatter.format(item.price * item.quantity);
      return `- ${item.quantity}x ${item.name} (${subtotal})`;
    });
    const text = [
      'Hola Despensa LM, quiero realizar el siguiente pedido:',
      ...lines,
      `Total estimado: ${formatter.format(total)}`,
    ].join('\n');

    if (!phone) {
      alert('Falta configurar el numero de WhatsApp del comercio.');
      return;
    }

    window.location.href = `https://wa.me/${phone}?text=${encodeURIComponent(text)}`;
  });

  renderCart();
  setCartOpen(false);
})();
