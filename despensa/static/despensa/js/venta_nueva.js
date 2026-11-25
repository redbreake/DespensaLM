(() => {
  const form = document.getElementById('sale-form');
  if (!form) return;

  const rowsContainer = document.getElementById('sale-rows');
  const addRowButton = document.getElementById('add-sale-row');
  const itemsInput = document.getElementById('sale-items');
  const totalOutput = document.getElementById('sale-total');
  const methodSelect = document.getElementById('sale-method');
  const clientSelect = document.getElementById('sale-client');

  const products = JSON.parse(document.getElementById('sale-products-data').textContent);
  const initialItems = JSON.parse(document.getElementById('sale-initial-items').textContent);
  const productById = new Map(products.map((product) => [String(product.id), product]));

  const currency = new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    maximumFractionDigits: 2,
  });

  function updateClientRequirement() {
    clientSelect.required = methodSelect.value === 'FIADO';
  }

  function updateSummary() {
    let total = 0;
    rowsContainer.querySelectorAll('tr').forEach((row) => {
      const select = row.querySelector('[data-field="producto_id"]');
      const qtyInput = row.querySelector('[data-field="cantidad"]');
      const subtotalCell = row.querySelector('[data-field="subtotal"]');
      const product = productById.get(select.value);
      const qty = Math.max(0, Number.parseInt(qtyInput.value, 10) || 0);
      const subtotal = product ? Number(product.precio_venta) * qty : 0;
      subtotalCell.textContent = currency.format(subtotal);
      total += subtotal;
    });
    totalOutput.textContent = currency.format(total);
  }

  function addRow(item = {}) {
    const row = document.createElement('tr');

    const productTd = document.createElement('td');
    productTd.dataset.label = 'Producto';
    const select = document.createElement('select');
    select.dataset.field = 'producto_id';
    select.required = true;

    const emptyOpt = document.createElement('option');
    emptyOpt.value = '';
    emptyOpt.textContent = 'Seleccionar producto...';
    select.appendChild(emptyOpt);

    products.forEach((product) => {
      const opt = document.createElement('option');
      opt.value = String(product.id);
      opt.textContent = `${product.nombre} — ${currency.format(Number(product.precio_venta))} (Stock: ${product.stock_actual})`;
      if (String(item.producto_id || '') === String(product.id)) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
    productTd.appendChild(select);

    const qtyTd = document.createElement('td');
    qtyTd.dataset.label = 'Cantidad';
    const qtyInput = document.createElement('input');
    qtyInput.dataset.field = 'cantidad';
    qtyInput.type = 'number';
    qtyInput.min = '1';
    qtyInput.step = '1';
    qtyInput.required = true;
    qtyInput.inputMode = 'numeric';
    qtyInput.value = item.cantidad ? String(item.cantidad) : '1';
    qtyTd.appendChild(qtyInput);

    const subtotalTd = document.createElement('td');
    subtotalTd.dataset.label = 'Subtotal';
    const subtotalStrong = document.createElement('strong');
    subtotalStrong.dataset.field = 'subtotal';
    subtotalStrong.textContent = currency.format(0);
    subtotalTd.appendChild(subtotalStrong);

    const actionsTd = document.createElement('td');
    actionsTd.className = 'receipt-row-actions';
    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'remove-row-button';
    removeButton.setAttribute('aria-label', 'Quitar producto');
    removeButton.textContent = '×';
    removeButton.addEventListener('click', () => {
      row.remove();
      if (!rowsContainer.children.length) addRow();
      updateSummary();
    });
    actionsTd.appendChild(removeButton);

    select.addEventListener('change', updateSummary);
    qtyInput.addEventListener('input', updateSummary);

    row.append(productTd, qtyTd, subtotalTd, actionsTd);
    rowsContainer.appendChild(row);
    updateSummary();
    return row;
  }

  addRowButton.addEventListener('click', () => addRow());
  methodSelect.addEventListener('change', updateClientRequirement);

  form.addEventListener('submit', (event) => {
    const items = Array.from(rowsContainer.querySelectorAll('tr')).map((row) => ({
      producto_id: row.querySelector('[data-field="producto_id"]').value,
      cantidad: row.querySelector('[data-field="cantidad"]').value,
    }));
    itemsInput.value = JSON.stringify(items);
    if (!form.checkValidity()) {
      event.preventDefault();
      form.reportValidity();
    }
  });

  updateClientRequirement();
  if (Array.isArray(initialItems) && initialItems.length) {
    initialItems.forEach(addRow);
  } else {
    addRow();
  }
})();
