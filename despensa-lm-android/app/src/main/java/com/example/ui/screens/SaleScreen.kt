package com.example.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
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
import com.example.data.local.CachedClient
import com.example.data.local.CachedProduct
import com.example.ui.AppViewModel
import com.example.ui.components.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SaleScreen(
    viewModel: AppViewModel,
    onNavigateToInventoryWithBarcode: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var searchQuery by remember { mutableStateOf("") }
    var showScanner by remember { mutableStateOf(false) }
    var showCheckout by remember { mutableStateOf(false) }
    var showClients by remember { mutableStateOf(false) }
    var clientQuery by remember { mutableStateOf("") }
    val allProducts by viewModel.allProducts.collectAsState()
    val allClients by viewModel.allClients.collectAsState()

    val filteredProducts = remember(searchQuery, allProducts) {
        if (searchQuery.isBlank()) emptyList() else allProducts.filter {
            it.nombre.contains(searchQuery, true) || it.codigo_barras.orEmpty().contains(searchQuery, true)
        }.take(20)
    }
    val filteredClients = remember(clientQuery, allClients) {
        if (clientQuery.isBlank()) allClients else allClients.filter {
            it.nombre.contains(clientQuery, true) || it.telefono.contains(clientQuery, true)
        }
    }

    if (viewModel.isNewProductScannedDialogShowing) {
        AlertDialog(
            onDismissRequest = { viewModel.isNewProductScannedDialogShowing = false },
            icon = { Icon(Icons.Default.Info, contentDescription = null) },
            title = { Text("Producto no registrado") },
            text = { Text("El código ${viewModel.scannedNotFoundBarcode} no está en el inventario. Podés cargarlo ahora y conservar el código.") },
            confirmButton = {
                Button(onClick = {
                    viewModel.isNewProductScannedDialogShowing = false
                    viewModel.resetProductForm(initialBarcode = viewModel.scannedNotFoundBarcode)
                    onNavigateToInventoryWithBarcode(viewModel.scannedNotFoundBarcode)
                }) { Text("Cargar producto") }
            },
            dismissButton = { TextButton(onClick = { viewModel.isNewProductScannedDialogShowing = false }) { Text("Ahora no") } }
        )
    }

    if (showScanner) {
        ModalBottomSheet(onDismissRequest = { showScanner = false }) {
            Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 24.dp)) {
                Text("Escanear producto", style = MaterialTheme.typography.headlineSmall)
                Text("El producto se agrega al carrito automáticamente.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(16.dp))
                ScannerPanel(
                    onBarcodeScanned = {
                        showScanner = false
                        viewModel.onBarcodeScanned(it)
                    },
                    modifier = Modifier.fillMaxWidth().height(280.dp)
                )
            }
        }
    }

    if (showClients) {
        ModalBottomSheet(onDismissRequest = {
            showClients = false
            showCheckout = true
        }) {
            Column(Modifier.fillMaxWidth().heightIn(max = 620.dp).padding(horizontal = 16.dp).padding(bottom = 20.dp)) {
                Text("Elegir cliente", style = MaterialTheme.typography.headlineSmall)
                Spacer(Modifier.height(12.dp))
                AppSearchField(clientQuery, { clientQuery = it }, "Nombre o teléfono", Modifier.fillMaxWidth())
                Spacer(Modifier.height(10.dp))
                LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(filteredClients, key = { it.id }) { client ->
                        ClientChoiceRow(client, viewModel.selectedClient?.id == client.id) {
                            viewModel.selectedClient = client
                            showClients = false
                            showCheckout = true
                        }
                    }
                }
            }
        }
    }

    if (showCheckout) {
        CheckoutSheet(
            viewModel = viewModel,
            onDismiss = { showCheckout = false },
            onChooseClient = {
                showCheckout = false
                showClients = true
            },
            onComplete = { showCheckout = false }
        )
    }

    Column(modifier.fillMaxSize()) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 14.dp)) {
            ScreenIntro("Caja rápida", "Buscá o escaneá productos para iniciar una venta")
            Spacer(Modifier.height(16.dp))
            AppSearchField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                placeholder = "Producto o código de barras",
                modifier = Modifier.fillMaxWidth().testTag("search_input"),
                actionIcon = Icons.Default.Search,
                actionDescription = "Abrir escáner",
                onAction = { showScanner = true }
            )

            AnimatedVisibility(searchQuery.isNotBlank()) {
                Surface(
                    modifier = Modifier.fillMaxWidth().heightIn(max = 250.dp).padding(top = 6.dp),
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.surface,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    shadowElevation = 4.dp
                ) {
                    LazyColumn {
                        if (filteredProducts.isEmpty()) {
                            item { Text("No encontramos coincidencias", Modifier.padding(16.dp), color = MaterialTheme.colorScheme.onSurfaceVariant) }
                        } else {
                            items(filteredProducts, key = { it.id }) { product ->
                                ProductSearchRow(product) {
                                    viewModel.addProductToCart(product)
                                    searchQuery = ""
                                }
                                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                            }
                        }
                    }
                }
            }
        }

        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Pedido actual", style = MaterialTheme.typography.titleMedium)
            if (viewModel.cart.isNotEmpty()) {
                TextButton(onClick = viewModel::clearCart) { Text("Vaciar") }
            }
        }

        LazyColumn(
            modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding = PaddingValues(bottom = 16.dp)
        ) {
            if (viewModel.cart.isEmpty()) {
                item {
                    EmptyState(
                        Icons.Default.ShoppingCart,
                        "Todavía no hay productos",
                        "Usá la búsqueda o el lector para agregarlos.",
                        Modifier.fillParentMaxHeight(.72f).fillMaxWidth()
                    )
                }
            } else {
                items(viewModel.cart.entries.toList(), key = { it.key.id }) { entry ->
                    CartProductRow(
                        product = entry.key,
                        quantity = entry.value,
                        onQuantityChange = { viewModel.updateProductCartQty(entry.key, it) },
                        onRemove = { viewModel.removeProductFromCart(entry.key) }
                    )
                }
            }
        }

        Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 8.dp) {
            Column(
                Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Button(
                    onClick = { showScanner = true },
                    modifier = Modifier.fillMaxWidth().height(58.dp).testTag("scan_sale_button"),
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
                ) {
                    Icon(Icons.Default.Search, contentDescription = null, modifier = Modifier.size(24.dp))
                    Spacer(Modifier.width(10.dp))
                    Text("Escanear producto", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                }

                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(Modifier.weight(1f)) {
                        Text("Total", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(money(viewModel.cartSubtotal), style = MaterialTheme.typography.headlineSmall)
                    }
                    Button(
                        onClick = { showCheckout = true },
                        enabled = viewModel.cart.isNotEmpty(),
                        modifier = Modifier.height(52.dp).widthIn(min = 150.dp),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("Cobrar", fontWeight = FontWeight.Bold)
                        Spacer(Modifier.width(8.dp))
                        Icon(Icons.Default.KeyboardArrowUp, contentDescription = null)
                    }
                }
            }
        }
    }
}

