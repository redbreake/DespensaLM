(function () {
  const storageKey = 'despensa-lm-cart';
  const formatter = new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
  });

  const cartItems = document.querySelector('[data-cart-items]');
  const totalNode = document.querySelector('[data-total]');
  const countNode = document.querySelector('[data-cart-count]');
  const whatsappButton = document.querySelector('[data-whatsapp]');
  const clearButton = document.querySelector('[data-clear]');

  const readCart = () => JSON.parse(localStorage.getItem(storageKey) || '[]');
  const writeCart = (cart) => localStorage.setItem(storageKey, JSON.stringify(cart));

  function renderCart() {
    const cart = readCart();
    cartItems.innerHTML = '';

    if (!cart.length) {
      cartItems.innerHTML = '<p class="empty">Agrega productos para armar tu pedido.</p>';
    }

    let total = 0;
    let count = 0;
    cart.forEach((item) => {
      total += item.price * item.quantity;
      count += item.quantity;
      const row = document.createElement('div');
      row.className = 'cart-row';
      row.innerHTML = `
        <div>
          <p>${item.name}</p>
          <small>${formatter.format(item.price)} c/u</small>
        </div>
        <div class="qty">
          <button type="button" data-dec="${item.id}" aria-label="Quitar ${item.name}">-</button>
          <strong>${item.quantity}</strong>
          <button type="button" data-inc="${item.id}" aria-label="Sumar ${item.name}">+</button>
        </div>
      `;
      cartItems.appendChild(row);
    });

    totalNode.textContent = formatter.format(total);
    countNode.textContent = count;
    whatsappButton.disabled = !cart.length;
  }

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
})();
