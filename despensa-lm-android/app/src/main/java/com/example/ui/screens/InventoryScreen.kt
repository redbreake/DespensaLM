package com.example.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.text.input.KeyboardType
import com.example.data.local.CachedProduct
import com.example.ui.AppViewModel
import com.example.ui.components.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InventoryScreen(
    viewModel: AppViewModel,
    openProductFormRequest: Int = 0,
    onProductFormRequestHandled: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    var searchQuery by remember { mutableStateOf("") }
    var showProductForm by remember { mutableStateOf(false) }
    var showInventoryScanner by remember { mutableStateOf(false) }
    val allProducts by viewModel.allProducts.collectAsState()

    LaunchedEffect(openProductFormRequest) {
        if (openProductFormRequest > 0) {
            showProductForm = true
            onProductFormRequestHandled()
        }
    }

    val filteredProducts = remember(searchQuery, allProducts) {
        if (searchQuery.isBlank()) allProducts else allProducts.filter {
            it.nombre.contains(searchQuery, true) || it.codigo_barras.orEmpty().contains(searchQuery, true)
        }
    }
    val criticalCount = allProducts.count { it.stock_actual <= it.stock_minimo }
    val stockValue = allProducts.sumOf { it.precio_costo * it.stock_actual }

    if (showInventoryScanner) {
        ModalBottomSheet(onDismissRequest = { showInventoryScanner = false }) {
            Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 24.dp)) {
                Text("Buscar por código", style = MaterialTheme.typography.headlineSmall)
                Text("Abriremos el producto para editarlo o uno nuevo si no existe.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(16.dp))
                ScannerPanel(
                    onBarcodeScanned = { barcode ->
                        val product = allProducts.firstOrNull { it.codigo_barras == barcode }
                        viewModel.resetProductForm(existing = product, initialBarcode = barcode)
                        showInventoryScanner = false
                        showProductForm = true
                    },
                    modifier = Modifier.fillMaxWidth().height(280.dp)
                )
            }
        }
    }

    if (showProductForm) {
        ProductFormSheet(viewModel = viewModel, onDismiss = { showProductForm = false })
    }

    Column(modifier.fillMaxSize()) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 14.dp)) {
            ScreenIntro("Inventario", "Precios, existencias y catálogo")
            Spacer(Modifier.height(14.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                MetricTile("Productos", allProducts.size.toString(), Modifier.weight(1f))
                MetricTile("Stock bajo", criticalCount.toString(), Modifier.weight(1f), emphasized = criticalCount > 0)
                MetricTile("Invertido", money(stockValue), Modifier.weight(1.3f))
            }
            Spacer(Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                AppSearchField(
                    searchQuery,
                    { searchQuery = it },
                    "Nombre o código",
                    Modifier.weight(1f).testTag("inventory_search_input"),
                    actionIcon = Icons.Default.Settings,
                    actionDescription = "Escanear código",
                    onAction = { showInventoryScanner = true }
                )
                Button(
                    onClick = {
                        viewModel.resetProductForm()
                        showProductForm = true
                    },
                    modifier = Modifier.height(56.dp),
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = PaddingValues(horizontal = 14.dp)
                ) {
                    Icon(Icons.Default.Add, contentDescription = null)
                    Spacer(Modifier.width(4.dp))
                    Text("Nuevo")
                }
            }
        }

        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("${filteredProducts.size} productos", style = MaterialTheme.typography.labelLarge)
            Text("Tocá uno para editar", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding = PaddingValues(bottom = 16.dp)
        ) {
            if (filteredProducts.isEmpty()) {
                item {
                    EmptyState(Icons.Default.List, "Sin resultados", "Probá con otro nombre o cargá un producto nuevo.", Modifier.fillParentMaxWidth().padding(top = 48.dp))
                }
            } else {
                items(filteredProducts, key = { it.id }) { product ->
                    InventoryProductRow(product) {
                        viewModel.resetProductForm(product)
                        showProductForm = true
                    }
                }
            }
        }
    }
}