@Composable
private fun ProductSearchRow(product: CachedProduct, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().clickable(onClick = onClick).padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Column(Modifier.weight(1f)) {
            Text(product.nombre, style = MaterialTheme.typography.titleSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("Stock ${product.stock_actual}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Text(money(product.precio_venta), style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
        Icon(Icons.Default.Add, contentDescription = "Agregar", tint = MaterialTheme.colorScheme.primary)
    }
}

@Composable
private fun CartProductRow(
    product: CachedProduct,
    quantity: Int,
    onQuantityChange: (Int) -> Unit,
    onRemove: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f)) {
                    Text(product.nombre, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    Text("${money(product.precio_venta)} c/u · Stock ${product.stock_actual}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                IconButton(onClick = onRemove, modifier = Modifier.size(36.dp)) {
                    Icon(Icons.Default.Delete, contentDescription = "Quitar", tint = MaterialTheme.colorScheme.secondary)
                }
            }
            Spacer(Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(shape = RoundedCornerShape(8.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = { onQuantityChange(quantity - 1) }, modifier = Modifier.size(38.dp)) {
                            Text("−", style = MaterialTheme.typography.titleLarge)
                        }
                        Text(quantity.toString(), modifier = Modifier.widthIn(min = 32.dp), textAlign = androidx.compose.ui.text.style.TextAlign.Center, fontWeight = FontWeight.Bold)
                        IconButton(onClick = { onQuantityChange(quantity + 1) }, modifier = Modifier.size(38.dp)) {
                            Icon(Icons.Default.Add, contentDescription = "Aumentar", modifier = Modifier.size(18.dp))
                        }
                    }
                }
                Spacer(Modifier.weight(1f))
                Text(money(product.precio_venta * quantity), style = MaterialTheme.typography.titleLarge)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CheckoutSheet(
    viewModel: AppViewModel,
    onDismiss: () -> Unit,
    onChooseClient: () -> Unit,
    onComplete: () -> Unit
) {
    val methods = listOf("EFECTIVO" to "Efectivo", "TRANSFERENCIA" to "Transferencia", "DEBITO" to "Débito", "FIADO" to "Fiado")
    var menuOpen by remember { mutableStateOf(false) }
    val selectedLabel = methods.firstOrNull { it.first == viewModel.selectedPaymentMethod }?.second ?: "Efectivo"

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            Modifier.fillMaxWidth().verticalScroll(androidx.compose.foundation.rememberScrollState()).padding(horizontal = 20.dp).padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Text("Finalizar venta", style = MaterialTheme.typography.headlineSmall)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
                Column {
                    Text("${viewModel.cart.values.sum()} unidades", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("Total a cobrar", style = MaterialTheme.typography.titleMedium)
                }
                Text(money(viewModel.cartSubtotal), style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
            }
            HorizontalDivider()

            ExposedDropdownMenuBox(expanded = menuOpen, onExpandedChange = { menuOpen = it }) {
                OutlinedTextField(
                    value = selectedLabel,
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Forma de pago") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(menuOpen) },
                    modifier = Modifier.menuAnchor().fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp)
                )
                ExposedDropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                    methods.forEach { method ->
                        DropdownMenuItem(
                            text = { Text(method.second) },
                            onClick = {
                                viewModel.selectedPaymentMethod = method.first
                                if (method.first != "FIADO") viewModel.selectedClient = null
                                menuOpen = false
                            },
                            leadingIcon = { if (viewModel.selectedPaymentMethod == method.first) Icon(Icons.Default.Check, contentDescription = null) }
                        )
                    }
                }
            }

            AnimatedVisibility(viewModel.selectedPaymentMethod == "FIADO") {
                OutlinedButton(
                    onClick = onChooseClient,
                    modifier = Modifier.fillMaxWidth().height(52.dp),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(Icons.Default.Person, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text(viewModel.selectedClient?.nombre ?: "Seleccionar cliente")
                }
            }

            OutlinedTextField(
                value = viewModel.saleNotes,
                onValueChange = { viewModel.saleNotes = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Nota opcional") },
                minLines = 2,
                maxLines = 3,
                shape = RoundedCornerShape(8.dp)
            )

            AnimatedVisibility(viewModel.saleStatusMessage != null) {
                Text(
                    viewModel.saleStatusMessage.orEmpty(),
                    style = MaterialTheme.typography.bodySmall,
                    color = if (viewModel.saleStatusMessage.orEmpty().startsWith("Error") || viewModel.saleStatusMessage.orEmpty().contains("requiere")) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Button(
                onClick = { viewModel.submitVenta(onSuccess = onComplete) },
                enabled = !viewModel.saleLoading && (viewModel.selectedPaymentMethod != "FIADO" || viewModel.selectedClient != null),
                modifier = Modifier.fillMaxWidth().height(54.dp).testTag("submit_sale_button"),
                shape = RoundedCornerShape(8.dp)
            ) {
                if (viewModel.saleLoading) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
                else Text("Confirmar cobro", fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun ClientChoiceRow(client: CachedClient, selected: Boolean, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(8.dp),
        color = if (selected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant)
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(client.nombre, style = MaterialTheme.typography.titleMedium)
                Text(client.telefono.ifBlank { "Sin teléfono" }, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(money(client.saldo_actual), style = MaterialTheme.typography.titleSmall)
                Text("saldo", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
