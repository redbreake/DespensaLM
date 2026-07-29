(() => {
  const form = document.getElementById('receipt-form');
  if (!form) return;

  const rowsContainer = document.getElementById('receipt-rows');
  const addButton = document.getElementById('add-receipt-row');
  const marginInput = document.getElementById('receipt-margin');
  const itemsInput = document.getElementById('receipt-items');
  const photoInput = document.getElementById('receipt-photo');
  const photoPreview = document.getElementById('receipt-photo-preview');
  const photoEmpty = document.getElementById('receipt-photo-empty');
  const unitsOutput = document.getElementById('receipt-units');
  const costOutput = document.getElementById('receipt-cost-total');
  const saleOutput = document.getElementById('receipt-sale-total');
  const initialItems = JSON.parse(document.getElementById('receipt-initial-items').textContent);
  const existingNames = new Set(
    JSON.parse(document.getElementById('receipt-existing-products').textContent)
      .map((name) => name.trim().toLocaleLowerCase('es-AR'))
  );
  const currency = new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    maximumFractionDigits: 2,
  });
  let photoUrl = null;

  function parseNumber(value) {
    const number = Number.parseFloat(value);
    return Number.isFinite(number) ? number : 0;
  }

  function salePrice(cost) {
    const margin = Math.max(0, parseNumber(marginInput.value));
    return Math.ceil((cost * (1 + margin / 100)) / 100) * 100;
  }

  function setProductStatus(row) {
    const name = row.querySelector('[data-field="nombre"]').value.trim().toLocaleLowerCase('es-AR');
    const status = row.querySelector('.receipt-product-status');
    if (!name) {
      status.textContent = '';
      status.dataset.type = '';
    } else if (existingNames.has(name)) {
      status.textContent = 'Sumará stock';
      status.dataset.type = 'existing';
    } else {
      status.textContent = 'Producto nuevo';
      status.dataset.type = 'new';
    }
  }

  function updateSummary() {
    let units = 0;
    let totalCost = 0;
    let totalSale = 0;

    rowsContainer.querySelectorAll('tr').forEach((row) => {
      const quantity = Math.max(0, Number.parseInt(row.querySelector('[data-field="cantidad"]').value, 10) || 0);
      const cost = Math.max(0, parseNumber(row.querySelector('[data-field="precio_costo"]').value));
      const sale = Math.max(0, parseNumber(row.querySelector('[data-field="precio_venta"]').value));
      units += quantity;
      totalCost += quantity * cost;
      totalSale += quantity * sale;
    });

    unitsOutput.textContent = String(units);
    costOutput.textContent = currency.format(totalCost);
    saleOutput.textContent = currency.format(totalSale);
  }

  function recalculateRow(row, force = false) {
    const sale = row.querySelector('[data-field="precio_venta"]');
    if (!force && sale.dataset.edited === 'true') return;
    const cost = parseNumber(row.querySelector('[data-field="precio_costo"]').value);
    sale.value = cost > 0 ? salePrice(cost).toFixed(2) : '';
    updateSummary();
  }

  function removeRow(row) {
    row.remove();
    if (!rowsContainer.children.length) addRow();
    updateSummary();
  }

  function addRow(item = {}) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td data-label="Producto">
        <input data-field="nombre" list="existing-products" maxlength="160" required autocomplete="off">
        <span class="receipt-product-status"></span>
      </td>
      <td data-label="Cantidad">
        <input data-field="cantidad" type="number" min="1" step="1" required inputmode="numeric">
      </td>
      <td data-label="Costo unitario">
        <div class="money-input"><span>$</span><input data-field="precio_costo" type="number" min="0" step="0.01" required inputmode="decimal"></div>
      </td>
      <td data-label="Venta">
        <div class="money-input"><span>$</span><input data-field="precio_venta" type="number" min="0" step="0.01" required inputmode="decimal"></div>
      </td>
      <td class="receipt-row-actions">
        <button type="button" class="remove-row-button" aria-label="Quitar producto" title="Quitar producto">×</button>
      </td>
    `;

    const name = row.querySelector('[data-field="nombre"]');
    const quantity = row.querySelector('[data-field="cantidad"]');
    const cost = row.querySelector('[data-field="precio_costo"]');
    const sale = row.querySelector('[data-field="precio_venta"]');

    name.value = item.nombre || '';
    quantity.value = item.cantidad || '';
    cost.value = item.precio_costo ?? '';
    sale.value = item.precio_venta ?? '';
    sale.dataset.edited = item.precio_venta ? 'true' : 'false';

    name.addEventListener('input', () => setProductStatus(row));
    quantity.addEventListener('input', updateSummary);
    cost.addEventListener('input', () => recalculateRow(row));
    sale.addEventListener('input', () => {
      sale.dataset.edited = sale.value ? 'true' : 'false';
      updateSummary();
    });
    row.querySelector('.remove-row-button').addEventListener('click', () => removeRow(row));

    rowsContainer.appendChild(row);
    setProductStatus(row);
    if (!sale.value && cost.value) recalculateRow(row);
    updateSummary();
    return row;
  }

  addButton.addEventListener('click', () => {
    const row = addRow();
    row.querySelector('[data-field="nombre"]').focus();
  });

  marginInput.addEventListener('input', () => {
    rowsContainer.querySelectorAll('tr').forEach((row) => recalculateRow(row, true));
  });

  photoInput.addEventListener('change', () => {
    const file = photoInput.files[0];
    if (!file) return;
    if (photoUrl) URL.revokeObjectURL(photoUrl);
    photoUrl = URL.createObjectURL(file);
    photoPreview.src = photoUrl;
    photoPreview.classList.add('visible');
    photoEmpty.hidden = true;
  });

  form.addEventListener('submit', (event) => {
    const items = Array.from(rowsContainer.querySelectorAll('tr')).map((row) => ({
      nombre: row.querySelector('[data-field="nombre"]').value.trim(),
      cantidad: row.querySelector('[data-field="cantidad"]').value,
      precio_costo: row.querySelector('[data-field="precio_costo"]').value,
      precio_venta: row.querySelector('[data-field="precio_venta"]').value,
    }));
    itemsInput.value = JSON.stringify(items);
    if (!form.checkValidity()) {
      event.preventDefault();
      form.reportValidity();
    }
  });

  window.addEventListener('beforeunload', () => {
    if (photoUrl) URL.revokeObjectURL(photoUrl);
  });

  if (initialItems.length) {
    initialItems.forEach(addRow);
  } else {
    addRow();
  }
})();