@Composable
private fun InventoryProductRow(product: CachedProduct, onClick: () -> Unit) {
    val critical = product.stock_actual <= product.stock_minimo
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, if (critical) MaterialTheme.colorScheme.secondary.copy(alpha = .55f) else MaterialTheme.colorScheme.outlineVariant)
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(product.nombre, modifier = Modifier.weight(1f, fill = false), style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    if (!product.activo_en_catalogo) {
                        Spacer(Modifier.width(8.dp))
                        StatusPill("Oculto", false)
                    }
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    product.codigo_barras?.let { "Código $it" } ?: "Sin código de barras",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    Text("Costo ${money(product.precio_costo)}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("Venta ${money(product.precio_venta)}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                }
            }
            Spacer(Modifier.width(12.dp))
            Column(horizontalAlignment = Alignment.End) {
                Text(product.stock_actual.toString(), style = MaterialTheme.typography.headlineSmall, color = if (critical) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.onSurface)
                Text(if (critical) "stock bajo" else "en stock", style = MaterialTheme.typography.labelSmall, color = if (critical) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Spacer(Modifier.width(8.dp))
            Icon(Icons.Default.KeyboardArrowRight, contentDescription = "Editar", tint = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ProductFormSheet(viewModel: AppViewModel, onDismiss: () -> Unit) {
    var showBarcodeScanner by remember { mutableStateOf(false) }
    var confirmDelete by remember { mutableStateOf(false) }
    val title = if (viewModel.isEditingMode) "Editar producto" else "Nuevo producto"

    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            icon = { Icon(Icons.Default.Delete, contentDescription = null, tint = MaterialTheme.colorScheme.error) },
            title = { Text("Eliminar producto") },
            text = { Text("¿Seguro que querés eliminar ${viewModel.selectedProductToEdit?.nombre.orEmpty()}? Esta acción no se puede deshacer.") },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.selectedProductToEdit?.let { product ->
                            viewModel.deleteProduct(product) {
                                confirmDelete = false
                                onDismiss()
                            }
                        }
                    },
                    enabled = !viewModel.deleteProductLoading,
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    if (viewModel.deleteProductLoading) {
                        CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onError)
                    } else {
                        Text("Eliminar definitivamente")
                    }
                }
            },
            dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text("Cancelar") } }
        )
    }

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).imePadding().padding(horizontal = 20.dp).padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(title, style = MaterialTheme.typography.headlineSmall)
            Text(
                if (viewModel.isEditingMode) "Actualizá los datos y guardá los cambios." else "Completá lo esencial para incorporarlo al catálogo.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            OutlinedTextField(
                value = viewModel.productFormBarcode,
                onValueChange = { viewModel.productFormBarcode = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Código de barras") },
                trailingIcon = {
                    IconButton(onClick = { showBarcodeScanner = !showBarcodeScanner }) {
                        Icon(Icons.Default.Settings, contentDescription = "Escanear")
                    }
                },
                singleLine = true,
                shape = RoundedCornerShape(8.dp)
            )
            AnimatedVisibility(showBarcodeScanner) {
                ScannerPanel(
                    onBarcodeScanned = {
                        viewModel.productFormBarcode = it
                        showBarcodeScanner = false
                    },
                    modifier = Modifier.fillMaxWidth().height(220.dp)
                )
            }
            OutlinedTextField(
                value = viewModel.productFormNombre,
                onValueChange = { viewModel.productFormNombre = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Nombre") },
                singleLine = true,
                shape = RoundedCornerShape(8.dp)
            )

            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                NumberField("Precio de costo", viewModel.productFormCosto, { viewModel.productFormCosto = it }, Modifier.weight(1f), decimal = true)
                NumberField("Precio de venta", viewModel.productFormVenta, { viewModel.productFormVenta = it }, Modifier.weight(1f), decimal = true)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                NumberField("Stock actual", viewModel.productFormStockActual, { viewModel.productFormStockActual = it }, Modifier.weight(1f))
                NumberField("Avisar desde", viewModel.productFormStockMinimo, { viewModel.productFormStockMinimo = it }, Modifier.weight(1f))
            }

            Surface(shape = RoundedCornerShape(8.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
                Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("Visible en el catálogo", style = MaterialTheme.typography.titleSmall)
                        Text("Permite venderlo desde la caja", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Switch(checked = viewModel.productFormActivo, onCheckedChange = { viewModel.productFormActivo = it })
                }
            }

            AnimatedVisibility(viewModel.saveProductError != null) {
                Text(viewModel.saveProductError.orEmpty(), color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }
            AnimatedVisibility(viewModel.deleteProductError != null) {
                Text(viewModel.deleteProductError.orEmpty(), color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }
            if (viewModel.isEditingMode) {
                OutlinedButton(
                    onClick = { confirmDelete = true },
                    enabled = !viewModel.deleteProductLoading,
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.error)
                ) {
                    Icon(Icons.Default.Delete, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Eliminar del catálogo")
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedButton(onClick = onDismiss, modifier = Modifier.weight(1f).height(52.dp), shape = RoundedCornerShape(8.dp)) { Text("Cancelar") }
                Button(
                    onClick = { viewModel.submitProductForm(onComplete = onDismiss) },
                    enabled = !viewModel.saveProductLoading,
                    modifier = Modifier.weight(1.4f).height(52.dp),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    if (viewModel.saveProductLoading) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
                    else Text("Guardar producto", fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun NumberField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier,
    decimal: Boolean = false
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = modifier,
        label = { Text(label, maxLines = 1) },
        keyboardOptions = KeyboardOptions(keyboardType = if (decimal) KeyboardType.Decimal else KeyboardType.Number),
        singleLine = true,
        shape = RoundedCornerShape(8.dp)
    )
}
